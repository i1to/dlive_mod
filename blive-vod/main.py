"""抖音直播弹幕点歌机。--listen-only 可单独验证弹幕接口。"""
import argparse
import asyncio
import json
import re
import webbrowser

from app_dir import get_config_path, get_blacklist_path
from douyin_client import listen, normalize_live_id


def parse_song(text):
    match = re.fullmatch(r'点歌\s+(\S+)(?:\s+(\S+))?\s*', text.strip())
    return (match.group(1), match.group(2) or '') if match else None


class SongController:
    def __init__(self, blacklist=(), skip_user_ids=(), listen_only=False):
        self.blacklist = set(blacklist)
        self.skip_user_ids = {str(uid) for uid in skip_user_ids}
        self.listen_only = listen_only
        self.queue = asyncio.Queue(maxsize=100)

    def on_chat(self, event):
        print(f'[弹幕][UID:{event.user_id}] {event.nickname}：{event.text}')
        if self.listen_only:
            return
        if event.text.strip() == '下一首':
            if event.user_id not in self.skip_user_ids:
                print('[切歌] 无切歌权限；请在 skip_user_ids 中配置用户ID')
                return
            from lxmusic import lxmusic
            ok = webbrowser.open(lxmusic().player_skipNext())
            print('[切歌] 已发送切歌指令' if ok else '[切歌] 提交失败，请确认落雪音乐已启动')
            return
        song = parse_song(event.text)
        if not song:
            return
        if song[0] in self.blacklist:
            print(f'[点歌] 已屏蔽歌曲: {song[0]}')
            return
        try:
            self.queue.put_nowait(song)
            print(f'[点歌] 已接收: {song[0]} - {song[1] or "未指定歌手"}；等待处理 {self.queue.qsize()} 条')
        except asyncio.QueueFull:
            print('[点歌] 待处理请求已满，请稍后再试')

    async def worker(self):
        while True:
            name, singer = await self.queue.get()
            try:
                await self.play_song(name, singer)
            except Exception as exc:
                print(f'[点歌] 处理失败: {exc}')
            finally:
                self.queue.task_done()

    async def play_song(self, name, singer):
        import kg_search
        import wy_search
        import tx_search
        import song_handler
        from lxmusic import lxmusic
        for module, label in ((kg_search, '酷狗'), (wy_search, '网易云'), (tx_search, 'QQ音乐')):
            try:
                info = await asyncio.wait_for(module.search_and_get_first(name, singer), 20)
            except Exception as exc:
                print(f'[搜索] {label}失败，尝试下一源: {exc}')
                continue
            if info:
                ok = song_handler.play_song(info)
                print(f'[点歌] {label}: {info["name"]} - {info["singer"]}；' +
                      ('已提交到落雪音乐' if ok else '提交失败，请确认落雪音乐已启动'))
                return
        print('[搜索] 所有源无结果，交给落雪音乐搜索')
        ok = webbrowser.open(lxmusic().music_searchPlay(name=name, singer=singer, playLater=True))
        print('[点歌] 已提交到落雪音乐' if ok else '[点歌] 提交失败，请确认落雪音乐已启动')


async def run(live_id, controller):
    worker = asyncio.create_task(controller.worker()) if not controller.listen_only else None
    try:
        await listen(live_id, controller.on_chat)
    finally:
        if worker:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass


def main():
    parser = argparse.ArgumentParser(description='抖音直播弹幕点歌机')
    parser.add_argument('room', nargs='?', help='抖音网页版直播间号或直播间链接')
    parser.add_argument('--listen-only', action='store_true', help='只打印弹幕，不搜索、不播放、不切歌')
    args = parser.parse_args()
    import config
    config.create_config()
    try:
        with open(get_config_path(), encoding='utf-8') as f:
            settings = json.load(f)
        # 旧 roomid 是B站房间号，不能直接用于抖音。
        room = args.room or settings.get('douyin_live_id') or input('请输入抖音网页版直播间号或链接: ')
        live_id = normalize_live_id(room)
        ids = settings.get('skip_user_ids', [])
        if not isinstance(ids, list):
            raise ValueError('配置 skip_user_ids 必须是用户ID数组')
        with open(get_blacklist_path(), encoding='utf-8') as f:
            blacklist = [line.strip() for line in f if line.strip()]
        settings['douyin_live_id'] = live_id
        with open(get_config_path(), 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        print(f'[抖音] 监听 https://live.douyin.com/{live_id}')
        if args.listen_only:
            print('[模式] 仅验证弹幕，不执行点歌和切歌')
        asyncio.run(run(live_id, SongController(blacklist, ids, args.listen_only)))
    except KeyboardInterrupt:
        print('\n[信息] 已停止监听')
    except (ValueError, OSError) as exc:
        parser.exit(1, f'[错误] {exc}\n')
    except ImportError as exc:
        parser.exit(1, f'[错误] 缺少依赖: {exc}；请运行 pip install -r requirements.txt\n')


if __name__ == '__main__':
    main()
