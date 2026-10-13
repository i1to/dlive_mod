"""抖音客户端适配层：同步上游客户端通过后台线程连接异步点歌程序。"""
import asyncio
from collections import deque
from dataclasses import dataclass
import threading
from urllib.parse import urlparse


@dataclass(frozen=True)
class ChatEvent:
    user_id: str
    nickname: str
    text: str
    message_id: int = 0


def normalize_live_id(value):
    value = str(value).strip()
    if value.isdecimal():
        return value
    parsed = urlparse(value)
    if parsed.scheme in ('http', 'https') and parsed.hostname == 'live.douyin.com':
        room = parsed.path.strip('/')
        if room.isdecimal():
            return room
    raise ValueError('请输入抖音网页版直播间号或 https://live.douyin.com/直播间号；短链接请先在浏览器打开')


async def listen(live_id, on_chat, reconnect_delay=5):
    # 延迟导入，使 --help 和离线规则测试不依赖网络库。
    from douyin_vendor.liveMan import DouyinLiveWebFetcher
    from douyin_vendor.protobuf.douyin import ChatMessage, ControlMessage, PushFrame
    import websocket

    loop = asyncio.get_running_loop()
    stopping = threading.Event()
    ended = threading.Event()
    recent = deque(maxlen=2000)
    seen = set()

    class Client(DouyinLiveWebFetcher):
        def __init__(self):
            super().__init__(live_id)
            original_get = self.session.get
            def bounded_get(*args, **kwargs):
                if stopping.is_set():
                    raise RuntimeError('监听已停止')
                kwargs.setdefault('timeout', 15)
                return original_get(*args, **kwargs)
            self.session.get = bounded_get

        def _parseChatMsg(self, payload):
            message = ChatMessage().parse(payload)
            mid = message.common.msg_id
            if mid:
                if mid in seen:
                    return
                if len(recent) == recent.maxlen:
                    seen.discard(recent[0])
                recent.append(mid)
                seen.add(mid)
            event = ChatEvent(str(message.user.id), message.user.nick_name,
                              message.content, mid)
            loop.call_soon_threadsafe(on_chat, event)

        def _parseControlMsg(self, payload):
            if ControlMessage().parse(payload).status == 3:
                ended.set()
                print('[抖音] 主播已下播，结束监听')
                self.stop()

        def _wsOnClose(self, ws, *args):
            # 上游关闭回调会调用已失效的房间状态接口，此处直接记录状态。
            print('[抖音] 弹幕连接已关闭')

        def _wsOnOpen(self, ws):
            if stopping.is_set():
                ws.close()
                return
            print('[抖音] 弹幕连接成功')
            threading.Thread(target=self._sendHeartbeat, args=(ws,), daemon=True).start()

        def _sendHeartbeat(self, ws):
            while not stopping.wait(5) and ws.keep_running:
                try:
                    ws.send(bytes(PushFrame(payload_type="hb")), websocket.ABNF.OPCODE_PING)
                except Exception:
                    break

    client = None
    worker = None
    try:
        while not ended.is_set():
            client = Client()
            worker = loop.run_in_executor(None, client.start)
            try:
                await asyncio.shield(worker)
            except Exception as exc:
                print(f'[抖音] 连接失败: {exc}')
            finally:
                if worker.done():
                    client.session.close()
            if not ended.is_set():
                print(f'[抖音] {reconnect_delay}秒后重新连接，Ctrl+C 退出')
                await asyncio.sleep(reconnect_delay)
    finally:
        stopping.set()
        if client is not None and hasattr(client, 'ws'):
            client.stop()
        if worker is not None:
            try:
                await asyncio.shield(worker)
            except Exception:
                pass
        if client is not None:
            client.session.close()
