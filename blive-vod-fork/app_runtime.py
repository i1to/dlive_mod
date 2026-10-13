# -*- coding: utf-8 -*-
"""桌面端运行时：登录、监听、点歌、配置热更新。"""

from __future__ import annotations

import asyncio
import json
import re
import time
import webbrowser
from typing import Any, Dict, List, Optional

import aiohttp
import blivedm
import blivedm.models.web as web_models
import bili_login
import kg_search
import qr_code
import song_handler
import tx_search
import wy_search
import lxmusic as lxmusic_module
from app_dir import get_blacklist_path, get_config_path
from event_bus import bus

lxmusic = lxmusic_module.lxmusic()

SEARCH_SOURCES = (
    (kg_search, "酷狗"),
    (wy_search, "网易云"),
    (tx_search, "QQ音乐"),
)


class EventBusQRPresenter:
    """桌面端二维码展示器：把点阵与状态通过事件总线推给前端弹窗"""

    def __init__(self, runtime: "AppRuntime"):
        self.runtime = runtime

    def show(self, qr_url: str) -> None:
        matrix = qr_code.make_matrix(qr_url)
        if not matrix:
            self.runtime.log("[登录] 二维码生成失败，请确认已安装 qrcode 依赖", level="error")
            self.runtime.qr = {
                "visible": True,
                "matrix": [],
                "state": "error",
                "message": "二维码生成失败，请重试登录",
            }
            bus.publish_sync("qr", **self.runtime.qr)
            return
        self.runtime.qr = {
            "visible": True,
            "matrix": matrix,
            "state": "waiting",
            "message": "请使用哔哩哔哩手机APP扫描二维码",
        }
        bus.publish_sync("qr", **self.runtime.qr)
        self.runtime.log("[登录] 请在窗口中扫描二维码完成登录")

    def status(self, state: str, message: str) -> None:
        self.runtime.qr["state"] = state
        self.runtime.qr["message"] = message
        bus.publish_sync("qr", **self.runtime.qr)

    def close(self) -> None:
        self.runtime.qr = {"visible": False, "matrix": [], "state": "idle", "message": ""}
        bus.publish_sync("qr", **self.runtime.qr)


