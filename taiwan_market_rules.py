"""
taiwan_market_rules.py
台股委託與撮合跳動單位（Tick Size）規則計算模組
"""

import math


def get_tick_size(price: float) -> float:
    """
    取得股價對應之標準跳動單位 (Tick Size)
    級距規則：
    - 股價 < 10 元：0.01
    - 10 ≤ 股價 < 50 元：0.05
    - 50 ≤ 股價 < 100 元：0.10
    - 100 ≤ 股價 < 500 元：0.50
    - 500 ≤ 股價 < 1000 元：1.00
    - 股價 >= 1000 元：5.00
    """
    if price < 10.0:
        return 0.01
    elif price < 50.0:
        return 0.05
    elif price < 100.0:
        return 0.10
    elif price < 500.0:
        return 0.50
    elif price < 1000.0:
        return 1.00
    else:
        return 5.00


def next_tick_price(price: float) -> float:
    """回傳高於 price 一個跳動單位的價格"""
    tick = get_tick_size(price)
    return round(price + tick, 2)


def previous_tick_price(price: float) -> float:
    """
    回傳低於 price 一個跳動單位的價格
    若價格恰位於跨級距邊界（例如 10.0, 50.0），向下一檔應使用較低級距之跳動單位。
    """
    if price <= 10.0:
        tick = 0.01
    elif price <= 50.0:
        tick = 0.05
    elif price <= 100.0:
        tick = 0.10
    elif price <= 500.0:
        tick = 0.50
    elif price <= 1000.0:
        tick = 1.00
    else:
        tick = 5.00
    return round(max(0.01, price - tick), 2)


def round_to_tick(price: float, method: str = "floor") -> float:
    """
    將 price 對齊至合法的跳動檔位
    :param price: 目標價格
    :param method: 對齊方式，支援 'floor'（無條件捨去至檔位）、'ceil'（無條件進位至檔位）或 'round'（四捨五入）
    :return: 對齊後的數值
    """
    tick = get_tick_size(price)
    factor = round(price / tick, 6)
    if method == "floor":
        units = math.floor(factor)
    elif method == "ceil":
        units = math.ceil(factor)
    else:
        units = round(factor)
    return round(units * tick, 2)
