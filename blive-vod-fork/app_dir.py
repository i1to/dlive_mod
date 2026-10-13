# -*- coding: utf-8 -*-
"""
应用目录工具 - 统一获取配置文件路径
优先级：
1. 环境变量 BLIVE_DATA_DIR（桌面端由 Electron 注入，指向 exe 所在目录）
2. PyInstaller 打包后：exe 所在目录
3. 开发环境：项目根目录
"""
import os
import sys


def get_app_dir() -> str:
    """获取应用目录（配置文件、黑名单等用户文件存放位置）"""
    override = os.environ.get("BLIVE_DATA_DIR", "").strip()
    if override:
        try:
            os.makedirs(override, exist_ok=True)
            return override
        except OSError:
            pass
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，exe 所在目录
        return os.path.dirname(sys.executable)
    # 开发环境，项目根目录
    return os.path.dirname(os.path.abspath(__file__))


def get_config_path() -> str:
    """获取 config.json 完整路径"""
    return os.path.join(get_app_dir(), "config.json")


def get_blacklist_path() -> str:
    """获取歌曲黑名单文件完整路径"""
    return os.path.join(get_app_dir(), ".A歌曲黑名单.txt")
