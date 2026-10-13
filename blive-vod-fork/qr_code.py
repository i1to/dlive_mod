# -*- coding: utf-8 -*-
"""
二维码矩阵生成 - 供前端自行绘制，无需依赖外部 CDN 或系统浏览器
"""
from typing import List, Optional


def make_matrix(data: str) -> Optional[List[List[bool]]]:
    """
    生成二维码点阵，True 表示黑点。
    失败时返回 None（调用方可回退到浏览器页面方案）。
    """
    if not data:
        return None
    try:
        import qrcode
    except Exception as exc:
        print(f"[登录] qrcode 库不可用，无法生成内置二维码: {exc}")
        return None
    try:
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        return [[bool(cell) for cell in row] for row in qr.get_matrix()]
    except Exception as exc:
        print(f"[登录] 生成二维码点阵失败: {exc}")
        return None
