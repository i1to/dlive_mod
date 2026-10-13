# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

B站直播弹幕点歌机 — 监听B站直播间弹幕，通过 LX Music 桌面版的 Scheme URL 协议实现弹幕点歌/切歌。
唯一运行形态：Electron 桌面端（Clash 风格控制台）+ Python 异步后端，Windows 环境。
旧的命令行 / tkinter 入口（`main.py`、`app_ui.py`、`qr_page.py`、`package-exe/build.py`）已删除，不要重新引入。

## Commands

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖并启动桌面端
cd desktop && npm install && npm start

# 单独启动后端（调试用）
python desktop_backend.py --host 127.0.0.1 --port 17820

# 语法检查（无测试框架）
python -c "import py_compile; py_compile.compile('文件名.py', doraise=True)"
node --check desktop/src/main.js

# 打包单文件 exe
cd package-exe && python build_desktop.py
```

## Architecture

### 核心流程

```
desktop/src/main.js (Electron 主进程)
  → spawn blive-vod-backend.exe / python desktop_backend.py
  → web_server.py 提供 HTTP / WebSocket API
  → app_runtime.py（AppRuntime）
      → bili_login.ensure_login(session, qr_presenter) — cookie 加载/刷新/扫码
      → blivedm.BLiveClient — WebSocket 连接直播间
      → DanmakuHandler — 解析弹幕指令
      → 多源搜索 (kg > wy > tx) → song_handler → LX Music
  → event_bus.py 广播日志 / 状态 / 二维码事件到渲染层
```

### 模块职责

- **desktop_backend.py** — 后端入口，启动 API 服务并向 stdout 打印 `{"type":"ready","host":...,"port":...}` 握手
- **web_server.py** — aiohttp HTTP/WS API（默认 `127.0.0.1:17820`，被占时自动顺延 20 个端口）
- **app_runtime.py** — `AppRuntime` 单例 `runtime`：登录 / 监听 / 点歌 / 配置热更新；`DanmakuHandler` 处理弹幕；`EventBusQRPresenter` 推送二维码
- **event_bus.py** — 500 条环形缓冲 + WebSocket 广播，单例 `bus`
- **bili_login.py** — B站登录全流程（cookie 持久化到 config.json、refresh、扫码），`ensure_login(session, qr_presenter)` 必传展示器
- **qr_code.py** — `make_matrix(data)` 用 qrcode 库生成布尔点阵（`ERROR_CORRECT_M`, border=2），失败返回 None
- **lxmusic.py** — LX Music Scheme URL 协议封装（文档: https://lxmusic.toside.cn/desktop/scheme-url）
- **song_handler.py** — 统一将搜索结果转为 `music/searchPlay` 调用，`playLater=True`（排队播放）
- **kg_search.py / wy_search.py / tx_search.py** — 酷狗/网易云/QQ音乐搜索，统一 `search_and_get_first(name, singer)`，共用 `search_common.py`
- **app_dir.py** — 数据目录：`BLIVE_DATA_DIR` → exe 同级目录 → 项目根目录
- **config.py** — 首次运行生成 config.json 与黑名单文件
- **blivedm/** — B站直播弹幕WebSocket客户端库（第三方，不要修改）

### 搜索模块标准返回格式

每个搜索模块的 `search_and_get_first()` 返回：
```python
{
    "source": "kg" | "wy" | "tx",
    "name": str, "singer": str, "songmid": str,
    "img": str, "albumId": str, "interval": str,  # mm:ss
    "albumName": str, "types": list, "hash": str
}
```

### 配置文件 config.json

仓库内仅保留空模板（`roomid` 与 `cookies` 字段均为空字符串）。
本地运行后会写入真实房间号与登录凭证，**绝不提交**（已标记 `skip-worktree`）。

### 弹幕指令

- `点歌 歌名 [歌手]` — 点歌，歌手可选
- `下一首` — 切歌（限房管）

## Key Conventions

- 所有网络请求使用 `aiohttp`，异步处理
- 与 LX Music 通信方式：生成 Scheme URL 后通过 `webbrowser.open()` 调用
- 搜索优先级固定为 kg → wy → tx，前一个有结果就不再查后续源
- 文件编码统一 UTF-8
- 项目语言为中文（注释、提示信息、文档）

## Desktop Architecture (Electron)

- 开发启动：`cd desktop && npm install && npm start`
- 默认 API 端口：`127.0.0.1:17820`（占用时自动顺延 20 个端口）
- 自定义解释器：环境变量 `BLIVE_PYTHON`
- 渲染层启用 CSP，禁止内联样式与内联脚本，新增样式请写入 `desktop/renderer/styles.css`
- 启动流程：splash → spawn 后端 → stdout `ready` 握手（30s）→ `/api/health` 轮询兜底 → 失败弹 `dialog.showErrorBox` 附最近 15 行日志
- 退出时 `taskkill /f /t` 结束后端进程树
- 扫码登录：`app_runtime.EventBusQRPresenter` 将点阵经 WebSocket `qr` 事件推给前端，渲染层 canvas 绘制；`qrcode` 不可用时弹窗提示错误（无浏览器回退）
- 打包：`package-exe/build_desktop.py`（PyInstaller 后端 + electron-builder portable 单文件 exe）
- 注意：`EXCLUDE_MODULES` 不可排除 `qrcode.compat.png`，否则 `qrcode.main` 导入失败

### 渲染层布局约定

- 布局骨架：`.app` = `.sidebar` + `.main`（`.topbar` + `.content`），`html, body` 锁定 `overflow: hidden`
- 滚动只在内层容器：页面用 `.page-scroll`，充满型面板用 `.panel.fill > .panel-body`
- 异步操作统一走 `runAction(button, task)`（内部 `beginBusy` 加 `busy` 类 + `aria-busy`），完成后调 `syncActionButtons()` 根据 `listening` / `logging_in` / `qr.visible` 推导按钮态
- 表单均加 `novalidate`，校验由 JS 处理（`invalid` 类 + `toast()`），避开浏览器原生校验拦截
- 响应式断点：`max-width: 1040px` 侧栏折叠为 76px 图标栏；`max-height: 620px` 压缩纵向间距
- 输入框获得焦点时不被后端推送的状态覆盖
