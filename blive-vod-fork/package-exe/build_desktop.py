# -*- coding: utf-8 -*-
"""
桌面端打包脚本
步骤：
1. PyInstaller 将 desktop_backend.py 打包为 package-exe/backend/blive-vod-backend.exe（onedir）
2. electron-builder 将 Electron 前端 + 后端一起打包为单个绿色 exe

产物：package-exe/dist-desktop/blive-vod-desktop-<版本>.exe（双击即用）
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
DESKTOP_DIR = os.path.join(PROJECT_ROOT, "desktop")
BACKEND_DIR = os.path.join(HERE, "backend")
BUILD_DIR = os.path.join(HERE, "build-backend")
BACKEND_NAME = "blive-vod-backend"

HIDDEN_IMPORTS = (
    "aiohttp",
    "asyncio",
    "http.cookies",
    "blivedm",
    "blivedm.clients",
    "blivedm.clients.web",
    "blivedm.clients.ws_base",
    "blivedm.models",
    "blivedm.models.web",
    "blivedm.handlers",
    "blivedm.utils",
    "web_server",
    "app_runtime",
    "event_bus",
    "qr_code",
    "qrcode",
    "qrcode.main",
    "qrcode.image.base",
    "qrcode.image.svg",
)

# 仅排除与点阵无关的重量级依赖，避免 exe 体积膨胀
# 注意：不可排除 qrcode.compat.png，否则 qrcode.image.pure 连带 qrcode.main 导入失败
EXCLUDE_MODULES = (
    "PIL",
    "qrcode.image.pil",
    "qrcode.image.styledpil",
    "numpy",
    "matplotlib",
    "scipy",
    "pandas",
    "tkinter",
    "pytest",
    "IPython",
)


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
        print(f"[打包] PyInstaller 版本: {PyInstaller.__version__}")
    except ImportError:
        print("[打包] 正在安装 PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build_backend():
    """打包 Python 后端（onedir，启动快、无需解压）"""
    ensure_pyinstaller()
    if os.path.isdir(BACKEND_DIR):
        shutil.rmtree(BACKEND_DIR, ignore_errors=True)

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        # 保留控制台子系统以便 stdout 握手，Electron 端已隐藏窗口
        "--console",
        "--name", BACKEND_NAME,
        "--distpath", BACKEND_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", HERE,
    ]
    for module in HIDDEN_IMPORTS:
        args += ["--hidden-import", module]
    for module in EXCLUDE_MODULES:
        args += ["--exclude-module", module]
    args.append(os.path.join(PROJECT_ROOT, "desktop_backend.py"))

    print("[打包] 开始打包 Python 后端...")
    subprocess.check_call(args, cwd=PROJECT_ROOT)

    # PyInstaller 会生成 backend/<name>/ 子目录，展平到 backend/ 便于 Electron 引用
    nested = os.path.join(BACKEND_DIR, BACKEND_NAME)
    if os.path.isdir(nested):
        for item in os.listdir(nested):
            shutil.move(os.path.join(nested, item), os.path.join(BACKEND_DIR, item))
        os.rmdir(nested)

    exe_path = os.path.join(BACKEND_DIR, f"{BACKEND_NAME}.exe")
    if not os.path.isfile(exe_path):
        raise RuntimeError(f"后端打包失败，未找到 {exe_path}")
    print(f"[打包] 后端产物: {exe_path}")


def npm(*args):
    cmd = shutil.which("npm") or shutil.which("npm.cmd")
    if not cmd:
        raise RuntimeError("未找到 npm，请先安装 Node.js 18+")
    subprocess.check_call([cmd, *args], cwd=DESKTOP_DIR, shell=False)


def build_desktop():
    """打包 Electron 前端为单文件 exe"""
    if not os.path.isdir(os.path.join(DESKTOP_DIR, "node_modules")):
        print("[打包] 安装前端依赖...")
        npm("install", "--no-audit", "--no-fund")
    print("[打包] 开始打包 Electron 桌面端...")
    npm("run", "dist")


def main():
    build_backend()
    build_desktop()

    with open(os.path.join(DESKTOP_DIR, "package.json"), "r", encoding="utf-8") as f:
        version = json.load(f)["version"]
    output = os.path.join(HERE, "dist-desktop", f"blive-vod-desktop-{version}.exe")

    print("\n" + "=" * 56)
    print("[完成] 桌面端打包成功！")
    print(f"[输出] {output}")
    print("[说明] 单个 exe，双击即启动图形界面，无需 Python / Node 环境")
    print("[说明] 首次运行会在 exe 同级目录生成 config.json 与歌曲黑名单文件")
    print("=" * 56)


if __name__ == "__main__":
    main()
