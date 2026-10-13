# dlive_mod · 抖音直播点歌姬

监听抖音直播间弹幕，将观众的点歌请求提交到 [落雪音乐桌面版](https://github.com/lyswhut/lx-music-desktop)，以稍后播放模式排队播放。

目前提供 Python 命令行版本，支持指定歌手、歌曲黑名单、按用户ID授权切歌、断线重连，以及只打印弹幕的验证模式。桌面版源码保留作为参考。

## 使用

安装 Python 3.9+，并先启动落雪音乐桌面版。在 `blive-vod` 目录执行：

```bash
python -m pip install -r requirements.txt

# 将“直播间号”替换为抖音网页版直播地址后的数字
python main.py https://live.douyin.com/直播间号 --listen-only

# 确认能收到弹幕后，启动点歌模式
python main.py https://live.douyin.com/直播间号
```

弹幕指令：`点歌 青花瓷`、`点歌 青花瓷 周杰伦`；`下一首` 仅允许配置的用户ID白名单使用。

配置、测试及打包说明见 [blive-vod/README.md](blive-vod/README.md)。真实直播接口和 Windows 播放效果仍需实际环境验证。

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
