# dlive_mod · 抖音直播点歌姬

监听抖音直播间弹幕，将观众的点歌请求提交到 [落雪音乐桌面版](https://github.com/lyswhut/lx-music-desktop)，以稍后播放模式排队播放。

目前提供 Python 命令行版本，支持指定歌手、歌曲黑名单、按用户ID授权切歌、断线重连，以及只打印弹幕的验证模式。桌面版源码保留作为参考。

## 使用

推荐 Windows 10/11 x64、Python 3.11 和 LX Music 桌面版 2.8.0+。在解压后的项目根目录打开 PowerShell：

```powershell
py -3.11 -X utf8 -m pip install --use-feature=truststore -r .\blive-vod\requirements.txt

# 先验证弹幕，将“直播间号”替换为抖音网页版直播地址后的数字
py -3.11 -X utf8 .\main.py https://live.douyin.com/直播间号 --listen-only

# Ctrl+C 停止验证，先启动 LX Music，再运行点歌模式
py -3.11 -X utf8 .\main.py https://live.douyin.com/直播间号
```

`--listen-only` 只显示弹幕，不点歌、不切歌。点歌指令为 `点歌 青花瓷` 或 `点歌 青花瓷 周杰伦`；`下一首` 仅允许用户ID白名单使用。

## 安装与配置 LX Music

1. 到 [LX Music 官方 Releases](https://github.com/lyswhut/lx-music-desktop/releases) 下载适合 Windows 的桌面安装包（通常选 x64），安装并启动。建议使用安装版，确保 Windows 注册了 `lxmusic://` 协议。
2. 根据 [LX Music 官方文档](https://lxmusic.toside.cn/) 的说明配置可用音源。点歌机不提供音源脚本，也不会自动安装音源。
3. 先在 LX Music 内手动搜索并播放一首歌，确认音源、声音输出正常。能搜索到歌曲不代表一定能播放。
4. 再启动点歌模式。在直播间发送 `点歌 青花瓷 周杰伦`，检查终端是否显示“已接收”“已提交到落雪音乐”，并观察 LX Music 的播放列表和实际播放。

本项目通过 [LX Music Scheme URL](https://lxmusic.toside.cn/desktop/scheme-url) 调用 `music/searchPlay`，传入歌名、歌手、音源等信息及 `playLater=true`。LX Music 会再次搜索并处理播放请求；实际队列和播放行为需在播放器中确认。程序不读取播放器状态，“已提交”不能证明歌曲已播放。

## 注意事项与故障排查

- Windows 上若 `python` 报“拒绝访问”，使用上面的 `py -3.11` 命令。`-X utf8` 可避免中文系统的编码问题。
- 使用 `https://live.douyin.com/数字` 直播地址，不使用抖音号或分享短链接；当前通过访客方式接收弹幕，无网页扫码登录步骤。
- 若收到弹幕中的点歌指令却没有搜索日志，检查是否仍带着 `--listen-only`。
- 若提示无法打开 `lxmusic://`、弹出“选择应用”或提交失败，检查 LX Music 安装及协议注册；重新运行官方安装包后重试。提交成功但不能播放时，先验证该歌曲在 LX Music 内能否手动播放。
- 若出现证书错误或 `ProxyError`，检查代理、TUN 模式、HTTPS 检查软件及网络。本次联调曾成功收到弹幕，但不能据此保证其他网络始终可用。可在当前 PowerShell 临时执行 `$env:NO_PROXY = "*"` 后重试；这只绕过程序的自动代理设置，不关闭 TUN 或网络层拦截，关闭终端恢复。不要关闭证书校验。
- 根目录 `main.py` 转交给 `blive-vod/main.py` 运行。配置与黑名单在 `blive-vod/` 中；重新解压到其他目录不会自动带上旧配置。
- 歌名和歌手以空格分隔，当前不支持包含空格的多词歌名。搜索按酷狗 → 网易云 → QQ 顺序进行，每源最多等待20秒，失败后回退；请求按收到顺序处理。

详细配置、切歌白名单及测试说明见 [blive-vod/README.md](blive-vod/README.md)。用户已验证真实抖音弹幕接收；离线点歌链路测试通过，Windows 实际播放、连续点歌排队和 EXE 仍需本机验证。

## 引用项目

感谢以下项目提供的基础代码和能力：

| 项目 | 本项目中的用途 |
| --- | --- |
| [xuan06zyx/blive-vod](https://github.com/xuan06zyx/blive-vod) | 原始弹幕点歌项目，提供点歌和播放器对接基础 |
| [QDLinux/blive-vod-fork](https://github.com/QDLinux/blive-vod-fork) | 点歌机改进版本，提供多源搜索、登录及桌面版参考 |
| [saermart/DouyinLiveWebFetcher](https://github.com/saermart/DouyinLiveWebFetcher) | 抖音直播弹幕接入、消息解码和签名资源 |
| [lyswhut/lx-music-desktop](https://github.com/lyswhut/lx-music-desktop) | 外部音乐播放器，通过 Scheme URL 接收点歌和切歌指令 |
| [xfgryujk/blivedm](https://github.com/xfgryujk/blivedm) | 原项目使用的B站弹幕库，源码保留，当前抖音入口不使用 |

引用源码保留各自许可证。内置抖音接入代码采用 AGPL-3.0，版本及修改记录见 [UPSTREAM.md](blive-vod/douyin_vendor/UPSTREAM.md)，许可证见 [LICENSE](blive-vod/douyin_vendor/LICENSE)。
