# B站直播点歌机桌面端（Electron）

Clash 风格深色控制台 + Python 异步后端。

项目已移除旧的命令行 / tkinter 入口，桌面端是唯一运行方式。

## 结构

```
desktop/
  package.json
  src/main.js          # Electron 主进程，拉起 Python 后端
  src/preload.js
  renderer/            # Clash 风格 SPA
desktop_backend.py     # 桌面后端入口
web_server.py          # HTTP/WS API
app_runtime.py         # 登录/监听/点歌运行时
event_bus.py           # 事件总线
```

## 开发启动

1. 安装 Python 依赖（项目根目录）

```bash
pip install -r requirements.txt
```

2. 安装 Electron 依赖

```bash
cd desktop
npm install
```

国内网络下载 Electron 二进制较慢时，可使用镜像：

```powershell
$env:ELECTRON_MIRROR="https://registry.npmmirror.com/-/binary/electron/"
npm install --registry=https://registry.npmmirror.com
```

3. 启动桌面端

```bash
npm start
```

默认会执行：

- `python desktop_backend.py --host 127.0.0.1 --port 17820`
- Electron 打开 `renderer/index.html` 并连接该端口

如需指定 Python 路径：

```bash
# PowerShell
$env:BLIVE_PYTHON="D:\path\to\python.exe"
npm start
```

## 功能页

- 概览：房间状态、统计、手动点歌
- 扫码弹窗：后端推送二维码点阵，渲染层用 canvas 绘制，不调系统浏览器
- 点歌队列：最近点歌结果
- 弹幕日志：实时日志流
- 设置：房间号、黑名单热更新

## 布局与交互

- 外层不滚动（`html, body { overflow: hidden }`），滚动只发生在 `.page-scroll` 或 `.panel.fill > .panel-body`
- 按钮忙碎态：`runAction()` 自动禁用按钮、加 spinner，结束后 `syncActionButtons()` 根据后端状态重算可用性与文案
- 提示统一用 toast（`#toastHost`），错误同时写入日志页
- 表单 `novalidate` + JS 校验；房间号非法时自动跳转设置页并聚焦输入框
- 日志页支持自动滚动开关与清空；黑名单实时显示条目数
- `Escape` 关闭扫码弹窗并取消登录；WebSocket 断开时侧栏徽章置为未连接
- 宽度 ≤ 1040px 侧栏折叠为图标栏，高度 ≤ 620px 压缩间距


## API 摘要

- `GET /api/status`
- `POST /api/listen/start`
- `POST /api/listen/stop`
- `POST /api/login`（启动登录流程，非阻塞）
- `POST /api/login/cancel`（取消登录并关闭二维码弹窗）
- `POST /api/skip`
- `POST /api/song/request`
- `GET/POST /api/config`
- `GET/POST /api/blacklist`
- `WS /ws`

## 打包为单个 exe

在项目根目录执行：

```bash
cd package-exe
python build_desktop.py
```

- PyInstaller 打包 `desktop_backend.py` → `package-exe/backend/blive-vod-backend.exe`
- electron-builder 以 portable 目标打包 → `package-exe/dist-desktop/blive-vod-desktop-<版本>.exe`
- 运行时主进程优先使用内置后端 exe，找不到时回退到 `python desktop_backend.py`
- 用户数据目录优先取 `PORTABLE_EXECUTABLE_DIR`（用户双击 exe 的位置），通过 `BLIVE_DATA_DIR` 传给后端

## 启动流程

1. 显示 `renderer/splash.html` 启动页
2. spawn 后端进程，读取 stdout 的 `{"type":"ready","port":...}` 握手
3. 握手失败时轮询 `/api/health` 兜底，仍失败则弹出错误对话框并附最近后端日志
4. 主窗口 `ready-to-show` 后关闭启动页
5. 窗口关闭 / 应用退出时 `taskkill /t` 结束后端进程树

## 扫码登录流程

1. 前端点「检查登录」→ `POST /api/login`，后端起后台任务并立即返回
2. `bili_login.qr_login` 通过 presenter 抽象把二维码交给 `EventBusQRPresenter`
3. `qr_code.make_matrix()` 生成点阵，经 WebSocket `qr` 事件推送
4. 渲染层在 `#qrCanvas` 上绘制点阵，`state` 变化时更新提示文案
5. 登录成功 / 过期 / 取消时后端推送 `visible: false`，弹窗关闭
6. `qrcode` 库不可用时弹窗提示生成失败，需安装依赖后重试
