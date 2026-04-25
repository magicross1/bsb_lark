import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp
import pytz

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 结果解析函数（原 ResultMapper 中的逻辑，现直接内联）
# ------------------------------------------------------------------

def _parse_date(container, key):
    """将 ISO 格式日期字符串转换为 YYYY-MM-DD HH:MM 格式"""
    date_str = container.get(key)
    if date_str:
        try:
            return datetime.fromisoformat(date_str).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return ""
    return ""


def _parse_containers_info(result_json, ctn_dict):
    """
    解析 getContainersInfo 接口结果。
    只保留与 ctn_dict 中 vessel 匹配的记录。
    返回 {箱号: {VesselName, Event}}
    """
    info = {}
    for container in result_json.get('Data', []):
        container_number = container['ContainerNumber']
        vessel_raw = container.get('Vessel') or ""
        vessel_name = vessel_raw.split('(')[-1].split('|')[0].strip() if vessel_raw else None
        last_event = container.get('LastEventType')
        expected_vessel = ctn_dict.get(container_number)
        # 若 ctnDict 里指定了 vessel 则进行核对
        if expected_vessel is not None and expected_vessel != vessel_name:
            continue
        info[container_number] = {
            'VesselName': vessel_name,
            'Event': last_event,
        }
    return info


def _parse_customs_cargo_status(result_json):
    """
    解析 customsCargoStatusSearch 接口结果。
    过滤掉 60 天以前的清关记录。
    返回 {箱号: {Clear Status, Quarantine}}
    """
    info = {}
    compare_base = datetime.now(pytz.utc) - timedelta(days=60)
    for unit in result_json.get('Data', []):
        container_number = unit['Container']
        clearance_str = unit.get("ClearanceDateTime")
        if clearance_str:
            clearance_dt = datetime.fromisoformat(clearance_str).replace(tzinfo=pytz.utc)
            if clearance_dt < compare_base:
                continue
        info[container_number] = {
            'Clear Status': unit["CargoStatus"],
            'Quarantine': unit["AqisGasStatus"],
        }
    return info


_TERMINAL_MAPPING = {
    "DP WORLD NS PORT BOTANY": {"Terminal": "Dp World NSW", "Depot": "NSW", "PortOfDischarge": "PORT OF SYDNEY"},
    "PATRICK NS PORT BOTANY": {"Terminal": "Patrick NSW", "Depot": "NSW", "PortOfDischarge": "PORT OF SYDNEY"},
    "HUTCHISON PORTS - PORT BOTANY": {"Terminal": "HUTCHISON NSW", "Depot": "NSW", "PortOfDischarge": "PORT OF SYDNEY"},
    "DP WORLD, VI, WEST SWANSON": {"Terminal": "Dp World VIC", "Depot": "VIC", "PortOfDischarge": "PORT OF MELBOURNE"},
    "PATRICK, VI, EAST SWANSON": {"Terminal": "Patrick VIC", "Depot": "VIC", "PortOfDischarge": "PORT OF MELBOURNE"},
    "VICTORIA INTERNATIONAL CONTAINER TERMINAL": {"Terminal": "VICT VIC", "Depot": "VIC", "PortOfDischarge": "PORT OF MELBOURNE"},
}


