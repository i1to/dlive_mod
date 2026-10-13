# 抖音直播弹幕点歌机

基于 blive-vod 命令行版改造，使用内置的
[DouyinLiveWebFetcher](https://github.com/saermart/DouyinLiveWebFetcher)
接收抖音弹幕，通过落雪音乐桌面版排队播放。

## 安装与验证

推荐 Windows 10/11 x64、Python 3.11、落雪音乐桌面版 2.8.0+。
Windows + Python 3.10 及以上使用 truststore 系统证书验证，覆盖 HTTPS 和 WebSocket；
系统未信任的证书仍会被拒绝。
LX Music 下载、音源配置和 Windows 常见问题见 [根目录 README](../README.md#安装与配置-lx-music)。
以下命令在项目根目录打开 PowerShell 执行：

```powershell
py -3.11 -X utf8 -m pip install --use-feature=truststore -r .\blive-vod\requirements.txt
py -3.11 -X utf8 .\main.py https://live.douyin.com/你的直播间号 --listen-only
```

直播间号是浏览器地址 `live.douyin.com/` 后面的数字，不是抖音号，
也不是旧B站房间号。暂不支持 `v.douyin.com` 分享短链接；请先在浏览器
打开分享链接，复制网页版直播地址。

`--listen-only` 只打印弹幕，不搜索、不播放、不切歌。
在直播间发送普通弹幕和 `点歌 青花瓷`，检查终端是否显示相同内容、
用户名及 `UID`。用 Ctrl+C 退出。

确认能收到弹幕后，先启动落雪音乐，再运行：

```powershell
py -3.11 -X utf8 .\main.py https://live.douyin.com/你的直播间号
```

也可双击 `启动点歌机.bat`。第一次输入房间号，之后使用保存的
`douyin_live_id`。不再调用B站登录或自动获取账号直播间。
上游当前自动获取访客 Cookie；若抖音接口变化或限制访客访问，
仍需针对实际错误调整接入代码。

## 指令与配置

- `点歌 青花瓷`：歌手可选，例如 `点歌 青花瓷 周杰伦`。
- `下一首`：只允许 `skip_user_ids` 白名单内的用户。
- `.A歌曲黑名单.txt`：一行一个完整歌名，修改后重启。

配置与黑名单均保存在 `blive-vod/` 中。`config.json` 配置示例：

```json
{
  "douyin_live_id": "你的网页版直播间号",
  "skip_user_ids": ["从弹幕日志复制的UID"]
}
```

ID 建议填写字符串。切歌授权使用日志中的数字 UID，不使用昵称、
抖音号或房管徽章；当前接入消息中没有可靠的房管权限字段。
旧配置中的B站 `roomid` 不会被当作抖音房间号使用。

请求按收到顺序依次搜索（酷狗 → 网易云 → QQ），找到后提交给落雪；
单源搜索最长等待20秒。等待处理的请求上限100条，超出会打印提示。
重连时按消息ID去重，保留最近2000条ID。直播结束消息到达后停止监听，
其他断线默认5秒后重试。退出时取消尚未完成的点歌请求。
“已提交”表示协议调用成功，不代表播放器已实际播放或音源可用。

## 本机测试清单

1. `--listen-only` 收到自己发送的弹幕，用户ID与文本正确。
2. 退出后正常模式发送点歌，观察落雪排队和实际播放。
3. 测试黑名单；白名单外用户不能切歌，白名单内用户可以切歌。
4. 连发几条点歌，核对提交顺序；断网后恢复，核对重连与重复消息。
5. 测试主播下播、无效房间、Ctrl+C，确认进程正常退出。

离线测试（无需第三方依赖）：

```bash
py -3.11 -X utf8 -m unittest discover -s blive-vod/tests -v
```

用户已验证真实抖音弹幕接收；9项离线测试通过，覆盖实际 Scheme URL 的歌曲参数、稍后播放标志、提交结果及搜索回退。Windows 播放器的真实播放、连续排队及EXE需本机联调。

## 打包与源码

```bash
cd blive-vod/package-exe
py -3.11 build.py
```

输出 `package-exe/dist/blive-vod.exe`，需在Windows上验证。
详细说明见 `package-exe/README.md`。

抖音接入源码与签名资源在 `douyin_vendor/`，来源、版本和修改记录见
`douyin_vendor/UPSTREAM.md`。保留了上游 AGPL-3.0 许可证及来源信息。
原B站模块保留在目录中，当前入口不再使用。
