import asyncio
import copy
import json
import logging
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

import aiohttp
from bs4 import BeautifulSoup
from lxml import etree

logger = logging.getLogger(__name__)

# 港口代码映射（operation名称 -> VBS 子域代码）
PORT_CODE = {
    "dpWorldNSW": "CTLPB",
    "dpWorldVIC": "CONWS",
    "patrickNSW": "ASLPB",
    "patrickVIC": "ASES1",
    "victVIC": "VICTM",
    "ACFS eDepot": "ACFS",
    "ACFS Elink": "Acfs",
    "ClinkSydneyPark": "CLINK",
    "ContainerSpace": "MAES1",
    "PatrickPortRail": "Clink",
    "TyneAcfsPortBotany": "acfs",
    "TyneMtMovements": "TYNE",
    "VictInternational": "VICTM",
    "DpWorldPortBotanyContainerPark": "DPSCP",
    "AcfsVicEDepotAppletonRoadElink": "ACfs",
    "AcfsVicERailAppletonRoadERail": "ACFs",
    "DpWorldMelbourneContainerPark": "DPMCP",
    "DpWorldCoodeRoadContainerPark": "DPCCP",
    "MelbourneContainerPark": "mElb",
    "WestLink": "melb",
    "PortMelbourneContainerPark": "MELB",
}

# VBS facility ID 映射（facility 切换时使用）
_NEW_SELECTED_MAPPING = {
    "Acfs": "AELSY",
    "ACFS": "AEDSY",
    "CLINK": "CLINKSYD",
    "MAES1": "CSSR",
    "Clink": "ESDRL",
    "acfs": "ATYSY",
    "ACfs": "AEDVIC",
    "ACFs": "AERVIC",
    "TYNE": "TYASY",
    "VICTM": "VICTM",
    "mElb": "MCPMB",
    "melb": "WCPMB",
    "MELB": "PMCMB",
}

# 集装箱查询页的正则匹配规则
_CTN_REGEX_PATTERNS = {
    "CTN NUMBER": r'id="ContainerDetailsForm___CONTAINERNUMBER"[^>]*>([^<]+)',
    "EstimatedArrival": r'id="ContainerVesselDetailsForm___ESTIMATEDARRIVALDATE"[^>]*>([^<]+)',
    "ImportAvailability": r'id="ContainerVesselDetailsForm___IMPORTAVAILABILITY"[^>]*>([^<]+)',
    "StorageStartDate": r'id="ContainerVesselDetailsForm___IMPORTSTORAGEDATE"[^>]*>([^<]+)',
}


# ------------------------------------------------------------------
# 结果解析函数（原 VbsSearchResultMapper 中的逻辑）
# ------------------------------------------------------------------

def _extract_by_regex(content, pattern):
    """从 HTML 内容中按正则提取第一个匹配组"""
    match = re.search(pattern, content)
    return match.group(1).strip() if match else ""