def _parse_match_containers_info(result_json):
    """
    解析 matchContainersInfo 接口结果（EDO 匹配用）。
    包含 vessel、port、ETA、存储日期、各事件状态等信息。
    返回 {箱号: {...}}
    """
    info = {}
    thirty_days_ago = datetime.now() - timedelta(days=30)

    for container in result_json.get('Data', []):
        # 过滤超过 30 天没有事件的记录
        latest_event_str = container.get('LatestEventDatetime')
        if latest_event_str:
            latest_event = datetime.fromisoformat(latest_event_str[:19])
            if latest_event < thirty_days_ago:
                continue

        container_number = container['ContainerNumber']
        vessel_in_raw = container.get('VesselIn') or ""
        vessel_in = vessel_in_raw.split('(')[-1].split('|')[0].strip() if vessel_in_raw else None
        in_voyage = vessel_in_raw.split('|')[-1].split(')')[0].strip() if vessel_in_raw else None

        event_place = container.get("EventPlace", "")
        pod = container.get("PortOfDischarge")
        terminal_info = _TERMINAL_MAPPING.get(event_place)
        terminal_match = bool(terminal_info and terminal_info.get("PortOfDischarge") == pod)

        gross_weight = container.get('GrossWeight')

        storage_start = ""
        if container.get('StorageStartDate'):
            storage_start = str(datetime.fromisoformat(container['StorageStartDate']) - timedelta(hours=1))

        event_dict = {e["Name"]: e.get("EventLocalTime", "") for e in container.get('Events', [])}

        def _event_flag_and_time(name):
            t_str = event_dict.get(name, "")
            flag = "Y" if t_str else ""
            time_val = _parse_date({'EventLocalTime': t_str}, 'EventLocalTime')
            return flag, time_val

        on_board, on_board_time = _event_flag_and_time('ON_BOARD_VESSEL')
        discharge, discharge_time = _event_flag_and_time('DISCHARGE')
        gateout, gateout_time = _event_flag_and_time('GATEOUT')

        info[container_number] = {
            'VesselIn': vessel_in,
            'InVoyage': in_voyage,
            'PortOfDischarge': container.get("PortOfDischarge"),
            'ISO': container.get("ISOCode"),
            'CommodityIn': container.get("CommodityIn"),
            'Gross Weight': gross_weight / 1000 if gross_weight is not None else None,
            'Terminal Full Name': event_place if terminal_match else '',
            'EstimatedArrival': _parse_date(container, 'EstimatedArrival') if terminal_match else '',
            'ImportAvailability': _parse_date(container, 'ImportAvailability') if terminal_match else '',
            'StorageStartDate': storage_start if terminal_match else '',
            'ON_BOARD_VESSEL': on_board if terminal_match else '',
            'ON_BOARD_VESSEL_Time': on_board_time if terminal_match else '',
            'DISCHARGE': discharge if terminal_match else '',
            'DISCHARGE_Time': discharge_time if terminal_match else '',
            'GATEOUT': gateout if terminal_match else '',
            'GATEOUT_Time': gateout_time if terminal_match else '',
        }
    return info


def _format_datetime(dt_str):
    """ISO 字符串转 YYYY-MM-DD HH:MM，失败返回空字符串"""
    if not dt_str or not str(dt_str).strip():
        return ""
    try:
        return datetime.fromisoformat(dt_str).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return ""


def _parse_vessel_search(full_vessel_name, result_json, ctn_dict):
    """
    解析 vesselSearchByNameList 单个 vessel 的结果。
    按 voyage 匹配并提取 ETA/ETD/存储日期等信息。
    返回 {full_vessel_name: {...}}
    """
    info = {}
    if not result_json:
        return info

    data = result_json.get("Data", [])
    vessel_name, voyage = ctn_dict.get(full_vessel_name, (None, None))
    matched = [d for d in data if d.get('InVoyage') == voyage or d.get('OutVoyage') == voyage]

    if matched:
        d0 = matched[0]
        last_free = ""
        if d0.get('ImportStorage'):
            last_free = str(datetime.fromisoformat(d0['ImportStorage']) - timedelta(hours=1))
        export_cutoff = ""
        if d0.get("CargoCutoff"):
            export_cutoff = str(datetime.fromisoformat(d0["CargoCutoff"]) - timedelta(hours=1))

        info[full_vessel_name] = {
            'ETA': _format_datetime(d0.get("EstimatedArrival")),
            "Terminal Full Name": d0.get("ContractorName", ""),
            "ETD": _format_datetime(d0.get("EstimatedDeparture")),
            "First Free": _format_datetime(d0.get("ImportAvailability")),
            "Last Free": _format_datetime(last_free),
            "Export Start": _format_datetime(d0.get("ExportReceival")),
            "Export Cutoff": _format_datetime(export_cutoff),
            "Actual Arrival": "Y" if d0.get("ActualArrival") else "",
        }
    else:
        info[full_vessel_name] = {
            'ETA': "", "Terminal Full Name": "", "ETD": "",
            "First Free": "", "Last Free": "",
            "Export Start": "", "Export Cutoff": "", "Actual Arrival": "",
        }
    return info


# ------------------------------------------------------------------
# Provider 类
# ------------------------------------------------------------------

