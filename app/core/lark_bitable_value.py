from __future__ import annotations


def extract_cell_text(field: object) -> str | None:
    """将飞书多维表格单元格值（字符串 / 多段文本 / 关联展示等）规整为可读字符串。"""
    if field is None:
        return None
    if isinstance(field, str):
        return field
    if isinstance(field, list):
        parts: list[str] = []
        for item in field:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
        return ", ".join(parts) if parts else None
    return str(field)


def link_field_contains_record_id(link_field: object, record_id: str) -> bool:
    """判断关联类字段是否包含给定 record_id。"""
    if link_field is None:
        return False
    if isinstance(link_field, str):
        return link_field == record_id
    if isinstance(link_field, list):
        for item in link_field:
            if isinstance(item, str) and item == record_id:
                return True
            if isinstance(item, dict):
                ids = item.get("record_ids", [])
                if record_id in ids:
                    return True
                if str(item.get("text", "")).endswith(record_id):
                    return True
    return False
