from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.common.update_wrapper import UpdateWrapper


class SyncData(BaseModel):
    """所有同步数据对象的基类。

    设计约定：
    - record_id 等元数据字段不写回 Bitable，通过 _metadata_fields() 排除
    - 写回字段用 alias 对齐飞书字段名（含空格）
    - datetime 字段存储毫秒时间戳（int），由 fetch_provider_data 负责转换
    - link 字段存储已解析的 record_id 列表（list[str]），由 fetch_provider_data 负责解析
    """

    model_config = ConfigDict(populate_by_name=True)

    record_id: str

    def _metadata_fields(self) -> set[str]:
        """需要从 to_update_wrapper 中排除的元数据字段（子类可覆盖）。"""
        return {"record_id"}

    def to_update_wrapper(self) -> UpdateWrapper:
        """生成 UpdateWrapper，alias 字段名即为 Bitable 写入 key。"""
        fields: dict[str, Any] = self.model_dump(
            by_alias=True,
            exclude_none=True,
            exclude=self._metadata_fields(),
        )
        return UpdateWrapper().eq("record_id", self.record_id).set_all(fields).with_label(self.record_id)

    def has_fields(self) -> bool:
        """是否有需要写回的字段。"""
        return bool(
            self.model_dump(
                by_alias=True,
                exclude_none=True,
                exclude=self._metadata_fields(),
            )
        )
