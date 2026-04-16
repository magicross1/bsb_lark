import asyncio
import json
import logging
import re
from datetime import datetime, timedelta

import aiohttp
from aiohttp import FormData
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 用于 matchpin 时的固定 slotid（可按需修改）
_DEFAULT_SLOT_ID = "0209191028"


def _extract_table_from_html(html_text, exclude_columns=None):
    """从 HTML 中提取 table，返回 list[dict]，可指定排除列"""
    if exclude_columns is None:
        exclude_columns = []
    soup = BeautifulSoup(html_text, 'html.parser')
    table = soup.find('table')
    if not table:
        return []

    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    if not headers:
        rows = table.find_all('tr')
        headers = [td.get_text(strip=True) for td in rows[0].find_all('td')]

    data = []
    for row in table.find_all('tr')[1:]:
        cells = row.find_all('td')
        row_data = {
            headers[i]: cell.get_text(strip=True)
            for i, cell in enumerate(cells)
            if headers[i] not in exclude_columns
        }
        data.append(row_data)
    return data


def _rename_keys(data_list, key_mapping):
    """批量重命名字典列表的 key"""
    return [{key_mapping.get(k, k): v for k, v in d.items()} for d in data_list]


def _convert_date_format(date_str):
    """将 dd/mm/YYYY HH:MM 格式转换为 YYYY-dd-mm HH:MM:SS"""
    if not date_str:
        return ""
    date_str = date_str.strip().replace("*", "")
    dt = datetime.strptime(date_str, '%d/%m/%Y %H:%M')
    return dt.strftime('%Y-%d-%m %H:%M:%S')


def _parse_and_format_date_time(date_time_str):
    """将 dd/mm/yyyy hh:mm 解析为 (date_str, time_str) 元组"""
    parsed = datetime.strptime(date_time_str, '%d/%m/%Y %H:%M')
    return parsed.strftime('%d/%m/%Y'), parsed.strftime('%H:%M')


def _parse_matchpin_result(result_dict):
    """
    解析 matchpinByList 的原始结果（dict: ctn -> JSON字符串），
    返回 {ctn: {"1-STOP": ..., "EDO PIN MATCH": ...}}
    """
    processed = {}
    for ctn, info_json in result_dict.items():
        entry = {"1-STOP": "", "EDO PIN MATCH": ""}
        try:
            info = json.loads(info_json)
            if info.get('Success', False):
                entry["1-STOP"] = "Y"
                entry["EDO PIN MATCH"] = "Y"
            else:
                errors = info.get('Errors', [])
                if any("not found on bay-plans received by the terminal" in e for e in errors):
                    entry["1-STOP"] = "N"
                elif any("Invalid eIDO PIN" in e for e in errors):
                    entry["1-STOP"] = "Y"
                    entry["EDO PIN MATCH"] = "N"
                else:
                    entry["1-STOP"] = "Y"
                    entry["EDO PIN MATCH"] = "Y"
        except json.JSONDecodeError:
            logger.warning(f"matchpin JSON 解析失败，箱号: {ctn}")
            continue
        processed[ctn] = entry
    return processed


