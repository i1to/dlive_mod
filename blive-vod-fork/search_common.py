# -*- coding: utf-8 -*-
"""
搜索模块公共工具 - 各音源搜索模块（kg/wy/tx）共享的常量与辅助函数
"""
import aiohttp

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# 网络请求超时（秒）
REQUEST_TIMEOUT = 10


def build_keyword(name: str, singer: str = "") -> str:
    """拼接搜索关键词（歌名 + 歌手）"""
    return f"{name} {singer}" if singer else name


def format_interval(seconds) -> str:
    """将秒数格式化为 mm:ss，无效/非数字时长返回空串"""
    if not isinstance(seconds, (int, float)) or seconds <= 0:
        return ""
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def make_result(source: str, name: str = "", singer: str = "", songmid: str = "",
                img: str = "", albumId: str = "", interval: str = "",
                albumName: str = "", types=None, hash: str = "",
                strMediaMid: str = "") -> dict:
    """
    构建搜索模块的标准返回 dict，统一各音源的返回结构。
    各字段含义见 AGENTS.md「搜索模块标准返回格式」。
    """
    return {
        "source": source,
        "name": name,
        "singer": singer,
        "songmid": songmid,
        "img": img,
        "albumId": albumId,
        "interval": interval,
        "albumName": albumName,
        "types": types if types is not None else [],
        "hash": hash,
        "strMediaMid": strMediaMid,
    }


async def fetch_json(method: str, url: str, *, params=None, data=None, headers=None):
    """
    统一的 HTTP 请求封装：发起请求并返回解析后的 JSON。
    非 200 返回 None。各音源共用，避免 ClientSession 样板重复。
    :param method: "GET" 或 "POST"
    :param url: 请求地址
    """
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.request(
            method, url, params=params, data=data, headers=req_headers,
        ) as resp:
            if resp.status != 200:
                return None
            return await resp.json(content_type=None)


async def run_search(search_fn, parser, keyword: str, source_label: str):
    """
    统一执行搜索：调用 search_fn 拿列表，取第一首交给 parser 解析。
    失败或无结果返回 None。
    :param search_fn: async 搜索函数，接收 keyword，返回歌曲列表
    :param parser: 解析函数，接收单首歌 dict，返回标准化 dict
    :param keyword: 搜索关键词
    :param source_label: 出错日志中显示的音源名称（如 "酷狗"）
    """
    try:
        songs = await search_fn(keyword)
        if not songs:
            return None
        return parser(songs[0])
    except Exception as e:
        print(f"[搜索] {source_label}搜索出错: {e}")
        return None
