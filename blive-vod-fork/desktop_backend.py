# -*- coding: utf-8 -*-
"""桌面模式入口：启动 API 后端供 Electron 调用。"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

import config
from web_server import start_api_server, stop_api_server


class _QuietUnknownCommand(logging.Filter):
    def filter(self, record):
        return not (
            record.name == "blivedm"
            and record.levelno < logging.ERROR
            and "unknown cmd=" in record.getMessage()
        )


def _force_utf8_stdio() -> None:
    """统一 stdout/stderr 为 UTF-8，避免 Electron 读取中文日志时乱码。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


async def _run(host: str, port: int) -> None:
    _force_utf8_stdio()
    logging.getLogger("blivedm").addFilter(_QuietUnknownCommand())
    config.create_config()
    runner, bound_port = await start_api_server(host=host, port=port)
    # 给 Electron 主进程读取
    print(json.dumps({"type": "ready", "host": host, "port": bound_port}, ensure_ascii=False), flush=True)
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await stop_api_server(runner)


def main() -> None:
    parser = argparse.ArgumentParser(description="B站直播点歌机桌面后端")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=17820)
    args = parser.parse_args()
    try:
        asyncio.run(_run(args.host, args.port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
