# -*- coding: utf-8 -*-
"""
网易云搜索模块 - 搜索歌曲并返回第一首的元数据，供 LX Music music/play 使用
"""
from search_common import build_keyword, format_interval, run_search, make_result, fetch_json

WY_SEARCH_URL = "https://music.163.com/api/search/get/web"


async def search_wy(keyword: str, page: int = 1, pagesize: int = 5) -> list:
    """
    网易云搜索歌曲
    :param keyword: 搜索关键词（歌名 + 歌手）
    :param page: 页码
    :param pagesize: 每页数量
    :return: 歌曲列表
    """
    data = {
        "s": keyword,
        "type": 1,  # 1=单曲
        "offset": (page - 1) * pagesize,
        "limit": pagesize,
    }
    headers = {
        "Referer": "https://music.163.com/",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    result = await fetch_json("POST", WY_SEARCH_URL, data=data, headers=headers)
    if not result or result.get("code") != 200:
        return []
    return result.get("result", {}).get("songs", [])


def parse_wy_song(song: dict) -> dict:
    """
    将网易云搜索结果转为 LX Music music/play 所需的参数格式
    """
    song_name = song.get("name", "")
    # 歌手可能是数组
    artists = song.get("artists", [])
    singer = "/".join(a.get("name", "") for a in artists) if artists else ""
    album = song.get("album") or {}
    album_name = album.get("name", "")
    album_id = album.get("id", "")
    song_id = song.get("id", "")
    song_duration = song.get("duration") or 0  # 毫秒，可能为 None
    img = album.get("picUrl", "")

    # 格式化时长 毫秒 -> mm:ss
    interval = format_interval(song_duration / 1000)

    # 构建 types 数组
    types = [
        {"type": "128k", "size": ""},
        {"type": "320k", "size": ""},
        {"type": "flac", "size": ""},
    ]

    return make_result(
        source="wy",
        name=song_name,
        singer=singer,
        songmid=str(song_id),  # wy用歌曲id作为songmid
        img=img,
        albumId=str(album_id) if album_id else "",
        interval=interval,
        albumName=album_name,
        types=types,
    )


async def search_and_get_first(name: str, singer: str = "") -> dict | None:
    """
    搜索网易云并返回第一首歌的 LX Music 播放参数
    :param name: 歌名
    :param singer: 歌手（可选）
    :return: music/play 所需参数 dict，失败返回 None
    """
    return await run_search(search_wy, parse_wy_song, build_keyword(name, singer), "网易云")
