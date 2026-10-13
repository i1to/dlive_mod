# 打包为 EXE

只有一种产物：Electron 图形界面的单文件 exe。

## 构建

```bash
cd package-exe
python build_desktop.py
```

流程：

1. PyInstaller 将 `desktop_backend.py` 打包为 `package-exe/backend/blive-vod-backend.exe`（onedir）
2. electron-builder 将 Electron 界面 + 后端一起打成单个绿色 exe

产物：`package-exe/dist-desktop/blive-vod-desktop-<版本>.exe`（约 90 MB）

分发方式：只复制这一个 exe 到目标电脑，双击启动，无需 Python / Node 环境。
首次运行会在 **exe 同级目录** 生成 `config.json` 与 `.A歌曲黑名单.txt`。

## 环境要求（打包机）

- Python 3.9+ 与 `pip install -r requirements.txt`
- Node.js 18+（脚本会自动执行 `npm install`）
- 国内网络建议先设置镜像：

```powershell
$env:ELECTRON_MIRROR="https://registry.npmmirror.com/-/binary/electron/"
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://registry.npmmirror.com/-/binary/electron-builder-binaries/"
```

## 注意事项

- 目标电脑仍需安装 [落雪音乐桌面版](https://github.com/lyswhut/lx-music-desktop/releases) 2.8.0+ 并保持运行
- 桌面端退出时会自动结束内置后端进程
- 如遇杀毒软件误报，请添加信任
- 构建产物目录（`backend/`、`build-backend/`、`dist-desktop/`）均已 gitignore
