from __future__ import annotations


def extract_select_text(field: object) -> str:
    """将多选字段值规整为可读字符串。

    _record_to_dict 对纯字符串 list（多选）保留原始 list，
    此函数统一 list[str] / str / None → 逗号拼接字符串。
    """
    if field is None:
        return ""
    if isinstance(field, str):
        return field.strip()
    if isinstance(field, list):
        return ", ".join(str(item) for item in field if item)
    return str(field)


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
    if isinstance(field, dict):
        if "link_record_ids" in field or "record_ids" in field:
            return None
        if "value" in field:
            return extract_cell_text(field["value"])
        text = field.get("text")
        if text:
            return str(text)
    return None


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
                for key in ("record_ids", "link_record_ids"):
                    ids = item.get(key, [])
                    if record_id in ids:
                        return True
                if str(item.get("text", "")).endswith(record_id):
                    return True
    if isinstance(link_field, dict):
        for key in ("record_ids", "link_record_ids"):
            ids = link_field.get(key, [])
            if record_id in ids:
                return True
    return False


def extract_link_record_ids(link_field: object) -> list[str]:
    """从关联类字段中提取所有 record_id。"""
    if link_field is None:
        return []
    if isinstance(link_field, str):
        return [link_field]
    if isinstance(link_field, list):
        result: list[str] = []
        for item in link_field:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                for key in ("record_ids", "link_record_ids"):
                    ids = item.get(key, [])
                    if isinstance(ids, list):
                        result.extend(str(i) for i in ids)
        return result
    if isinstance(link_field, dict):
        result = []
        for key in ("record_ids", "link_record_ids"):
            ids = link_field.get(key, [])
            if isinstance(ids, list):
                result.extend(str(i) for i in ids)
        return result
    return []


def extract_attachment_file_tokens(attachment_field: object) -> list[str]:
    """Extract file_token list from a Bitable attachment field value."""
    if attachment_field is None:
        return []
    if isinstance(attachment_field, list):
        result: list[str] = []
        for item in attachment_field:
            if isinstance(item, dict):
                token = item.get("file_token")
                if token:
                    result.append(str(token))
        return result
    return []
