"""离线测试：无需登录、网络或落雪音乐。"""
import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from douyin_client import ChatEvent, normalize_live_id
from main import SongController, parse_song


class InputTests(unittest.TestCase):
    def test_live_id(self):
        self.assertEqual(normalize_live_id('123456'), '123456')
        self.assertEqual(normalize_live_id('https://live.douyin.com/123456?foo=bar'), '123456')
        for value in ['https://evil.com/123', 'https://live.douyin.com.evil.com/123', 'https://v.douyin.com/foo', 'abc']:
            with self.assertRaises(ValueError):
                normalize_live_id(value)

    def test_song_syntax(self):
        self.assertEqual(parse_song('点歌 青花瓷 周杰伦'), ('青花瓷', '周杰伦'))
        self.assertEqual(parse_song(' 点歌 青花瓷 '), ('青花瓷', ''))
        for text in ['点歌', '聊天 点歌 青花瓷', '点歌 a b c']:
            self.assertIsNone(parse_song(text))


class ControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_filter_and_listen_only(self):
        controller = SongController(['禁歌'])
        for text in ['普通弹幕', '点歌 禁歌']:
            controller.on_chat(ChatEvent('1', '观众', text))
        self.assertTrue(controller.queue.empty())
        controller.on_chat(ChatEvent('1', '观众', '点歌 青花瓷'))
        self.assertEqual(controller.queue.get_nowait(), ('青花瓷', ''))
        controller = SongController(skip_user_ids=['1'], listen_only=True)
        with patch('main.webbrowser.open') as opened:
            for text in ['点歌 青花瓷', '下一首']:
                controller.on_chat(ChatEvent('1', '观众', text))
            opened.assert_not_called()
        self.assertTrue(controller.queue.empty())

    async def test_skip_permissions(self):
        controller = SongController(skip_user_ids=['123'])
        with patch('main.webbrowser.open', return_value=True) as opened:
            controller.on_chat(ChatEvent('456', '同名', '下一首'))
            opened.assert_not_called()
            controller.on_chat(ChatEvent('123', '同名', '下一首'))
            opened.assert_called_once()

    async def test_order_and_failure_recovery(self):
        controller = SongController()
        calls = []
        async def play(name, singer):
            calls.append(name)
            if name == '失败':
                raise RuntimeError('模拟搜索异常')
        controller.play_song = play
        for name in ['失败', '第二首', '第三首']:
            controller.on_chat(ChatEvent('1', '观众', f'点歌 {name}'))
        worker = asyncio.create_task(controller.worker())
        await asyncio.wait_for(controller.queue.join(), 1)
        worker.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await worker
        self.assertEqual(calls, ['失败', '第二首', '第三首'])

    async def test_search_fallback(self):
        kg = SimpleNamespace(search_and_get_first=AsyncMock(side_effect=RuntimeError('断网')))
        wy = SimpleNamespace(search_and_get_first=AsyncMock(return_value=None))
        tx = SimpleNamespace(search_and_get_first=AsyncMock(return_value={'name': '歌', 'singer': '歌手'}))
        handler = SimpleNamespace(play_song=lambda info: True)
        with patch.dict(sys.modules, {'kg_search': kg, 'wy_search': wy, 'tx_search': tx, 'song_handler': handler}):
            await SongController().play_song('歌', '')
        for module in [kg, wy, tx]:
            module.search_and_get_first.assert_awaited_once()


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_callback_deduplication_and_reconnect(self):
        from douyin_client import listen
        clients = []
        received = []
        message = SimpleNamespace(common=SimpleNamespace(msg_id=999),
                                  user=SimpleNamespace(id=123, nick_name='观众'),
                                  content='点歌 青花瓷')
        class Parser:
            def parse(self, payload):
                return payload
        class FakeFetcher:
            def __init__(self, live_id):
                self.session = SimpleNamespace(get=lambda *a, **k: None, close=lambda: None)
                self.live_id = live_id
                self.stopped = False
                clients.append(self)
            def start(self):
                self._parseChatMsg(message)
                self._parseChatMsg(message)
                if len(clients) == 2:
                    self._parseControlMsg(SimpleNamespace(status=3))
            def stop(self):
                self.stopped = True
        modules = {
            'douyin_vendor.liveMan': SimpleNamespace(DouyinLiveWebFetcher=FakeFetcher),
            'douyin_vendor.protobuf.douyin': SimpleNamespace(ChatMessage=Parser, ControlMessage=Parser, PushFrame=Parser),
            'websocket': SimpleNamespace(),
        }
        loop = asyncio.get_running_loop()
        def executor(executor_arg, start):
            future = loop.create_future()
            start()
            future.set_result(None)
            return future
        with patch.dict(sys.modules, modules), patch.object(loop, 'run_in_executor', side_effect=executor):
            await asyncio.wait_for(listen('123456', received.append, reconnect_delay=0), 2)
        self.assertEqual(len(clients), 2)
        self.assertTrue(clients[-1].stopped)
        self.assertEqual(received, [ChatEvent('123', '观众', '点歌 青花瓷', 999)])


if __name__ == '__main__':
    unittest.main()