class HutchisonPortsProvider:
    """HPA（Hutchison Ports Australia）平台爬虫 Provider，缓存 aiohttp session 避免重复登录"""

    _instance = None
    _BASE_URL = 'https://www.hpaportal.com.au/HPAPB'
    _USERNAME = "admin@bsbtransport.com.au"
    _PASSWORD = "Cpy19871230"
    _PROXY = "http://127.0.0.1:7890"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.session: aiohttp.ClientSession | None = None
            self._session_lock = asyncio.Lock()
            self._headers = {
                "referer": self._BASE_URL,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            self.token = None
            self._initialized = True

    @classmethod
    def get_instance(cls):
        return cls()

    # ------------------------------------------------------------------
    # 内部：会话管理
    # ------------------------------------------------------------------

    async def _create_session(self):
        """若 session 不存在或已关闭则新建"""
        async with self._session_lock:
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession()

    async def _ensure_session(self):
        """若 session 无效则重新登录（session cookie 会在 aiohttp 中自动保持）"""
        if self.session is None or self.session.closed:
            logger.info("HutchisonPorts session 无效，重新登录")
            await self.login()

    async def login(self):
        """登录 HPA 平台，session cookie 自动存储在 aiohttp cookie_jar"""
        await self._create_session()
        # 预登录获取 CSRF token
        pre_login_url = f'{self._BASE_URL}/Login'
        async with self.session.get(pre_login_url) as response:
            if response.status != 200:
                raise RuntimeError("HPA 预登录失败")
            html = await response.text()
            token = self._get_token(html)

        # 提交登录表单
        data = FormData()
        data.add_field('__RequestVerificationToken', token)
        data.add_field('ReturnUrl', '')
        data.add_field('Username', self._USERNAME)
        data.add_field('Password', self._PASSWORD)
        data.add_field('RememberMyPassword', 'false')
        data.add_field('AgreeToTermsConditions', 'true')
        data.add_field('AgreeToTermsConditions', 'false')

        login_url = f"{self._BASE_URL}/Login"
        async with self.session.post(login_url, data=data, proxy=self._PROXY, headers=self._headers) as response:
            if response.status == 200:
                result = await response.text()
                self.token = self._get_token(result)
                logger.info("HPA 登录成功")

    # ------------------------------------------------------------------
    # 内部：辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _get_token(html_content):
        """从 HTML 提取 __RequestVerificationToken"""
        pattern = r'name="__RequestVerificationToken"\s*type="hidden"\s*value="([^"]+)"'
        match = re.search(pattern, html_content)
        return match.group(1) if match else None

    @staticmethod
    def _get_page_info(html_content):
        """从预约页面 HTML 提取 matchpin 所需的表单字段"""
        patterns = {
            "ConfirmManifestByTimeString": r'name="ConfirmManifestByTimeString"\s*type="hidden"\s*value="([^"]+)"',
            "jsonid": r'name="Id"\s*type="hidden"\s*value="([^"]+)"',
            "arrivalWindowstarttime": r'name="TimeOfArrival"\s*type="hidden"\s*value="([^"]+)"',
            "TimeOfArrivalString": r'name="TimeOfArrivalString"\s*type="hidden"\s*value="([^"]+)"',
        }
        info = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, html_content)
            if not match:
                return None
            info[key] = match.group(1)
        return info

    @staticmethod
    def _parse_container_enquiry_html(html_doc):
        """从集装箱查询 HTML 解析清关状态、ISO码、重量等信息"""
        if "Container not found" in html_doc:
            return None
        patterns = {
            "Clear Status": r'<span\s*id = "CustomsStatus".*?>(.*?)</span>',
            "ISO": r'<span\s*id = "ISO".*?>(.*?)</span>',
            "Gross Weight": r'<span\s*id = "Weight".*?>(.*?)</span>',
        }
        result = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, html_doc)
            value = match.group(1).strip() if match else None
            if value and key == "Gross Weight":
                try:
                    value = str(float(value) / 1000)
                except Exception:
                    value = "Not Found"
            result[key] = value or ""
        result["Quarantine"] = "Not Found"
        return result

    async def _get_aspxauth_cookie(self):
        """从 cookie_jar 中取出 .ASPXAUTH"""
        for cookie in self.session.cookie_jar:
            if cookie.key == '.ASPXAUTH' and cookie['domain'] == 'www.hpaportal.com.au':
                return cookie.value
        return None

    async def _get_cookies(self):
        """收集当前 session 中 hpaportal.com.au 的所有 cookie"""
        ck = {}
        for cookie in self.session.cookie_jar:
            if cookie['domain'] == 'www.hpaportal.com.au':
                try:
                    ck[cookie.key] = cookie.value
                except Exception:
                    continue
        ck[".ASPXAUTH"] = await self._get_aspxauth_cookie()
        return ck

    async def _pre_container_enquiry(self):
        """访问集装箱查询页，取 CSRF token"""
        url = "https://www.hpaportal.com.au/HPAPB/Container"
        async with self.session.get(url, proxy=self._PROXY, headers=self._headers) as response:
            if response.status == 200:
                html = await response.text()
                return self._get_token(html)

    async def _container_enquiry(self, ctn_number):
        """查询单个集装箱信息"""
        token = await self._pre_container_enquiry()
        ck = await self._get_cookies()
        data = FormData()
        data.add_field('__RequestVerificationToken', token)
        data.add_field('ContainerNumber', ctn_number)
        url = "https://hpaportal.com.au/HPAPB/Container"
        async with self.session.post(url, data=data, cookies=ck) as response:
            if response.status == 200:
                html = await response.text()
                result = self._parse_container_enquiry_html(html)
                return {ctn_number: result} if result else {}

    async def _pre_matchpin_enquiry(self, slot_id):
        """访问预约页，取 matchpin 所需表单字段"""
        url = f"https://www.hpaportal.com.au/HPAPB/TAS/Appointments/Public/{slot_id}"
        ck = {'.ASPXAUTH': await self._get_aspxauth_cookie()}
        async with self.session.get(url, proxy=self._PROXY, headers=self._headers, cookies=ck) as response:
            if response.status == 200:
                html = await response.text()
                return self._get_page_info(html)
        return None

    async def _matchpin(self, ctn_number, pin, slot_id):
        """为单个集装箱提交 matchpin"""
        page_info = await self._pre_matchpin_enquiry(slot_id)
        if page_info is None:
            logger.warning(f"未能获取 {ctn_number} 的 matchpin 页面信息")
            return None

        ck = {".ASPAUTH": await self._get_aspxauth_cookie()}
        async with self.session.post(
            f"https://hpaportal.com.au/HPAPB/Administration/AppointmentManagement/PublicAppointmentDetails/Confirm",
            proxy=self._PROXY,
            headers={
                "referer": f"https://hpaportal.com.au/HPAPB/TAS/Appointments/Public/{slot_id}",
                "origin": "https://hpaportal.com.au",
                "content-type": "application/json; charset=utf-8",
            },
            json={
                "ConfirmManifestByTimeString": page_info["ConfirmManifestByTimeString"],
                "CurrentStatus": "Confirmed",
                "Direction": "Import",
                "HasRestrictions": "False",
                "HasRestrictionsContainerDetails": "False",
                "Id": page_info["jsonid"],
                "ImportContainerDetails.ContainerNumber": ctn_number,
                "ImportContainerDetails.eIDOpin": pin,
                "ImportContainerDetails.IsContainerNumberEditable.IsEditable": "True",
                "ImportContainerDetails.IsEidoPinEditable.IsEditable": "True",
                "IsDirectionUnspecified": "False",
                "IsPrivateAppointment": "False",
                "ReferenceNumber": slot_id,
                "TimeOfArrival": page_info["arrivalWindowstarttime"],
                "TimeOfArrivalString": page_info["TimeOfArrivalString"],
            },
            cookies=ck,
        ) as response:
            if response.status == 200:
                info = await response.text()
                return {ctn_number: info} if info else {}

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    async def container_enquiry_by_list(self, ctn_number_list: list) -> dict:
        """批量查询集装箱信息"""
        await self._ensure_session()
        tasks = [self._container_enquiry(item) for item in ctn_number_list]
        results = await asyncio.gather(*tasks)
        result_dict = {}
        for res in results:
            if res:
                result_dict.update(res)
        return result_dict

    async def matchpin_by_list(self, ctn_pin_dict: dict, slot_id: str = _DEFAULT_SLOT_ID) -> dict:
        """
        批量 matchpin，返回 {ctn: {"1-STOP": "Y/N", "EDO PIN MATCH": "Y/N"}}

        :param ctn_pin_dict: {箱号: PIN}
        :param slot_id: VBS slot ID
        """
        await self._ensure_session()
        tasks = [self._matchpin(ctn, pin, slot_id) for ctn, pin in ctn_pin_dict.items()]
        results = await asyncio.gather(*tasks)
        raw = {}
        for res in results:
            if res:
                raw.update(res)
        return _parse_matchpin_result(raw)

    async def get_truck_manifests(self, start_date, end_date):
        """查询 Truck Manifests 列表"""
        await self._ensure_session()
        url1 = "https://www.hpaportal.com.au/HPAPB/TruckManifests"
        ck = await self._get_cookies()
        async with self.session.get(url1, cookies=ck) as res1:
            result_text = await res1.text()
            token = self._get_token(result_text)

        data = FormData()
        data.add_field('__RequestVerificationToken', token)
        data.add_field('SlotNumber', "")
        data.add_field('MovementPIN', "")
        data.add_field('DriverMSIC', "")
        data.add_field('TruckRegistration', "")
        data.add_field('StartDate', start_date)
        data.add_field("EndDate", end_date)
        data.add_field("ManifestReference", "")
        data.add_field("ContainerNumber", "")
        async with self.session.post(url1, data=data, cookies=ck) as res:
            result = await res.text()
            return _extract_table_from_html(result, exclude_columns=["Type"])

    async def get_appointment(self, start_date, end_date, selected_direction="All"):
        """查询预约列表"""
        await self._ensure_session()
        url = "https://www.hpaportal.com.au/HPAPB/TAS/Appointments"
        ck = await self._get_cookies()
        async with self.session.get(url, cookies=ck) as res:
            result = await res.text()
            token = self._get_token(result)

        data = FormData()
        data.add_field("__RequestVerificationToken", token)
        data.add_field('DateTimeFrom', start_date)
        data.add_field("DateTimeTo", end_date)
        data.add_field("SelectedDirection", selected_direction)
        data.add_field("SearchReferenceNumber", "")
        data.add_field("SearchContainerNumber", "")
        async with self.session.post(url, cookies=ck, data=data) as res2:
            result_text = await res2.text()
            return _extract_table_from_html(result_text, exclude_columns=["Type"])

    async def _query_op_time_slot(self, start_date):
        """查询单天操作时间槽并合并 Appointment + Manifest 数据"""
        appointment = await self.get_appointment(start_date, start_date)
        manifests = await self.get_truck_manifests(start_date, start_date)

        # 以 ManifestReference 为键合并
        manifest_map = {app.get("ManifestReference"): app for app in manifests if app.get("ManifestReference")}
        for app in appointment:
            mr = app.get("ManifestReference")
            if mr and mr in manifest_map:
                manifest_map[mr].pop("Status", None)
                app.update(manifest_map[mr])

        key_mapping = {
            "AppointmentNumber": "Booking Ref",
            "TimeZone": "Time",
            "GateIn": "Gate In",
            "GateOut": "Gate Out",
            "TruckRegistration": "Truck Rego",
            "ContainerNumber": "CTN NUMBER",
            "Direction": "Type",
        }
        result = _rename_keys(appointment, key_mapping)
        for app in result:
            _type = app.get("Type")
            if _type in ("Import", "Export"):
                app["Pool Name"] = "General"
            elif _type == "Empty Dehire":
                app["Pool Name"] = "Empty Return"

            # 格式化 Gate In / Gate Out
            for field in ("Gate In", "Gate Out"):
                if app.get(field):
                    app[field] = _convert_date_format(app[field])

            # 解析时间
            time_val = app.get("Time")
            if time_val:
                stripped = time_val.strip()
                length = len(stripped)
                app["Time"] = stripped[length - 5:length]
                app["Slot Date"] = stripped[0:length - 5]
            elif "ArrivalWindowStartTime" in app:
                start_time = app.get("ArrivalWindowStartTime")
                if start_time:
                    app["Slot Date"], app["Time"] = _parse_and_format_date_time(start_time)
        return result

    async def query_slot_by_list(self, date_list: list = None) -> list:
        """批量按日期查询操作时间槽"""
        if not date_list:
            return []
        await self._ensure_session()
        tasks = [self._query_op_time_slot(date) for date in date_list]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r]

    async def _query_empty_dehire(self, start_date):
        """查询单天 Empty Dehire / Export 数据"""
        await self._ensure_session()
        result_export = await self.get_appointment(start_date, start_date, "Export")
        result_dehire = await self.get_appointment(start_date, start_date, "Empty Dehire")
        app_result = result_dehire + result_export

        manifests = await self.get_truck_manifests(start_date, start_date)
        manifest_map = {app.get("ManifestReference"): app for app in manifests if app.get("ManifestReference")}
        for app in app_result:
            mr = app.get("ManifestReference")
            if mr and mr in manifest_map:
                app.update(manifest_map[mr])

        key_mapping = {
            "AppointmentNumber": "Booking Ref",
            "TimeZone": "Time",
            "GateIn": "Gate In",
            "GateOut": "Gate Out",
            "TruckRegistration": "Truck Rego",
            "ContainerNumber": "CTN NUMBER",
            "Direction": "Type",
        }
        result = _rename_keys(app_result, key_mapping)
        for app in result:
            _type = app.get("Type")
            if _type in ("Import", "Export"):
                app["Pool Name"] = "General"
            elif _type == "Empty Dehire":
                app["Pool Name"] = "Empty Return"

            for field in ("Gate In", "Gate Out"):
                if app.get(field):
                    app[field] = _convert_date_format(app[field])

            time_val = app.get("Time")
            if time_val:
                stripped = time_val.strip()
                length = len(stripped)
                app["Time"] = stripped[length - 5:length]
                app["Slot Date"] = stripped[0:length - 5]
        return result

    async def query_dehire_by_list(self, date_list: list = None) -> list:
        """批量按日期查询 Dehire / Export 时间槽"""
        if not date_list:
            return []
        await self._ensure_session()
        tasks = [self._query_empty_dehire(date) for date in date_list]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r]
