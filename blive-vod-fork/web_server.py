# -*- coding: utf-8 -*-
"""桌面端 API 服务：HTTP + WebSocket。"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from aiohttp import WSMsgType, web

from app_runtime import runtime
from event_bus import bus


def _json(data: Any, status: int = 200) -> web.Response:
    return web.json_response(data, status=status)


async def handle_health(_: web.Request) -> web.Response:
    return _json({"ok": True, "service": "blive-vod-desktop"})


async def handle_status(_: web.Request) -> web.Response:
    return _json({"ok": True, "status": runtime.status()})


async def handle_events(request: web.Request) -> web.Response:
    try:
        limit = int(request.query.get("limit", "200"))
    except ValueError:
        limit = 200
    return _json({"ok": True, "events": bus.history(limit=limit)})


async def handle_config_get(_: web.Request) -> web.Response:
    return _json(
        {
            "ok": True,
            "config": runtime.load_config(),
            "blacklist": runtime.blacklist,
            "status": runtime.status(),
        }
    )


async def handle_config_post(request: web.Request) -> web.Response:
    body = await request.json()
    roomid = str(body.get("roomid", "")).strip()
    if roomid and not roomid.isdecimal():
        return _json({"ok": False, "message": "房间号必须是数字"}, status=400)
    cfg = runtime.save_config({"roomid": roomid})
    return _json({"ok": True, "config": cfg, "status": runtime.status()})


async def handle_blacklist_get(_: web.Request) -> web.Response:
    return _json({"ok": True, "items": runtime.load_blacklist()})


async def handle_blacklist_post(request: web.Request) -> web.Response:
    body = await request.json()
    items = body.get("items", [])
    if not isinstance(items, list):
        return _json({"ok": False, "message": "items 必须是数组"}, status=400)
    saved = runtime.save_blacklist(items)
    return _json({"ok": True, "items": saved})


async def handle_login(_: web.Request) -> web.Response:
    """启动登录流程（非阻塞），二维码通过 WebSocket 的 qr 事件推送"""
    result = await runtime.start_login()
    return _json(result)


async def handle_login_cancel(_: web.Request) -> web.Response:
    result = await runtime.cancel_login()
    return _json(result)


async def handle_start(request: web.Request) -> web.Response:
    body: Dict[str, Any] = {}
    if request.can_read_body:
        try:
            body = await request.json()
        except Exception:
            body = {}
    result = await runtime.start_listen(str(body.get("roomid", "")).strip())
    status = 200 if result.get("ok") else 400
    return _json(result, status=status)


async def handle_stop(_: web.Request) -> web.Response:
    result = await runtime.stop_listen()
    return _json(result)


async def handle_skip(_: web.Request) -> web.Response:
    return _json(runtime.skip_song())


async def handle_request_song(request: web.Request) -> web.Response:
    body = await request.json()
    result = await runtime.request_song(
        name=str(body.get("name", "")),
        singer=str(body.get("singer", "")),
        requester=str(body.get("requester", "手动点歌")),
    )
    status = 200 if result.get("ok") else 400
    return _json(result, status=status)


async def handle_ws(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
    queue = await bus.subscribe()

    async def send(payload: Dict[str, Any]) -> bool:
        """发送失败（客户端已断开）时返回 False，避免抛出未处理异常"""
        try:
            await ws.send_json(payload)
            return True
        except (ConnectionResetError, RuntimeError):
            return False

    try:
        await send({"type": "hello", "status": runtime.status(), "events": bus.history(100)})
        while not ws.closed:
            get_task = asyncio.create_task(queue.get())
            recv_task = asyncio.create_task(ws.receive())
            done, pending = await asyncio.wait(
                {get_task, recv_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if get_task in done:
                event = get_task.result()
                if not await send(event):
                    break
            if recv_task in done:
                msg = recv_task.result()
                if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.ERROR):
                    break
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except Exception:
                        continue
                    if data.get("type") == "ping":
                        if not await send({"type": "pong"}):
                            break
    finally:
        await bus.unsubscribe(queue)
        if not ws.closed:
            try:
                await ws.close()
            except (ConnectionResetError, RuntimeError):
                pass
    return ws


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/events", handle_events)
    app.router.add_get("/api/config", handle_config_get)
    app.router.add_post("/api/config", handle_config_post)
    app.router.add_get("/api/blacklist", handle_blacklist_get)
    app.router.add_post("/api/blacklist", handle_blacklist_post)
    app.router.add_post("/api/login", handle_login)
    app.router.add_post("/api/login/cancel", handle_login_cancel)
    app.router.add_post("/api/listen/start", handle_start)
    app.router.add_post("/api/listen/stop", handle_stop)
    app.router.add_post("/api/skip", handle_skip)
    app.router.add_post("/api/song/request", handle_request_song)
    app.router.add_get("/ws", handle_ws)
    return app


async def start_api_server(host: str = "127.0.0.1", port: int = 17820) -> tuple[web.AppRunner, int]:
    await runtime.bootstrap()
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    last_error: Optional[Exception] = None
    for offset in range(20):
        candidate = port + offset
        try:
            site = web.TCPSite(runner, host, candidate)
            await site.start()
            runtime.log(f"[系统] API 服务已启动: http://{host}:{candidate}")
            return runner, candidate
        except OSError as exc:
            last_error = exc
            continue
    raise RuntimeError(f"无法绑定 API 端口: {last_error}")


async def stop_api_server(runner: web.AppRunner) -> None:
    await runtime.shutdown()
    await runner.cleanup()
