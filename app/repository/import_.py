from __future__ import annotations

import tempfile
from pathlib import Path

import httpx

from app.common.lark_repository import BaseRepository
from app.common.lark_tables import T


class ImportRepository(BaseRepository):
    table_id = T.op_import.id

    async def _get_tenant_token(self) -> str:
        from app.config.app_settings import settings

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        body = {"app_id": settings.LARK_APP_ID, "app_secret": settings.LARK_APP_SECRET}
        async with httpx.AsyncClient() as hc:
            r = await hc.post(url, json=body)
            data = r.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Failed to get tenant token: {data}")
            return data["tenant_access_token"]

    async def download_attachment(self, file_token: str) -> Path:
        url = f"https://open.feishu.cn/open-apis/drive/v1/medias/{file_token}/download"
        tenant_token = await self._get_tenant_token()
        headers = {"Authorization": f"Bearer {tenant_token}"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers, follow_redirects=True)
            r.raise_for_status()
            suffix = ".pdf"
            cd = r.headers.get("content-disposition", "")
            if "filename=" in cd:
                fname = cd.split("filename=")[-1].strip('"').strip("'")
                if "." in fname:
                    suffix = "." + fname.rsplit(".", 1)[-1]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(r.content)
            tmp.close()
            return Path(tmp.name)
