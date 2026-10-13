# 打包抖音点歌机 EXE

在 Windows 上安装项目依赖后运行：

```bash
cd package-exe
python build.py
```

产物为 `package-exe/dist/blive-vod.exe`（onefile 控制台程序）。
打包脚本收集抖音签名 JS、Protobuf 和 MiniRacer 运行资源。
目标电脑需安装并启动落雪音乐桌面版。

先在源码模式测试真实弹幕，再验证 EXE：

```bash
blive-vod.exe https://live.douyin.com/你的直播间号 --listen-only
blive-vod.exe https://live.douyin.com/你的直播间号
```

首次启动在 EXE 同目录生成 `config.json` 和 `.A歌曲黑名单.txt`。
Windows EXE 打包和运行尚需本机验证。使用了上游 AGPL-3.0 接入代码，
分发时应一并提供对应源码和许可证。