class AppRuntime:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.client: Optional[blivedm.BLiveClient] = None
        self.listener_task: Optional[asyncio.Task] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

        self.roomid: str = ""
        self.connected: bool = False
        self.listening: bool = False
        self.user: Dict[str, Any] = {"uname": "", "uid": 0}
        self.blacklist: List[str] = []
        self.qr: Dict[str, Any] = {"visible": False, "matrix": [], "state": "idle", "message": ""}
        self.login_task: Optional[asyncio.Task] = None
        self.song_queue: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {
            "danmaku_total": 0,
            "song_total": 0,
            "song_success": 0,
            "song_failed": 0,
            "started_at": 0,
        }
        self._started = False

    def log(self, message: str, level: str = "info") -> None:
        print(message)
        bus.publish_sync("log", level=level, message=message)

    def load_config(self) -> Dict[str, Any]:
        try:
            with open(get_config_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"roomid": ""}

    def save_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        cfg = self.load_config()
        cfg.update(patch)
        with open(get_config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        if "roomid" in patch:
            self.roomid = str(patch.get("roomid") or "").strip()
        return cfg

    def load_blacklist(self) -> List[str]:
        path = get_blacklist_path()
        items: List[str] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    text = line.strip()
                    if text:
                        items.append(text)
        except FileNotFoundError:
            with open(path, "w", encoding="utf-8") as f:
                f.write("")
        self.blacklist = items
        return items

    def save_blacklist(self, items: List[str]) -> List[str]:
        cleaned = [str(x).strip() for x in items if str(x).strip()]
        path = get_blacklist_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(cleaned) + ("\n" if cleaned else ""))
        self.blacklist = cleaned
        self.log(f"[配置] 黑名单已更新，共 {len(cleaned)} 项")
        bus.publish_sync("blacklist", items=cleaned)
        return cleaned

    def status(self) -> Dict[str, Any]:
        return {
            "roomid": self.roomid,
            "connected": self.connected,
            "listening": self.listening,
            "user": self.user,
            "blacklist": self.blacklist,
            "song_queue": self.song_queue[-50:],
            "stats": self.stats,
            "sources": [label for _, label in SEARCH_SOURCES],
            "qr": self.qr,
            "logging_in": self.login_task is not None and not self.login_task.done(),
        }

    async def bootstrap(self) -> None:
        if self._started:
            return
        self._started = True
        self.loop = asyncio.get_running_loop()
        self.session = aiohttp.ClientSession()
        self.load_blacklist()
        cfg = self.load_config()
        self.roomid = str(cfg.get("roomid") or "").strip()
        self.stats["started_at"] = int(time.time() * 1000)
        await self._restore_session_cookies()
        self.log("[系统] 桌面后端已启动")
        bus.publish_sync("status", **self.status())

    async def _restore_session_cookies(self) -> None:
        """启动时把已保存的 Cookie 装载进 session，并读取账号信息"""
        cookie_data = bili_login.load_cookies()
        if not cookie_data or not self.session:
            return
        bili_login.apply_cookies_to_session(self.session, cookie_data)
        info = await bili_login.get_user_info(self.session)
        if info:
            self.user = info
            self.log(f"[登录] 已恢复登录状态: {info.get('uname')} (UID:{info.get('uid')})")
        else:
            self.log("[登录] 本地 Cookie 已失效，请重新扫码登录", level="warn")

    async def shutdown(self) -> None:
        await self.cancel_login()
        await self.stop_listen()
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None
        self._started = False
        self.log("[系统] 桌面后端已停止")

    async def ensure_login(self) -> Optional[str]:
        if not self.session:
            await self.bootstrap()
        self.log("[登录] 开始检查登录状态...")
        presenter = EventBusQRPresenter(self)
        try:
            roomid = await bili_login.ensure_login(
                self.session,
                qr_presenter=presenter,
            )
        except asyncio.CancelledError:
            presenter.close()
            self.log("[登录] 登录已取消", level="warn")
            raise
        except Exception as exc:
            presenter.close()
            self.log(f"[登录] 登录失败: {exc}", level="error")
            bus.publish_sync("status", **self.status())
            return None
        info = await bili_login.get_user_info(self.session)
        if info:
            self.user = info
            self.log(f"[登录] 当前账号: {info.get('uname')} (UID:{info.get('uid')})")
        else:
            self.user = {"uname": "", "uid": 0}
            self.log("[登录] 当前未登录或无法获取账号信息", level="warn")
        bus.publish_sync("status", **self.status())
        return roomid

    async def start_login(self) -> Dict[str, Any]:
        """后台执行登录流程，二维码通过事件推送给前端"""
        if self.login_task is not None and not self.login_task.done():
            return {"ok": True, "message": "登录流程进行中", "status": self.status()}
        if not self.session:
            await self.bootstrap()

        async def _run() -> None:
            try:
                roomid = await self.ensure_login()
                if roomid and not self.roomid:
                    self.save_config({"roomid": roomid})
                    self.log(f"[配置] 已使用登录账号的直播间号: {roomid}")
            except asyncio.CancelledError:
                pass
            finally:
                bus.publish_sync("status", **self.status())

        self.login_task = asyncio.create_task(_run())
        bus.publish_sync("status", **self.status())
        return {"ok": True, "message": "已开始登录流程", "status": self.status()}

    async def cancel_login(self) -> Dict[str, Any]:
        """取消进行中的登录流程并关闭二维码弹窗"""
        task = self.login_task
        if task is None or task.done():
            self.qr = {"visible": False, "matrix": [], "state": "idle", "message": ""}
            bus.publish_sync("qr", **self.qr)
            return {"ok": True, "message": "当前没有进行中的登录", "status": self.status()}
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        self.login_task = None
        self.qr = {"visible": False, "matrix": [], "state": "idle", "message": ""}
        bus.publish_sync("qr", **self.qr)
        self.log("[登录] 已取消登录", level="warn")
        bus.publish_sync("status", **self.status())
        return {"ok": True, "message": "已取消登录", "status": self.status()}

    async def start_listen(self, roomid: str = "") -> Dict[str, Any]:
        if self.listening:
            return {"ok": True, "message": "已在监听中", "status": self.status()}

        roomid = (roomid or self.roomid or "").strip()
        if not roomid or not roomid.isdecimal():
            return {"ok": False, "message": "请输入有效的直播间号", "status": self.status()}

        if not self.session:
            await self.bootstrap()

        # 未登录时先引导扫码，避免请求长时间挂起
        if not await bili_login.check_cookie_valid(self.session):
            await self.start_login()
            return {
                "ok": False,
                "message": "请先在弹窗中扫码登录，登录完成后再开始监听",
                "status": self.status(),
            }

        self.roomid = roomid
        self.save_config({"roomid": roomid})
        self.listener_task = asyncio.create_task(self._listen_loop(int(roomid)))
        self.listening = True
        self.stats["started_at"] = int(time.time() * 1000)
        self.log(f"[信息] 开始监听房间号: {roomid}  https://live.bilibili.com/{roomid}")
        bus.publish_sync("status", **self.status())
        return {"ok": True, "message": f"已开始监听 {roomid}", "status": self.status()}

    async def stop_listen(self) -> Dict[str, Any]:
        self.listening = False
        if self.client is not None:
            try:
                await self.client.stop_and_close()
            except Exception:
                pass
            self.client = None
        if self.listener_task is not None:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except Exception:
                pass
            self.listener_task = None
        self.connected = False
        bus.publish_sync("status", **self.status())
        self.log("[信息] 已停止监听")
        return {"ok": True, "message": "已停止监听", "status": self.status()}

    async def _listen_loop(self, room_id: int) -> None:
        assert self.session is not None
        client = blivedm.BLiveClient(room_id, session=self.session)
        handler = DanmakuHandler(self)
        client.set_handler(handler)
        self.client = client
        client.start()
        self.connected = True
        bus.publish_sync("status", **self.status())
        try:
            await client.join()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.log(f"[错误] 监听异常: {exc}", level="error")
        finally:
            self.connected = False
            self.listening = False
            try:
                await client.stop_and_close()
            except Exception:
                pass
            if self.client is client:
                self.client = None
            bus.publish_sync("status", **self.status())

    def skip_song(self) -> Dict[str, Any]:
        ok = bool(webbrowser.open(lxmusic.player_skipNext()))
        message = "已发送切歌指令" if ok else "切歌失败，请确认 LX Music 已启动"
        self.log(f"[操作] {message}")
        bus.publish_sync("action", action="skip", ok=ok, message=message)
        return {"ok": ok, "message": message}

    async def request_song(self, name: str, singer: str = "", requester: str = "手动点歌") -> Dict[str, Any]:
        name = (name or "").strip()
        singer = (singer or "").strip()
        if not name:
            return {"ok": False, "message": "歌名不能为空"}
        if name in self.blacklist:
            msg = f"歌曲在黑名单中: {name}"
            self.log(f"[点歌] {msg}", level="warn")
            return {"ok": False, "message": msg}
        await self._play_song(name, singer, requester=requester, source_label="手动")
        return {"ok": True, "message": "点歌请求已提交"}

    async def _play_song(
        self,
        song_name: str,
        song_singer: str = "",
        requester: str = "",
        source_label: str = "弹幕",
    ) -> None:
        self.stats["song_total"] += 1
        bus.publish_sync(
            "song_request",
            name=song_name,
            singer=song_singer,
            requester=requester,
            source=source_label,
        )
        for module, label in SEARCH_SOURCES:
            song_info = await module.search_and_get_first(song_name, song_singer)
            if not song_info:
                continue
            self.log(f"[点歌] {label}找到: {song_info['name']} - {song_info['singer']}")
            submitted = song_handler.play_song(song_info)
            status = "已提交到 LX Music" if submitted else "提交失败，请确认 LX Music 已启动"
            level = "info" if submitted else "error"
            self.log(f"[点歌] {status}: {song_info['name']} - {song_info['singer']}", level=level)
            item = {
                "ts": int(time.time() * 1000),
                "name": song_info.get("name", song_name),
                "singer": song_info.get("singer", song_singer),
                "source": song_info.get("source", ""),
                "source_label": label,
                "requester": requester,
                "ok": submitted,
            }
            self.song_queue.append(item)
            if submitted:
                self.stats["song_success"] += 1
            else:
                self.stats["song_failed"] += 1
            bus.publish_sync("song_result", **item)
            bus.publish_sync("status", **self.status())
            return

        self.log("[点歌] 所有源均无结果，使用默认搜索", level="warn")
        scheme = lxmusic.music_searchPlay(name=song_name, singer=song_singer, playLater=True)
        submitted = bool(webbrowser.open(url=scheme))
        status = "已提交到 LX Music" if submitted else "提交失败，请确认 LX Music 已启动"
        self.log(f"[点歌] {status}: {song_name} - {song_singer}", level="info" if submitted else "error")
        item = {
            "ts": int(time.time() * 1000),
            "name": song_name,
            "singer": song_singer,
            "source": "searchPlay",
            "source_label": "默认搜索",
            "requester": requester,
            "ok": submitted,
        }
        self.song_queue.append(item)
        if submitted:
            self.stats["song_success"] += 1
        else:
            self.stats["song_failed"] += 1
        bus.publish_sync("song_result", **item)
        bus.publish_sync("status", **self.status())


class DanmakuHandler(blivedm.BaseHandler):
    def __init__(self, runtime: AppRuntime):
        super().__init__()
        self.runtime = runtime

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        msg = message.msg
        uname = message.uname
        admin = message.admin
        self.runtime.stats["danmaku_total"] += 1
        self.runtime.log(f"[{message.timestamp}] {uname}：{msg}")
        bus.publish_sync(
            "danmaku",
            user=uname,
            msg=msg,
            admin=bool(admin),
            timestamp=message.timestamp,
        )

        if msg == "下一首" and admin == 1:
            self.runtime.skip_song()
            return

        diange = re.match(r"点歌\s+(\S+)(?:\s+(\S+))?", msg)
        if not diange:
            return
        song_name = diange.group(1)
        song_singer = diange.group(2) if diange.group(2) else ""
        if song_name in self.runtime.blacklist:
            self.runtime.log(f"发现屏蔽词:{song_name},发送者:{uname}", level="warn")
            return
        self.runtime.log(f"收到点歌请求: {song_name} 歌手:{song_singer}")
        asyncio.create_task(
            self.runtime._play_song(song_name, song_singer, requester=uname, source_label="弹幕")
        )


runtime = AppRuntime()
