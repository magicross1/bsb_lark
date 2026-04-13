from __future__ import annotations

from abc import ABC

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

from app.core.lark import get_lark_client
from app.common.exceptions import LarkApiError, NotFoundError


class LarkRepository(ABC):
    table_id: str

    def __init__(self) -> None:
        self._client = get_lark_client()

    @property
    def app_token(self) -> str:
        from app.config.app_settings import settings
        return settings.LARK_BITABLE_APP_TOKEN

    def _record_to_dict(self, r: AppTableRecord) -> dict[str, Any]:
        return {"record_id": r.record_id, **(r.fields or {})}

    # ── List / Get ──────────────────────────────────────────

    async def list_records(
        self,
        *,
        page_size: int = 100,
        page_token: str | None = None,
        filter_expr: str | None = None,
        sort_expr: str | None = None,
        field_names: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        builder = (
            ListAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .page_size(page_size)
        )
        if page_token:
            builder.page_token(page_token)
        if filter_expr:
            builder.filter(filter_expr)
        if sort_expr:
            builder.sort(sort_expr)
        if field_names:
            builder.field_names(str(field_names))

        resp = await self._client.bitable.v1.app_table_record.alist(
            builder.build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="list_records")

        records = resp.data.items if resp.data and resp.data.items else []
        next_token = resp.data.page_token if resp.data and resp.data.page_token else None
        return [self._record_to_dict(r) for r in records], next_token

    async def list_all_records(
        self,
        *,
        filter_expr: str | None = None,
        sort_expr: str | None = None,
        field_names: list[str] | None = None,
        page_size: int = 500,
        max_pages: int = 100,
    ) -> list[dict[str, Any]]:
        all_records: list[dict[str, Any]] = []
        token: str | None = None
        for _ in range(max_pages):
            records, token = await self.list_records(
                page_size=page_size,
                page_token=token,
                filter_expr=filter_expr,
                sort_expr=sort_expr,
                field_names=field_names,
            )
            all_records.extend(records)
            if not token:
                break
        return all_records

    async def get_record(self, record_id: str) -> dict[str, Any]:
        resp = await self._client.bitable.v1.app_table_record.aget(
            GetAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .record_id(record_id)
            .build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            if resp.code == 1254006:
                raise NotFoundError(resource="record", detail=record_id)
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="get_record")

        return self._record_to_dict(resp.data.record)

    # ── Create ──────────────────────────────────────────────

    async def create_record(self, fields: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.bitable.v1.app_table_record.acreate(
            CreateAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(AppTableRecord.builder().fields(fields).build())
            .build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="create_record")

        return self._record_to_dict(resp.data.record)

    async def batch_create_records(self, fields_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records = [AppTableRecord.builder().fields(f).build() for f in fields_list]
        resp = await self._client.bitable.v1.app_table_record.abatch_create(
            BatchCreateAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(BatchCreateAppTableRecordRequestBody.builder().records(records).build())
            .build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="batch_create_records")

        items = resp.data.records if resp.data and resp.data.records else []
        return [self._record_to_dict(r) for r in items]

    # ── Update ──────────────────────────────────────────────

    async def update_record(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.bitable.v1.app_table_record.aupdate(
            UpdateAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .record_id(record_id)
            .request_body(AppTableRecord.builder().fields(fields).build())
            .build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="update_record")

        return self._record_to_dict(resp.data.record)

    async def batch_update_records(self, updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records = [
            AppTableRecord.builder().record_id(u["record_id"]).fields(u["fields"]).build()
            for u in updates
        ]
        resp = await self._client.bitable.v1.app_table_record.abatch_update(
            BatchUpdateAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(BatchUpdateAppTableRecordRequestBody.builder().records(records).build())
            .build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="batch_update_records")

        items = resp.data.records if resp.data and resp.data.records else []
        return [self._record_to_dict(r) for r in items]

    # ── Delete ──────────────────────────────────────────────

    async def delete_record(self, record_id: str) -> None:
        resp = await self._client.bitable.v1.app_table_record.adelete(
            DeleteAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .record_id(record_id)
            .build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="delete_record")

    async def batch_delete_records(self, record_ids: list[str]) -> None:
        resp = await self._client.bitable.v1.app_table_record.abatch_delete(
            BatchDeleteAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(BatchDeleteAppTableRecordRequestBody.builder().records(record_ids).build())
            .build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="batch_delete_records")

    # ── Batch Get ───────────────────────────────────────────

    async def batch_get_records(self, record_ids: list[str]) -> list[dict[str, Any]]:
        resp = await self._client.bitable.v1.app_table_record.abatch_get(
            BatchGetAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(BatchGetAppTableRecordRequestBody.builder().records(record_ids).build())
            .build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="batch_get_records")

        items = resp.data.records if resp.data and resp.data.records else []
        return [self._record_to_dict(r) for r in items]

    # ── Search ──────────────────────────────────────────────

    async def search_records(
        self,
        *,
        condition: dict[str, Any] | None = None,
        page_size: int = 100,
        page_token: str | None = None,
        field_names: list[str] | None = None,
        sort: list[dict[str, Any]] | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        body_builder = SearchAppTableRecordRequestBody.builder().page_size(page_size)
        if condition:
            body_builder.condition(condition)
        if field_names:
            body_builder.field_names(str(field_names))
        if sort:
            body_builder.sort(sort)

        resp = await self._client.bitable.v1.app_table_record.asearch(
            SearchAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .request_body(body_builder.build())
            .build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="search_records")

        items = resp.data.items if resp.data and resp.data.items else []
        next_token = resp.data.page_token if resp.data and resp.data.page_token else None
        return [self._record_to_dict(r) for r in items], next_token

    # ── Find by Business Key ────────────────────────────────

    async def find_record(
        self,
        field_name: str,
        value: str,
    ) -> dict[str, Any] | None:
        filter_expr = f'CurrentValue.[{field_name}]="{value}"'
        records, _ = await self.list_records(filter_expr=filter_expr, page_size=1)
        return records[0] if records else None

    async def find_record_or_fail(
        self,
        field_name: str,
        value: str,
    ) -> dict[str, Any]:
        record = await self.find_record(field_name, value)
        if record is None:
            raise NotFoundError(resource=f"{self.table_id} record with {field_name}={value}")
        return record

    async def find_record_id(
        self,
        field_name: str,
        value: str,
    ) -> str | None:
        record = await self.find_record(field_name, value)
        return record["record_id"] if record else None

    async def find_record_id_or_fail(
        self,
        field_name: str,
        value: str,
    ) -> str:
        record_id = await self.find_record_id(field_name, value)
        if record_id is None:
            raise NotFoundError(resource=f"{self.table_id} record with {field_name}={value}")
        return record_id

    # ── Upsert (find by key → update or create) ────────────

    async def upsert_record(
        self,
        key_field: str,
        key_value: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        existing = await self.find_record(key_field, key_value)
        if existing:
            return await self.update_record(existing["record_id"], fields)
        return await self.create_record(fields)

    # ── Update by Business Key ──────────────────────────────

    async def update_by_key(
        self,
        key_field: str,
        key_value: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        record_id = await self.find_record_id_or_fail(key_field, key_value)
        return await self.update_record(record_id, fields)

    async def delete_by_key(
        self,
        key_field: str,
        key_value: str,
    ) -> None:
        record_id = await self.find_record_id_or_fail(key_field, key_value)
        await self.delete_record(record_id)

    # ── Fields ──────────────────────────────────────────────

    async def list_fields(self) -> list[dict[str, Any]]:
        resp = await self._client.bitable.v1.app_table_field.alist(
            ListAppTableFieldRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .build(),
            lark.BaseRequest.builder().build(),
        )

        if not resp.success():
            raise LarkApiError(lark_code=resp.code, message=resp.msg, detail="list_fields")

        items = resp.data.items if resp.data and resp.data.items else []
        return [{"field_id": f.field_id, "field_name": f.field_name, "type": f.type} for f in items]


# Backward-compatible alias during the repository refactor.
BaseRepository = LarkRepository
