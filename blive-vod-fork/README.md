<div align="center">

<h1>Blive-Vod</h1>

<p><strong>阿B直播弹幕点歌机</strong></p>

<p>
  <a href="https://github.com/QDLinux/blive-vod-fork/releases/latest"><img src="https://img.shields.io/github/v/release/QDLinux/blive-vod-fork?style=flat-square&label=Release" alt="Latest release"></a>
  <a href="https://github.com/QDLinux/blive-vod-fork/releases/latest"><img src="https://img.shields.io/github/downloads/QDLinux/blive-vod-fork/total?style=flat-square&label=Downloads" alt="Downloads"></a>
  <a href="https://t.me/blive_vod"><img src="https://img.shields.io/badge/Telegram-%E5%8A%A0%E5%85%A5%E9%A2%91%E9%81%93-26A5E4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram channel"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/QDLinux/blive-vod-fork?style=flat-square" alt="License"></a>
</p>

<p>
  <a href="https://github.com/QDLinux/blive-vod-fork/releases/latest"><strong>下载最新版</strong></a>
  ·
  <a href="https://t.me/blive_vod"><strong>Telegram 频道</strong></a>
  ·
  <a href="https://github.com/QDLinux/blive-vod-fork/issues"><strong>问题反馈</strong></a>
</p>

</div>