class OneStopProvider:
    """1-Stop 平台爬虫 Provider，缓存 aiohttp session 避免重复登录"""

    _instance = None
    _BASE_URL = 'https://ccproxy-api.1-stop.biz/CargoConnectGW'
    _APP_CODE = 'Gateway_'
    _COUNTRY_CODE = 'AU'
    _CLIENT_ID = '1STOP'
    _USERNAME = "bsbtransport"
    _PASSWORD = "Cpy19871230"
    _PROXY = None

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
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'App-Code': self._APP_CODE,
                'Country-Code': self._COUNTRY_CODE,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
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
        """若 session 无效则重新登录"""
        if self.session is None or self.session.closed:
            logger.info("1-Stop session 无效，重新登录")
            await self.login()

    async def login(self):
        """登录 1-Stop 平台，token 存储在 session cookie 中"""
        await self._create_session()
        login_url = f'{self._BASE_URL}/api/v1/user/login?skip-notification=true'
        payload = {
            'ClientID': self._CLIENT_ID,
            'Username': self._USERNAME,
            'Password': self._PASSWORD,
        }
        async with self.session.post(login_url, proxy=self._PROXY, headers=self._headers, json=payload) as response:
            if response.status != 200:
                raise RuntimeError(f"1-Stop 登录失败，状态码: {response.status}")
            logger.info("1-Stop 登录成功")

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    async def _request_with_retry(self, url: str, payload: dict) -> dict | None:
        """带 401 自动重新登录重试的 POST 请求"""
        for attempt in range(2):
            async with self.session.post(url, proxy=self._PROXY, headers=self._headers, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                if response.status == 401 and attempt == 0:
                    logger.warning("1-Stop API 返回 401，重新登录重试: %s", url.split('?')[0].split('/')[-1])
                    await self.login()
                    continue
                logger.error("1-Stop API 失败，状态码: %s, URL: %s", response.status, url.split('?')[0].split('/')[-1])
                return None
        return None

    async def get_containers_info_by_list(self, ctn_vessel_dict: dict) -> dict:
        """
        批量查询集装箱最新事件（用于 Discharged 流程）

        :param ctn_vessel_dict: {箱号: vessel名称}
        :return: {箱号: {VesselName, Event}}
        """
        await self._ensure_session()
        container_list = list(ctn_vessel_dict.keys())
        result = {}
        for i in range(0, len(container_list), 10):
            slice_list = container_list[i:i + 10]
            url = f'{self._BASE_URL}/services/Container/v1/Event/Search?skip-notification=true'
            result_json = await self._request_with_retry(url, {"Containers": slice_list})
            if result_json:
                result.update(_parse_containers_info(result_json, ctn_vessel_dict))
        return result

    async def match_containers_info_by_list(self, container_list: list[str]) -> dict:
        """
        批量查询集装箱详细匹配信息（用于 EDO 匹配流程）

        :param container_list: 箱号列表
        :return: {箱号: {...详细信息...}}
        """
        await self._ensure_session()
        result = {}
        for i in range(0, len(container_list), 10):
            slice_list = container_list[i:i + 10]
            url = f'{self._BASE_URL}/services/Container/v1/Event/Search?skip-notification=true'
            result_json = await self._request_with_retry(url, {"Containers": slice_list})
            if result_json:
                result.update(_parse_match_containers_info(result_json))
        return result

    async def customs_cargo_status_search(self, container_list: list) -> dict:
        """
        批量查询清关状态

        :param container_list: 箱号列表
        :return: {箱号: {Clear Status, Quarantine}}
        """
        await self._ensure_session()
        result = {}
        for i in range(0, len(container_list), 10):
            slice_list = container_list[i:i + 10]
            url = "https://ccproxy-api.1-stop.biz/CMRGW/services/CMRImport/v1/CustomStatus/SearchBasic?skip-notification=true"
            result_json = await self._request_with_retry(url, {"ContainerNumbers": slice_list, "SubSearch": "public"})
            if result_json:
                result.update(_parse_customs_cargo_status(result_json))
        return result

    async def _vessel_search_by_name(self, vessel_name, base_node):
        """查询单个船名的班轮信息，401 时自动重新登录重试"""
        port_dict = {"PORT OF SYDNEY": "AUSYD", "PORT OF MELBOURNE": "AUMEL"}
        payload = {
            'PortOfCall': port_dict[base_node],
            'VesselLloydsVoyage': vessel_name,
            'Vessel': "",
            'Terminal': "",
            'DisplayDeparted': False,
        }
        url = "https://ccproxy-api.1-stop.biz/CargoConnectGW/services/Vessel/v2/Schedule/Search?skip-notification=true"
        return await self._request_with_retry(url, payload)

    async def vessel_search_by_name_list(self, vessel_map_dict: dict, base_node: str) -> dict:
        """
        批量查询船名班期，返回解析后的 {full_vessel_name: {...ETA/ETD...}}

        :param vessel_map_dict: {full_vessel_name: (vessel_name, voyage)}
        :param operation: 'nsw' 或 'vic'
        :return: {full_vessel_name: {...}}
        """
        await self._ensure_session()
        tasks = {key: self._vessel_search_by_name(vessel_map_dict[key][0], base_node) for key in vessel_map_dict}
        raw_results = await asyncio.gather(*tasks.values())

        result = {}
        for full_name, raw in zip(tasks.keys(), raw_results):
            result.update(_parse_vessel_search(full_name, raw, vessel_map_dict))
        return result
