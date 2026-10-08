# -*- coding: utf-8 -*-
"""
台灣證券交易所股票跳動單位（Tick Size）規則模組

此模組提供台股跳動單位的對齊與計算功能，依據台灣證券交易所營業細則規定：
- 股價 < 10 元：0.01 元
- 10 <= 股價 < 50 元：0.05 元
- 50 <= 股價 < 100 元：0.10 元
- 100 <= 股價 < 500 元：0.50 元
- 500 <= 股價 < 1000 元：1.00 元
- 股價 >= 1000 元：5.00 元
"""

from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_UP


def get_tick_size(price: float) -> float:
    """
    取得給定價格區間所適用的跳動單位 (Tick Size)
    
    :param price: 股票價格
    :return: 該價格對應的跳動單位
    """
    p = Decimal(str(round(price, 4)))
    if p < Decimal("10"):
        return 0.01
    elif p < Decimal("50"):
        return 0.05
    elif p < Decimal("100"):
        return 0.10
    elif p < Decimal("500"):
        return 0.50
    elif p < Decimal("1000"):
        return 1.00
    else:
        return 5.00


def next_tick_price(price: float) -> float:
    """
    回傳高於 price 一個跳動單位的價格
    
    :param price: 當前價格
    :return: 上漲一個跳動單位的價格
    """
    p = Decimal(str(round(price, 4)))
    if p < Decimal("10"):
        tick = Decimal("0.01")
    elif p < Decimal("50"):
        tick = Decimal("0.05")
    elif p < Decimal("100"):
        tick = Decimal("0.10")
    elif p < Decimal("500"):
        tick = Decimal("0.50")
    elif p < Decimal("1000"):
        tick = Decimal("1.00")
    else:
        tick = Decimal("5.00")
    
    res = p + tick
    return float(res)


def previous_tick_price(price: float) -> float:
    """
    回傳低於 price 一個跳動單位的價格
    
    :param price: 當前價格
    :return: 下跌一個跳動單位的價格（不低於 0.01）
    """
    p = Decimal(str(round(price, 4)))
    if p <= Decimal("10.0"):
        tick = Decimal("0.01")
    elif p <= Decimal("50.0"):
        tick = Decimal("0.05")
    elif p <= Decimal("100.0"):
        tick = Decimal("0.10")
    elif p <= Decimal("500.0"):
        tick = Decimal("0.50")
    elif p <= Decimal("1000.0"):
        tick = Decimal("1.00")
    else:
        tick = Decimal("5.00")
    
    res = p - tick
    return float(max(Decimal("0.01"), res))


def round_to_tick(price: float, method: str = "floor") -> float:
    """
    將 price 對齊跳動單位
    
    :param price: 原始價格
    :param method: 對齊方式，支援 'floor' (向下取整)、'ceil' (向上取整)、'round' (四捨五入)
    :return: 對齊跳動單位後的價格
    """
    p = Decimal(str(round(price, 4)))
    
    if p < Decimal("10"):
        tick = Decimal("0.01")
    elif p < Decimal("50"):
        tick = Decimal("0.05")
    elif p < Decimal("100"):
        tick = Decimal("0.10")
    elif p < Decimal("500"):
        tick = Decimal("0.50")
    elif p < Decimal("1000"):
        tick = Decimal("1.00")
    else:
        tick = Decimal("5.00")
        
    mode = method.lower()
    if mode == "floor":
        rounded = (p / tick).quantize(Decimal("1"), rounding=ROUND_FLOOR) * tick
    elif mode == "ceil":
        rounded = (p / tick).quantize(Decimal("1"), rounding=ROUND_CEILING) * tick
    else:
        rounded = (p / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
        
    return float(rounded)