> [!IMPORTANT]
> 项目仍在开发测试阶段，建议具备一定计算机基础的用户使用。版本发布和 Windows EXE 下载通知会同步至 [Telegram 频道](https://t.me/blive_vod)。

## 一句话介绍

监听 B 站直播间弹幕，把观众点的歌通过 [落雪音乐桌面版](https://github.com/lyswhut/lx-music-desktop/releases) 排队播放。
桌面端为 Electron + Clash 风格控制台，单个 exe 双击即用，无需 Python 环境。

> 旧的命令行 / tkinter 版本（`main.py`、`启动点歌机.bat`、命令行 exe）已在本版本删除，现在只保留 Electron 桌面端。

## 功能特性

- [x] 实时监控直播间弹幕
- [x] 弹幕点歌（支持指定歌手）
- [x] 弹幕切歌（房管权限）
- [x] 歌曲黑名单过滤（界面内热更新）
- [x] **B站自动登录**（内嵌扫码 + Cookie 持久化 + 自动刷新）
- [x] **多源音乐搜索**（酷狗 → 网易云 → QQ音乐，优先级依次降低）
- [x] **稍后播放模式**（点歌不打断当前播放，排队等待）
- [x] **房间号自动获取**（登录后自动取账号直播间号）
- [x] 异步点歌处理（不阻塞弹幕监听）
- [x] **桌面图形界面**（Electron + Clash 风格控制台）
- [x] **打包为单个 EXE**（无需 Python / Node 环境，开箱即用）
- [ ] 前端歌单管理与音源优先级拖拽排序

## 开箱使用

环境要求：Windows 10/11 x64，已安装并运行落雪音乐桌面版 2.8.0+。

1. 先启动 [落雪音乐桌面版](https://github.com/lyswhut/lx-music-desktop/releases)（**必须先启动**）
2. 双击 `blive-vod-desktop-<版本>.exe`
3. 启动页读条结束后自动进入控制台
4. 点「检查登录」，在弹窗内用B站APP扫码，登录成功弹窗自动关闭
5. 在「设置」确认直播间号（登录后会自动带出），回到「概览」点「开始监听」
6. 首次运行会在 exe 同级目录生成 `config.json` 与 `.A歌曲黑名单.txt`

## 界面说明

Clash 风格深色控制台，Electron 界面 + 本地 Python API 后端。

功能页：
- 概览：监听状态、登录账号、统计、手动点歌
- 点歌队列：最近点歌结果与来源
- 弹幕日志：WebSocket 实时日志流
- 设置：房间号与歌曲黑名单热更新

界面细节：
- 登录二维码直接在应用弹窗里绘制，不跳系统浏览器
- 每个功能页独立滚动，窗口不会出现整页横向/纵向溢出
- 按钮点击后进入忙碎态（禁用 + 转圈），完成后按运行状态自动切换文案
- 操作结果以 toast 提示，输入非法时高亮输入框并跳转到对应页面
- 窗口宽度小于 1040px 时侧栏折叠为图标栏

## 使用说明

### 弹幕点歌

在直播间发送弹幕：
- `点歌 青花瓷` — 搜索并播放“青花瓷”
- `点歌 青花瓷 周杰伦` — 指定歌手，更精确

点歌不会打断当前播放的歌曲，会排队等待当前歌曲播放完毕后再播放。
搜索优先级：酷狗 → 网易云 → QQ音乐，找到即播放，无需等待所有源返回。

### 弹幕切歌（房管专属）

拥有房管权限的用户发送：`下一首`

### 登录管理

- 点「检查登录」会优先使用已保存的 Cookie，失效时自动刷新，仍失败则弹出扫码弹窗
- 扫码期间可点「取消登录」或按 `Escape` 中断
- 登录凭证保存在 `config.json`，不会提交到仓库

### 歌曲黑名单

在「设置」页编辑，一行一个歌名，保存后立即生效（无需重启）。
对应文件为 exe 同级目录的 `.A歌曲黑名单.txt`。

## 源码开发

### 环境要求

- Windows 10/11 x64
- Python 3.9+ ([下载地址](https://www.python.org/downloads/windows/))
- Node.js 18+
- 落雪音乐桌面版 2.8.0+

### 启动

```bash
pip install -r requirements.txt

cd desktop
npm install
npm start
```

说明：
- 桌面后端入口：`desktop_backend.py`
- API / WebSocket：`web_server.py`（默认 `127.0.0.1:17820`，被占用时自动顺延）
- 若 Python 不在 PATH，可设置环境变量 `BLIVE_PYTHON` 指向解释器
- 数据目录可用 `BLIVE_DATA_DIR` 覆盖
- 二维码点阵由 `qr_code.py` 生成，通过 WebSocket `qr` 事件推给前端
- 详细文档见 [desktop/README.md](desktop/README.md)

### 打包 EXE

```bash
cd package-exe
python build_desktop.py
```

产物：`package-exe/dist-desktop/blive-vod-desktop-<版本>.exe`（约 90 MB），内置 Electron 界面与 PyInstaller 后端，复制单个 exe 即可分发。
详见 [package-exe/README.md](package-exe/README.md)。

## 文件说明

```
blive-vod-fork/
├── desktop/                 # Electron 桌面端（主进程 + Clash 风格渲染层）
│   ├── src/main.js          # 主进程，拉起 Python 后端
│   ├── src/preload.js
│   └── renderer/            # SPA 页面与样式
├── desktop_backend.py       # 后端入口（API 服务 + ready 握手）
├── web_server.py            # HTTP / WebSocket API
├── app_runtime.py           # 登录 / 监听 / 点歌 运行时
├── event_bus.py             # 事件总线（日志 / 状态 / 二维码广播）
├── bili_login.py            # B站登录（扫码 / Cookie 管理）
├── qr_code.py               # 二维码点阵生成
├── kg_search.py             # 酷狗音乐搜索
├── wy_search.py             # 网易云音乐搜索
├── tx_search.py             # QQ音乐搜索
├── search_common.py         # 搜索公共工具
├── song_handler.py          # 搜索结果处理（统一播放接口）
├── lxmusic.py               # LX Music Scheme URL 封装
├── app_dir.py               # 数据目录工具
├── config.py                # 配置 / 黑名单自动生成
├── blivedm/                 # B站直播弹幕客户端库（第三方）
├── package-exe/             # EXE 打包脚本
├── config.json              # 配置模板（本地运行后写入房间号与 Cookie）
└── requirements.txt         # Python 依赖列表
```

## 常见问题

### Q: 落雪音乐无法播放歌曲？
A: 参考 [LX Music Issues #5](https://github.com/lyswhut/lx-music-desktop/issues/5#issuecomment-2099784225)

### Q: 弹幕用户名显示为打码状态？
A: 点「检查登录」完成扫码即可显示完整用户名。登录信息会自动保存，后续启动无需重新登录。

### Q: Cookie 过期怎么办？
A: 程序会自动检测并刷新。如果刷新失败，会弹出扫码弹窗重新登录。

### Q: 如何更换监听的直播间？
A: 在「设置」页修改直播间号并保存，重新点「开始监听」。

### Q: 启动时提示无法启动后端？
A: 弹窗会附带最近的后端日志。常见原因是端口被占或杀毒软件拦截，添加信任后重试。

## 免责声明

本软件仅供学习交流使用，请于下载后24小时内删除，不得用于任何商业用途，否则后果自负。

## 问题反馈

- 使用问题与功能建议：[GitHub Issues](https://github.com/QDLinux/blive-vod-fork/issues)
- 版本发布与 EXE 同步：[Telegram 频道](https://t.me/blive_vod)

## 致谢

- 原项目：[xuan06zyx/blive-vod](https://github.com/xuan06zyx/blive-vod)
- B站直播弹幕库：[xfgryujk/blivedm](https://github.com/xfgryujk/blivedm)
- 音乐播放器：[lyswhut/lx-music-desktop](https://github.com/lyswhut/lx-music-desktop)

<br>
<div align="center">
  <strong>如果这个项目对你有帮助，欢迎点个 Star。</strong>
</div>