def _normalize_ctn_dates(result_dict):
    """将日期字段标准化为 YYYY-MM-DD HH:MM 格式"""
    for key in ("EstimatedArrival", "ImportAvailability", "StorageStartDate"):
        if not result_dict.get(key):
            continue
        try:
            if key == "StorageStartDate":
                # 只有日期，减去一小时
                dt = datetime.strptime(result_dict[key], "%d/%m/%Y")
                result_dict[key] = (dt - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
            else:
                dt = datetime.strptime(result_dict[key], "%d/%m/%Y %H:%M")
                result_dict[key] = dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            result_dict[key] = ""
    return result_dict


def _extract_column_value(json_data, column_code):
    """从 VBS AJAX 响应 JSON 中按列 Code 提取单元格值"""
    columns = json_data.get("AnonymousObject", {}).get("UpdatedGridColumns", [])
    cells = json_data.get("AnonymousObject", {}).get("UpdatedGridRow", {}).get("Cells", [])

    for idx, col in enumerate(columns):
        if col.get("Code") == column_code and idx < len(cells):
            cell_value = cells[idx].get("CellValue", {})
            if isinstance(cell_value, dict):
                return cell_value.get("ValueSearchable", cell_value)
            return cell_value
    return None


def _parse_ctn_info(raw_html_list):
    """
    解析 getCtnNumberInfoByList 的原始 HTML 结果列表，
    返回 {箱号: {CTN NUMBER, EstimatedArrival, ImportAvailability, StorageStartDate}}
    """
    result = {}
    for s in raw_html_list:
        if not isinstance(s, str) or not s:
            continue
        try:
            e = json.loads(s)
        except json.JSONDecodeError:
            continue
        if e.get("Content") == "Container not found." or e.get("Result") != "true":
            continue
        content = e["Content"]
        row = {key: _extract_by_regex(content, pattern) for key, pattern in _CTN_REGEX_PATTERNS.items()}
        row = _normalize_ctn_dates(row)
        if row.get("CTN NUMBER"):
            result[row["CTN NUMBER"]] = row
    return result


def _parse_check_add_ctn(raw_html_list):
    """
    解析 checkaddCtnByList 的原始结果列表，
    返回 {箱号: {CTN NUMBER, 1-STOP, EDO PIN MATCH}}
    """
    result = {}
    for s in raw_html_list:
        if not isinstance(s, str):
            continue
        try:
            e = json.loads(s)
        except json.JSONDecodeError:
            continue
        if e.get("Content") == "Container not found." or e.get("Result") != "true":
            continue
        ctn_number = _extract_column_value(e, "CONTAINER")
        container_status = _extract_column_value(e, "CBI_FULLEMPTY")
        one_stop = "Y" if container_status and "Full" in container_status else "N"
        pin = _extract_column_value(e, "PIN")
        edo_pin_match = "Y" if pin else "N"
        if ctn_number:
            result[ctn_number] = {
                "CTN NUMBER": ctn_number,
                "1-STOP": one_stop,
                "EDO PIN MATCH": edo_pin_match,
            }
    return result


def _convert_date_format_vbs(date_str):
    """将 dd-mm-YYYY HH:MM:SS 转换为 YYYY-dd-mm HH:MM:SS（VBS 特殊格式）"""
    if not date_str:
        return ""
    dt = datetime.strptime(date_str, '%d-%m-%Y %H:%M:%S')
    return dt.strftime('%Y-%d-%m %H:%M:%S')


def _parse_slot_list_html(result_json_str):
    """
    解析 CheckBookings 页面的 AJAX JSON 响应，
    提取 VBS 时间槽列表，返回 list[dict]
    """
    try:
        json_data = json.loads(result_json_str)
    except Exception:
        logger.warning(f"slot list JSON 解析失败")
        return []

    table_html = json_data.get("AnonymousObject", {}).get("BookingListResult", "")
    soup = BeautifulSoup(table_html, 'html.parser')
    table = soup.find('table', id='CBKTimeslotSearchBookingsGrid')
    if not table:
        return []

    headers = [th.get_text(strip=True) for th in table.find('thead').find_all('th')]
    target_cols = {'Slot Date', 'Zone', 'Booking Ref', 'Type', 'Status', 'Container', 'Pool Group', 'Pool Name', 'Truck Rego'}

    rows = []
    for tr in table.find('tbody').find_all('tr'):
        row = {}
        for i, td in enumerate(tr.find_all('td')):
            if i < len(headers) and headers[i] in target_cols:
                row[headers[i]] = td.get_text(separator=" ", strip=True)
        if not row:
            continue
        row['Time'] = (row['Zone'] + ":00") if 'Zone' in row else ""
        # 只取箱号，去掉后面的尺寸说明
        if 'Container' in row:
            row['CTN NUMBER'] = str(row['Container']).split(" ")[0]
            del row['Container']
        rows.append(row)
    return rows


def _parse_booking_search_result(result_json_str):
    """
    解析 SearchBooking 页面的 AJAX JSON 响应，
    返回单条预约详情 dict
    """
    try:
        json_data = json.loads(result_json_str)
        html = json_data.get("AnonymousObject", {}).get("BSSearchResult", "")
        soup = BeautifulSoup(html, 'html.parser')

        def _text(selector_id):
            el = soup.find('span', id=selector_id)
            return el.text.strip() if el else None

        booking_ref = _text('BSBookingDetails___TIMESLOTID')
        booking_status = _text('BSBookingDetails___STATUSCODE')
        truck_rego = _text('BSBookingTruckDetails___TRK_REG')
        gatein_raw = _text('BSBookingTruckDetails___TRK_IN_GATE_TIME')
        gateout_raw = _text('BSBookingTruckDetails___TRK_OUT_GATE_TIME')

        return {
            'Booking Ref': booking_ref,
            'booking_status': booking_status,
            'Truck Rego': truck_rego,
            'Gate In': _convert_date_format_vbs(gatein_raw.replace("/", "-")) if gatein_raw else None,
            'Gate Out': _convert_date_format_vbs(gateout_raw.replace("/", "-")) if gateout_raw else None,
        }
    except Exception:
        logger.warning(f"booking search result 解析失败")
        return {}


# ------------------------------------------------------------------
# Provider 类
# ------------------------------------------------------------------

class VbsSearchProvider:
    """VBS（1-Stop VBS 平台）爬虫 Provider，按 operation 缓存 session，避免重复登录"""

    _instance = None
    _USERNAME = "bsbtransport"
    _PASSWORD = "Cpy19871230"
    _PROXY = "http://127.0.0.1:7890"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # 按 operation 保存 session，避免切换 facility 时需要重新全量登录
            self._sessions: dict[str, aiohttp.ClientSession] = {}
            self._session_locks: dict[str, asyncio.Lock] = {}
            self._default_headers = {
                "accept": "*/*",
                "accept-language": "zh-CN,zh;q=0.9",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "sec-ch-ua": '"Chromium";v="119", "Not?A_Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.160 Safari/537.36",
                "x-requested-with": "XMLHttpRequest",
            }
            self._initialized = True

    @classmethod
    def get_instance(cls):
        return cls()

    def _get_headers(self, extra: dict = None):
        """合并默认 headers 与额外 headers"""
        h = copy.deepcopy(self._default_headers)
        if extra:
            h.update(extra)
        return h

    # ------------------------------------------------------------------
    # 内部：会话管理（按 operation 缓存）
    # ------------------------------------------------------------------

    async def _ensure_session(self, operation: str):
        """确保指定 operation 的 session 存在且已登录"""
        if operation not in self._session_locks:
            self._session_locks[operation] = asyncio.Lock()

        session = self._sessions.get(operation)
        if session is None or session.closed:
            async with self._session_locks[operation]:
                session = self._sessions.get(operation)
                if session is None or session.closed:
                    logger.info(f"VBS session [{operation}] 无效，重新登录")
                    new_session = aiohttp.ClientSession()
                    self._sessions[operation] = new_session
                    await self._login(new_session, operation)

    async def _login(self, session: aiohttp.ClientSession, operation: str):
        """完整登录流程：OAuth 认证 -> 切换 facility -> 接受条款"""
        code = PORT_CODE[operation]
        facility_id = _NEW_SELECTED_MAPPING.get(code, code)

        # 1. 获取 OAuth 重定向 URL
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "user-agent": self._default_headers["user-agent"],
            "upgrade-insecure-requests": "1",
        }
        async with session.get("https://vbs.1-stop.biz/SignIn.aspx", proxy=self._PROXY, headers=headers) as resp:
            login_url = str(resp.url)

        # 2. 提交账号密码到 auth 服务器
        params = parse_qs(urlparse(login_url).query)
        post_headers = {
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://auth.onestop.co",
            "referer": login_url,
            "user-agent": self._default_headers["user-agent"],
        }
        login_data = {
            "state": params["state"][0],
            "username": self._USERNAME,
            "password": self._PASSWORD,
            "action": "default",
        }
        async with session.post(login_url, proxy=self._PROXY, headers=post_headers, data=login_data) as resp:
            text = await resp.text()
            doc = etree.HTML(text)
            form_data = {
                el.xpath("./@name")[0]: el.xpath("./@value")[0]
                for el in doc.xpath("//input[@type='hidden']")
            }

        # 3. 自动提交 SAML 表单回 VBS
        auto_headers = {
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://auth.onestop.co",
            "referer": "https://auth.onestop.co/",
            "user-agent": self._default_headers["user-agent"],
        }
        async with session.post("https://vbs.1-stop.biz/AutoSignIn.aspx", proxy=self._PROXY, headers=auto_headers, data=form_data) as resp:
            await resp.text()

        # 4. 切换到目标 facility
        switch_url = f"https://{code}.vbs.1-stop.biz/Default.aspx?vbs_Facility_Changed=true&vbs_new_selected_FACILITYID={facility_id}"
        async with session.get(switch_url, proxy=self._PROXY, headers={"user-agent": self._default_headers["user-agent"]}) as resp:
            text = await resp.text()
            doc = etree.HTML(text)
            facility_form = {
                el.xpath("./@name")[0]: el.xpath("./@value")[0]
                for el in doc.xpath("//input[@type='hidden']")
            }

        async with session.post(
            f"https://{code}.vbs.1-stop.biz/AutoSignIn.aspx",
            proxy=self._PROXY, headers=auto_headers, data=facility_form,
        ) as resp:
            await resp.text()

        # 5. 接受服务条款
        terms_url = f"https://{code}.vbs.1-stop.biz/TermsConditions.aspx"
        terms_headers = {
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-requested-with": "XMLHttpRequest",
            "referer": f"https://{code}.vbs.1-stop.biz/Landing.aspx?/Default.aspx?vbs_Facility_Changed=true&vbs_new_selected_FACILITYID={facility_id}",
            "user-agent": self._default_headers["user-agent"],
        }
        async with session.post(terms_url, proxy=self._PROXY, headers=terms_headers, data={"AjaxActionName": "ACCEPT_TNC"}) as resp:
            await resp.text()

        logger.info(f"VBS [{operation}] 登录成功")

    # ------------------------------------------------------------------
    # 内部：各页面请求
    # ------------------------------------------------------------------

    async def _get_ctn_info(self, ctn_number: str, code: str, session: aiohttp.ClientSession):
        """查询单个集装箱在 VBS 平台的状态信息"""
        async with session.post(
            f"https://{code}.vbs.1-stop.biz/ContainerSearch.aspx",
            proxy=self._PROXY,
            headers=self._get_headers({
                "referer": f"https://{code}.vbs.1-stop.biz/ContainerSearch.aspx?ContainerSearchForm___CONTAINERNUMBER={ctn_number}&ContainerSearchForm___IsPosted=true&container_search=",
                "origin": f"https://{code}.vbs.1-stop.biz",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            }),
            data={
                "ContainerSearchForm___CONTAINERNUMBER": ctn_number,
                "ContainerSearchForm___IsPosted": "true",
                "container_search": "",
                "AjaxActionName": "SEARCH",
            },
        ) as response:
            return await response.text()

    async def _check_add_ctn(self, ctn_number: str, code: str, session: aiohttp.ClientSession):
        """查询单个集装箱在工作区的状态（用于 PIN 核对）"""
        async with session.post(
            f"https://{code}.vbs.1-stop.biz/ContainerBookingItems.aspx",
            proxy=self._PROXY,
            headers=self._get_headers({
                "referer": f"https://{code}.vbs.1-stop.biz/BookingsWorkingSpace.aspx",
                "origin": f"https://{code}.vbs.1-stop.biz",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            }),
            data={
                "AjaxActionName": "UPDATE_CONTAINER",
                "ContainerNumber": ctn_number,
                "ContainerDirection": "IMPORT",
                "PartyId": "16595",
                "idTimeslot": "",
            },
        ) as response:
            return await response.text()

    async def _get_check_bookings_by_date(self, date: str, code: str, session: aiohttp.ClientSession, type_code=""):
        """查询指定日期的预约列表"""
        async with session.post(
            f"https://{code}.vbs.1-stop.biz/CheckBookings.aspx",
            proxy=self._PROXY,
            headers=self._get_headers({
                "referer": f"https://{code}.vbs.1-stop.biz/CheckBookings.aspx",
                "origin": f"https://{code}.vbs.1-stop.biz",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            }),
            data={
                "SelectParty___IsPosted": "true",
                "SearchDateBasic___BOOKINGDATE": date,
                "SearchDateBasic___BOOKINGZONE": "",
                "SearchDateBasic___IsPosted": "true",
                "SearchDateRange___DTFROM": date,
                "SearchDateRange___TZFROM": "0",
                "SearchDateRange___DTTO": date,
                "SearchDateRange___TZTO": "23",
                "SearchDateRange___IsPosted": "true",
                "BookingByDateSearchOptions___POOL": "",
                "BookingByDateSearchOptions___VESSEL": "",
                "BookingByDateSearchOptions___TYPECODE": type_code,
                "BookingByDateSearchOptions___STATUSCODE": "",
                "BookingByDateSearchOptions___LATERECEIVAL": "false",
                "BookingByDateSearchOptions___EARLYRECEIVAL": "false",
                "BookingByDateSearchOptions___IsPosted": "true",
                "BookingByDateSearchButton___IsPosted": "true",
                "SEARCH_COMPANY_DATE": "",
                "idFrom": "From",
                "idTo": "To",
                "BookingByReferenceSearch___TIMESLOTID": "Booking Reference",
                "BookingByReferenceSearch___IsPosted": "true",
                "SEARCH_BOOKING_REFERENCE": "",
                "searchType": "COMPANY_DATE_BASIC",
                "AjaxActionName": "SEARCH",
            },
        ) as response:
            return await response.text()

    async def _get_booking_search_by_ref(self, booking_ref: str, code: str, session: aiohttp.ClientSession):
        """按 Booking Ref 查询预约详情"""
        async with session.post(
            f"https://{code}.vbs.1-stop.biz/SearchBooking.aspx",
            proxy=self._PROXY,
            headers=self._get_headers({
                "referer": f"https://{code}.vbs.1-stop.biz/SearchBooking.aspx",
                "origin": f"https://{code}.vbs.1-stop.biz",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            }),
            data={
                "BookingSearchForm___CHBOOKINGREF": booking_ref,
                "BookingSearchForm___CHCONTAINER": "",
                "BookingSearchForm___CHVBSUNIQUEKEY": "",
                "SearchDateBasic___IsPosted": "true",
                "btnSearchBooking": "",
                "AjaxActionName": "SEARCH_BOOKING",
            },
        ) as response:
            return await response.text()

    async def _add_ctn(self, ctn_numbers: list, code: str, session: aiohttp.ClientSession):
        """向工作区添加集装箱"""
        ctn_str = "\n".join(ctn_numbers)
        async with session.post(
            f"https://{code}.vbs.1-stop.biz/ContainerBookingItems.aspx",
            proxy=self._PROXY,
            headers=self._get_headers({
                "referer": f"https://{code}.vbs.1-stop.biz/BookingsWorkingSpace.aspx",
                "origin": f"https://{code}.vbs.1-stop.biz",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            }),
            data={
                "CBIUploadConatinersForm___DIRECTION": "IMPORT",
                "CBIUploadConatinersForm___CONTAINERS": ctn_str,
                "CBIUploadConatinersForm___PROCESSIDh": "",
                "CBIUploadConatinersForm___IsPosted": "true",
                "cbi_add_containers_btn": "",
                "AjaxActionName": "ADD_CONTAINERS",
            },
        ) as response:
            if response.status == 200:
                text = await response.text()
                return json.loads(text) if text else None

    async def _pin_check(self, pins: list, code: str, session: aiohttp.ClientSession):
        """批量校验 PIN"""
        pins_str = "\n".join(pins)
        async with session.post(
            f"https://{code}.vbs.1-stop.biz/ContainerBookingItems.aspx",
            proxy=self._PROXY,
            headers=self._get_headers({
                "referer": f"https://{code}.vbs.1-stop.biz/BookingsWorkingSpace.aspx",
                "origin": f"https://{code}.vbs.1-stop.biz",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            }),
            data={
                "CBIMatchPinsForm___PINS": pins_str,
                "CBIMatchPinsForm___IsPosted": "true",
                "cbi_match_pins": "",
                "AjaxActionName": "MATCH_PINS",
            },
        ) as response:
            if response.status == 200:
                text = await response.text()
                return json.loads(text) if text else None

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    async def get_ctn_info_by_list(self, ctn_number_list: list, operation: str) -> dict:
        """
        批量查询集装箱在 VBS 的状态（ETA、进口可用时间等）

        :return: {箱号: {CTN NUMBER, EstimatedArrival, ImportAvailability, StorageStartDate}}
        """
        await self._ensure_session(operation)
        session = self._sessions[operation]
        code = PORT_CODE[operation]
        tasks = [self._get_ctn_info(ctn, code, session) for ctn in ctn_number_list if ctn]
        raw_results = await asyncio.gather(*tasks)
        return _parse_ctn_info([r for r in raw_results if r])

    async def check_add_ctn_by_list(self, ctn_number_list: list, operation: str) -> dict:
        """
        批量查询集装箱工作区状态（1-STOP 状态 + EDO PIN MATCH）

        :return: {箱号: {CTN NUMBER, 1-STOP, EDO PIN MATCH}}
        """
        await self._ensure_session(operation)
        session = self._sessions[operation]
        code = PORT_CODE[operation]
        tasks = [self._check_add_ctn(ctn, code, session) for ctn in ctn_number_list if ctn]
        raw_results = await asyncio.gather(*tasks)
        return _parse_check_add_ctn([r for r in raw_results if r])

    async def add_ctn_by_list(self, ctn_numbers: list, operation: str) -> list:
        """
        批量向 VBS 工作区添加集装箱（失败时自动重试，最多 20 次）

        :return: 每批成功结果的列表
        """
        await self._ensure_session(operation)
        session = self._sessions[operation]
        code = PORT_CODE[operation]
        max_retries = 20
        result_list = []
        for i in range(0, len(ctn_numbers), 10):
            slice_list = ctn_numbers[i:i + 10]
            succeeded = False
            for attempt in range(max_retries):
                if attempt > 0:
                    time.sleep(0.5)
                result = await self._add_ctn(slice_list, code, session)
                if result and result.get("Result") == "true":
                    result_list.append(result)
                    succeeded = True
                    break
            if not succeeded:
                logger.error(f"add_ctn_by_list: {slice_list} 失败，已重试 {max_retries} 次")
        return result_list

    async def pin_check_by_list(self, pins: list, operation: str) -> list:
        """
        批量校验 PIN（失败时自动重试，最多 20 次）

        :return: 每批成功结果的列表
        """
        await self._ensure_session(operation)
        session = self._sessions[operation]
        code = PORT_CODE[operation]
        max_retries = 20
        result_list = []
        for i in range(0, len(pins), 10):
            slice_list = pins[i:i + 10]
            succeeded = False
            for attempt in range(max_retries):
                if attempt > 0:
                    time.sleep(0.5)
                result = await self._pin_check(slice_list, code, session)
                if result and result.get("Result") == "true":
                    result_list.append(result)
                    succeeded = True
                    break
            if not succeeded:
                logger.error(f"pin_check_by_list: {slice_list} 失败，已重试 {max_retries} 次")
        return result_list

    async def vbs_slot_list_by_dates(self, date_list: list, operation: str) -> list:
        """
        按日期列表查询 VBS 时间槽列表，合并 CheckBookings + SearchBooking 数据

        :return: 合并后的 list[dict]，每条含 Booking Ref、时间、箱号、状态等
        """
        await self._ensure_session(operation)
        session = self._sessions[operation]
        code = PORT_CODE[operation]

        # 获取各日期的 booking 列表（已解析）
        check_tasks = [self._get_check_bookings_by_date(date, code, session) for date in date_list if date]
        raw_check_results = await asyncio.gather(*check_tasks)
        daily_slot_lists = [_parse_slot_list_html(r) for r in raw_check_results]

        # 按 Booking Ref 查询详情并合并
        merged = []
        for day_slots in daily_slot_lists:
            search_tasks = [self._get_booking_search_by_ref(slot['Booking Ref'], code, session) for slot in day_slots if slot.get('Booking Ref')]
            raw_search_results = await asyncio.gather(*search_tasks)
            search_by_ref = {
                detail['Booking Ref']: detail
                for raw in raw_search_results
                if (detail := _parse_booking_search_result(raw)) and detail.get('Booking Ref')
            }
            for slot in day_slots:
                ref = slot.get('Booking Ref')
                if ref and ref in search_by_ref:
                    merged_entry = {**slot, **search_by_ref[ref]}
                    merged.append(merged_entry)
        return merged

    async def dehire_list_by_dates(self, date_list: list, operation: str) -> list:
        """
        按日期列表查询 VBS Empty Dehire / Export 时间槽，合并详情

        :return: 二维 list，每个子列表对应一天的结果
        """
        await self._ensure_session(operation)
        session = self._sessions[operation]
        code = PORT_CODE[operation]

        # 只查 EXPORT 类型
        check_tasks = [self._get_check_bookings_by_date(date, code, session, type_code="EXPORT") for date in date_list if date]
        raw_check_results = await asyncio.gather(*check_tasks)
        daily_slot_lists = [_parse_slot_list_html(r) for r in raw_check_results]

        if not any(daily_slot_lists):
            return []

        result_by_day = []
        for day_slots in daily_slot_lists:
            search_tasks = [self._get_booking_search_by_ref(slot['Booking Ref'], code, session) for slot in day_slots if slot.get('Booking Ref')]
            raw_search_results = await asyncio.gather(*search_tasks)
            search_by_ref = {
                detail['Booking Ref']: detail
                for raw in raw_search_results
                if (detail := _parse_booking_search_result(raw)) and detail.get('Booking Ref')
            }
            day_result = []
            for slot in day_slots:
                ref = slot.get('Booking Ref')
                if ref and ref in search_by_ref:
                    day_result.append({**slot, **search_by_ref[ref]})
            result_by_day.append(day_result)
        return [r for r in result_by_day if r]
