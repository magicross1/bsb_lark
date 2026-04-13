from __future__ import annotations

"""Cartage 送货地址与主数据记录匹配时的分数阈值。"""

# 低于该相似度则视为无匹配
ADDRESS_MATCH_MIN_SCORE = 0.6
# 最佳匹配低于该值时标记需人工复核
ADDRESS_MATCH_REVIEW_BELOW_SCORE = 0.8
