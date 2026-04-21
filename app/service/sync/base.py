from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from app.common.bitable_fields import get_field_type
from app.common.bitable_query import BitableQuery

logger = logging.getLogger(__name__)


# ── 类型定义 ──────────────────────────────────────────────────


class OverwritePolicy(Enum):
    """字段覆盖策略 — 控制 Provider 返回值何时覆盖 Bitable 已有值。"""

    ALWAYS = "always"
    NON_EMPTY = "non_empty"
    ONCE = "once"


@dataclass(frozen=True)
class LinkConfig:
    """关联字段解析配置 — 指定目标表和搜索字段，自动查找 record_id。

    用法:
        LinkConfig(table=T.md_terminal, search_field="Terminal Full Name")
        → 按 "Terminal Full Name" 搜索 MD-Terminal 表，返回匹配记录的 record_id
    """

    table: Any  # TableDef from lark_tables (e.g. T.md_terminal)
    search_field: str  # 目标表中的搜索字段 Bitable 显示名

    @property
    def table_id(self) -> str:
        return self.table.id


@dataclass(frozen=True)
class FieldMapping:
    """Provider 返回字段 → Bitable 写入字段。

    provider_key:   Provider 返回数据中的 key
    bitable_field:  Bitable 写入字段名（类型从全局注册表自动解析）
    link:           关联字段配置（非空时自动解析 link，field_type 强制为 "link"）
    overwrite:      覆盖策略
        ALWAYS    — Provider 有值就覆盖（适合会变化的字段如 Status）
        NON_EMPTY — Provider 返回空值时不覆盖（默认，安全策略）
        ONCE      — Bitable 已有值就不覆盖（适合"一旦确定就不变"的字段如日期）
    """

    provider_key: str
    bitable_field: str
    link: LinkConfig | None = None
    overwrite: OverwritePolicy = OverwritePolicy.NON_EMPTY

    @property
    def field_type(self) -> str:
        if self.link is not None:
            return "link"
        return get_field_type(self.bitable_field)


@dataclass(frozen=True)
class BatchCondition:
    """一个同步条件 = 筛选规则 + 写回字段（单 Provider）。"""

    name: str
    description: str
    query: BitableQuery
    write_fields: list[FieldMapping]


@dataclass(frozen=True)
class MultiProviderBatchCondition:
    """多 Provider 同步条件 — 按 Provider 分组写回字段。

    用法:
        MultiProviderBatchCondition(
            ...,
            write_fields={
                "1-Stop customs": [FieldMapping(...), ...],
                "Hutchison": [FieldMapping(...), ...],
            },
        )
    """

    name: str
    description: str
    query: BitableQuery
    write_fields: dict[str, list[FieldMapping]]


# ── Link 解析 ──────────────────────────────────────────────────


class LinkResolver:
    """通用关联字段解析器 — 根据显示文本查找目标表记录的 record_id。

    同一请求内自动缓存，相同 table+field+value 只查一次 Bitable。
    """

    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}

    async def resolve(self, config: LinkConfig, search_value: str) -> str | None:
        if not search_value:
            return None

        cache_key = f"{config.table_id}|{config.search_field}={search_value}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        repo = _get_repo(config.table_id)
        records, _ = await repo.list_records(
            filter_expr=f'CurrentValue.[{config.search_field}]="{search_value}"',
            page_size=1,
        )
        record_id = records[0].get("record_id") if records else None
        self._cache[cache_key] = record_id
        return record_id


_repo_cache: dict[str, Any] = {}


def _get_repo(table_id: str) -> Any:
    if table_id not in _repo_cache:
        from app.common.lark_repository import LarkRepository

        class _DynamicRepo(LarkRepository):
            pass

        _DynamicRepo.table_id = table_id
        _repo_cache[table_id] = _DynamicRepo()
    return _repo_cache[table_id]


# ── 共享逻辑 ──────────────────────────────────────────────────


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


async def build_update_fields(
    data: dict[str, Any],
    write_fields: list[FieldMapping],
    link_resolver: LinkResolver,
    existing_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """根据 FieldMapping 配置，将 Provider 数据转为 Bitable 写入字段。

    自动处理:
    - text/select: str(value)
    - number: float(value)
    - datetime: parse_datetime_to_timestamp
    - link: LinkResolver 自动查找 record_id

    覆盖策略:
    - ALWAYS:    Provider 有值就写
    - NON_EMPTY: Provider 返回空值时不写（默认）
    - ONCE:      Bitable 已有值时不写（需传 existing_fields）
    """
    fields: dict[str, Any] = {}
    for mapping in write_fields:
        value = data.get(mapping.provider_key)
        is_empty = value is None or value == ""

        if mapping.overwrite == OverwritePolicy.ONCE:
            if existing_fields and _has_existing_value(existing_fields, mapping.bitable_field):
                continue
            if is_empty:
                continue
        elif mapping.overwrite == OverwritePolicy.NON_EMPTY:
            if is_empty:
                continue
        # ALWAYS: 即便空值也写入 (由下面的类型转换自然处理)

        if is_empty:
            continue

        ft = mapping.field_type
        if ft == "link":
            record_id = await link_resolver.resolve(mapping.link, str(value))
            if record_id:
                fields[mapping.bitable_field] = [record_id]
        elif ft == "datetime":
            ts = parse_datetime_to_timestamp(str(value))
            if ts is not None:
                fields[mapping.bitable_field] = ts
        elif ft == "number":
            try:
                fields[mapping.bitable_field] = float(value)
            except (ValueError, TypeError):
                logger.warning("数值转换失败 %s=%s", mapping.bitable_field, value)
        else:
            fields[mapping.bitable_field] = str(value)

    return fields


def _has_existing_value(existing_fields: dict[str, Any], bitable_field: str) -> bool:
    """检查 Bitable 记录中该字段是否已有值。"""
    from app.core.lark_bitable_value import extract_cell_text

    val = existing_fields.get(bitable_field)
    if val is None:
        return False
    text = extract_cell_text(val)
    return bool(text)


async def batch_write_back(
    repo: Any,
    updates: list[dict[str, Any]],
) -> tuple[int, int]:
    """批量写回 Bitable — 先 batch_update，失败回退逐条。返回 (synced, errors)。"""
    if not updates:
        return 0, 0

    try:
        await repo.batch_update_records(updates)
        return len(updates), 0
    except Exception as batch_err:
        logger.warning("batch_update 失败，逐条回退: %s", batch_err)
        synced = 0
        errors = 0
        for u in updates:
            try:
                await repo.update_record(u["record_id"], u["fields"])
                synced += 1
            except Exception as e:
                logger.error("逐条写回失败 %s: %s", u["record_id"], e)
                errors += 1
        return synced, errors
