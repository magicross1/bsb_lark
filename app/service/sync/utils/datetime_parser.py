from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_datetime_to_timestamp(dt_str: str) -> int | None:
    """解析日期时间字符串为 Bitable 毫秒时间戳。"""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(dt_str, fmt)
            return int(dt.timestamp() * 1000)
        except (ValueError, OSError):
            continue
    logger.warning("日期解析失败: %s", dt_str)
    return None


def safe_ts(raw: dict, key: str) -> int | None:
    """从 dict 取值并转为毫秒时间戳，空值返回 None。"""
    v = raw.get(key)
    return parse_datetime_to_timestamp(str(v)) if v else None
