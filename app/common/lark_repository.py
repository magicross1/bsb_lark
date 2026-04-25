from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any


@dataclass(frozen=True)
class FieldMeta:
    """Bitable 字段元数据。"""
    field_id: str
    field_name: str
    type: int

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

from app.core.lark import get_lark_client
from app.common.exceptions import LarkApiError, NotFoundError
from app.common.query_wrapper import QueryWrapper

from app.common.update_wrapper import UpdateWrapper


class BaseRepository(ABC):
    table_id: str

    def __init__(self) -> None:
        self._client = get_lark_client()

    @property
    def app_token(self) -> str:
        from app.config.app_settings import settings
        return settings.LARK_BITABLE_APP_TOKEN

    def _record_to_dict(self, r: AppTableRecord) -> dict[str, Any]:
        from app.core.lark_bitable_value import extract_cell_text
        raw = r.fields or {}
        normalized: dict[str, Any] = {"record_id": r.record_id}
        for k, v in raw.items():
            if isinstance(v, list) and all(isinstance(item, str) for item in v):
                normalized[k] = v
            elif isinstance(v, (list, dict)):
                text = extract_cell_text(v)
                normalized[k] = text if text is not None else v
            else:
                normalized[k] = v
        return normalized

    # ── 查询 ────────────────────────────────────────────────

    async def list(
        self,
        query: QueryWrapper | None = None,
        *,
        page_size: int = 500,
        max_pages: int = 100,
    ) -> list[dict[str, Any]]:
        """返回所有匹配记录（自动分页 + 客户端精筛）。

        若 query 为 in_list('record_id', ids)，走 batch_get API 直接按 ID 批量取记录。
        """
        if query is not None:
            record_ids = query._get_record_ids_hint()
            if record_ids:
                return await self._batch_get(record_ids)

        all_records: list[dict[str, Any]] = []
        token: str | None = None
        for _ in range(max_pages):
            page, token = await self._search_page(query, page_token=token, page_size=page_size)
            all_records.extend(page)
            if not token:
                break
        if query is not None:
            all_records = query._apply_client_filter(all_records)
        return all_records

    async def page(
        self,
        query: QueryWrapper | None = None,
        *,
        page_token: str | None = None,
        page_size: int = 100,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """单页查询，返回 (records, next_page_token)。

        仅应用服务端过滤，不含客户端精筛（client_filter 子句被忽略）。
        """
        return await self._search_page(query, page_token=page_token, page_size=page_size)

    async def _get(self, record_id: str) -> dict[str, Any]:
        """按 record_id 直接取单条记录（内部实现，外部通过 find(QueryWrapper().eq('record_id', ...)) 调用）。"""
        resp = await self._client.bitable.v1.app_table_record.aget(
            GetAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .record_id(record_id)
            .build(),
        )
        if not resp.success():
            if resp.code == 1254006:
                raise NotFoundError(resource="record", detail=record_id)
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="get")
        return self._record_to_dict(resp.data.record)

    async def findOne(self, query: QueryWrapper) -> dict[str, Any] | None:
        """返回第一条匹配记录，无匹配则返回 None。

        若 query 为 eq('record_id', rid)，走直连 GET API（性能更优）；否则走 search + 客户端精筛。
        """
        rid = query._get_record_id_hint()
        if rid:
            try:
                return await self._get(rid)
            except NotFoundError:
                return None
        records = await self.list(query)
        return records[0] if records else None

    # ── 写操作 ──────────────────────────────────────────────

    async def createOne(self, fields: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.bitable.v1.app_table_record.acreate(
            CreateAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(AppTableRecord.builder().fields(fields).build())
            .build(),
        )
        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="create")
        return self._record_to_dict(resp.data.record)

    async def batch_create(self, fields_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records = [AppTableRecord.builder().fields(f).build() for f in fields_list]
        resp = await self._client.bitable.v1.app_table_record.abatch_create(
            BatchCreateAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(BatchCreateAppTableRecordRequestBody.builder().records(records).build())
            .build(),
        )
        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="batch_create")
        items = resp.data.records if resp.data and resp.data.records else []
        return [self._record_to_dict(r) for r in items]

    async def updateOne(self, wrapper: UpdateWrapper) -> dict[str, Any]:
        """按 record_id 更新单条记录。必须通过 UpdateWrapper().eq('record_id', rid).set(...) 指定目标。"""
        rid = wrapper._get_record_id_hint()
        if not rid:
            raise ValueError("updateOne() 需通过 UpdateWrapper().eq('record_id', rid) 指定目标记录")
        fields = wrapper._get_fields()
        if not fields:
            raise ValueError("UpdateWrapper 未调用 set() / set_all()")
        resp = await self._client.bitable.v1.app_table_record.aupdate(
            UpdateAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .record_id(rid)
            .request_body(AppTableRecord.builder().fields(fields).build())
            .build(),
        )
        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="updateOne")
        return self._record_to_dict(resp.data.record)

    async def batch_update(self, wrappers: list[UpdateWrapper]) -> list[dict[str, Any]]:
        """批量更新记录，每条可指定不同字段（均须含 record_id hint）。"""
        if not wrappers:
            return []
        records = [
            AppTableRecord.builder()
            .record_id(w._get_record_id_hint() or "")
            .fields(w._get_fields())
            .build()
            for w in wrappers
        ]
        resp = await self._client.bitable.v1.app_table_record.abatch_update(
            BatchUpdateAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(BatchUpdateAppTableRecordRequestBody.builder().records(records).build())
            .build(),
        )
        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="batch_update")
        items = resp.data.records if resp.data and resp.data.records else []
        return [self._record_to_dict(r) for r in items]

    async def deleteOne(self, query: QueryWrapper) -> None:
        """删除单条记录。必须通过 QueryWrapper().eq('record_id', rid) 指定目标记录。"""
        rid = query._get_record_id_hint()
        if not rid:
            raise ValueError("delete() 需通过 QueryWrapper().eq('record_id', rid) 指定目标记录")
        resp = await self._client.bitable.v1.app_table_record.adelete(
            DeleteAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .record_id(rid)
            .build(),
        )
        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="delete")

    async def batch_delete(self, record_ids: list[str]) -> None:
        resp = await self._client.bitable.v1.app_table_record.abatch_delete(
            BatchDeleteAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(BatchDeleteAppTableRecordRequestBody.builder().records(record_ids).build())
            .build(),
        )
        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="batch_delete")

    async def _batch_get(self, record_ids: list[str]) -> list[dict[str, Any]]:
        """按 record_id 列表批量取记录（内部实现，外部通过 list(QueryWrapper().in_list('record_id', ids)) 调用）。"""
        if not record_ids:
            return []
        resp = await self._client.bitable.v1.app_table_record.abatch_get(
            BatchGetAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(BatchGetAppTableRecordRequestBody.builder().record_ids(record_ids).build())
            .build(),
        )
        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="batch_get")
        items = resp.data.records if resp.data and resp.data.records else []
        return [self._record_to_dict(r) for r in items]

    # ── 字段元数据 ───────────────────────────────────────────

    async def list_fields(self) -> list[FieldMeta]:
        resp = await self._client.bitable.v1.app_table_field.alist(
            ListAppTableFieldRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .build(),
        )
        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="list_fields")
        items = resp.data.items if resp.data and resp.data.items else []
        return [FieldMeta(field_id=f.field_id, field_name=f.field_name, type=f.type) for f in items]

    # ── 内部分页（_search_page）────────────────────────────

    async def _search_page(
        self,
        query: QueryWrapper | None,
        *,
        page_token: str | None = None,
        page_size: int = 100,
    ) -> tuple[list[dict[str, Any]], str | None]:
        flt = query._to_filter() if query else None
        field_names = query._to_field_names() if query else None
        sort = query._to_sort() if query else None

        body_builder = SearchAppTableRecordRequestBody.builder()
        if flt:
            body_builder.filter(flt)
        if field_names:
            body_builder.field_names(field_names)
        if sort:
            body_builder.sort(sort)

        req_builder = (
            SearchAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .page_size(page_size)
            .request_body(body_builder.build())
        )
        if page_token:
            req_builder.page_token(page_token)

        resp = await self._client.bitable.v1.app_table_record.asearch(req_builder.build())

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="search")

        items = resp.data.items if resp.data and resp.data.items else []
        next_token = resp.data.page_token if resp.data and resp.data.page_token else None
        return [self._record_to_dict(r) for r in items], next_token
