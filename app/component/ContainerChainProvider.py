import logging
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)


def _send_request(url, headers, cookies=None):
    return requests.get(url, headers=headers, cookies=cookies, allow_redirects=False)


def _get_cookies(response):
    return response.cookies.get_dict()


def _convert_date(date_str, pattern=''):
    """将 dd/mm/YYYY 格式转换为 API 所需的日期范围字符串"""
    original_date = datetime.strptime(date_str, "%d/%m/%Y")
    time_str = " 00:00:00"
    if pattern == 'start':
        return original_date.strftime("%m-%d-%Y") + time_str
    else:
        day = original_date + timedelta(days=1)
        return day.strftime("%m-%d-%Y") + time_str


def _format_datetime(time_str, target_hour=None):
    """将 ISO 时间字符串解析为 (日期, 时间) 元组"""
    dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
    if target_hour is not None:
        dt = dt.replace(hour=target_hour)
    return dt.strftime("%d/%m/%y"), dt.strftime("%H:%M")


def _rename_keys(data_list, key_mapping):
    """批量重命名字典列表的 key"""
    return [{key_mapping.get(k, k): v for k, v in data.items()} for data in data_list]


class ContainerChainProvider:
    """ContainerChain 平台爬虫 Provider，负责登录和数据拉取，内部缓存 cookie 避免重复登录"""

    _instance = None
    _USERNAME = 'admin@bsbtransport.com.au'
    _PASSWORD = 'Cpy19871230'
    _COOKIE_TTL_HOURS = 4  # cookie 有效期

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cookie = None
            cls._instance._cookie_expires_at = None
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()

    # ------------------------------------------------------------------
    # 内部：会话管理
    # ------------------------------------------------------------------

    def _ensure_authenticated(self):
        """检查 cookie 是否有效，过期或不存在时重新登录"""
        now = datetime.now()
        if self._cookie is None or (self._cookie_expires_at and now >= self._cookie_expires_at):
            logger.info("ContainerChain cookie 已过期或不存在，重新登录")
            self._cookie = self._login_main()
            self._cookie_expires_at = now + timedelta(hours=self._COOKIE_TTL_HOURS)

    def _login_main(self):
        """执行完整的 OAuth 登录流程，返回 LIVE_8760 cookie 值"""
        url = "https://live.containerchain.com.au/"
        headers = {
            'Host': 'live.containerchain.com.au',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
        }

        # 第一步：访问主页，跟随 302 跳转到 SSO
        response = _send_request(url, headers)
        dyc_cookie = response.cookies.get_dict()
        if response.status_code != 302:
            logger.error(f"登录第一步失败，状态码: {response.status_code}")
            return None

        # 第二步：跳转到 SSO 登录页
        location_url = response.headers.get('Location')
        cookies = _get_cookies(response)
        headers['Host'] = 'sso.containerchain.com'
        response = _send_request(location_url, headers, cookies)
        dec_cookie = response.cookies.get_dict()
        if response.status_code != 302:
            logger.error(f"登录第二步失败，状态码: {response.status_code}")
            return None

        # 第三步：获取 xsrf token
        location_url = response.headers.get('Location')
        cookies = _get_cookies(response)
        response = _send_request(location_url, headers, cookies)
        idsrv_xsrf = response.text.split(';idsrv.xsrf&')[-1].split('&quot;}', 1)[0].split('&quot;')[-1]
        dsc_cookie = response.cookies.get_dict()

        # 第四步：提交用户名密码
        payload = {
            "idsrv.xsrf": idsrv_xsrf,
            "username": self._USERNAME,
            "password": self._PASSWORD,
        }
        post_headers = {
            'Host': 'sso.containerchain.com',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Upgrade-Insecure-Requests': '1',
            'Origin': 'https://sso.containerchain.com',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Referer': 'https://sso.containerchain.com/identity/login?signin=880cb8c2acdd814edf381369ced81735',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
        }
        new_cookie = {'cc.idsrv.xsrf': dsc_cookie['cc.idsrv.xsrf']}
        for k, v in dec_cookie.items():
            if 'cc.SignInMessage' in k:
                new_cookie[k] = v

        response = requests.post(
            location_url, headers=post_headers, cookies=new_cookie,
            data=urlencode(payload), allow_redirects=False,
        )
        dsic_cookie = response.cookies.get_dict()
        location_url11 = response.headers.get('Location')

        new_cookie['cc.idsrv'] = dsic_cookie['cc.idsrv']
        new_cookie['cc.idsvr.username'] = dsic_cookie['cc.idsvr.username']
        new_cookie['cc.idsvr.session'] = dsic_cookie['cc.idsvr.session']
        cookies_str = ''.join(f'{k}={v}; ' for k, v in new_cookie.items())
        headers['Cookie'] = cookies_str

        # 第五步：获取最终表单并提交完成登录
        response5 = _send_request(location_url11, headers)
        root = ET.fromstring(response5.text)
        items = {tag.get('name'): tag.get('value') for tag in root.findall('.//input')}
        login_cookie = ''.join(f'{k}={v}; ' for k, v in dyc_cookie.items())
        return self._finalize_login(items, login_cookie)

    def _finalize_login(self, payload_dict, cookie):
        """提交最终 SAMLResponse，获取 LIVE_8760 cookie"""
        url = "https://live.containerchain.com.au/"
        headers = {
            'Host': 'live.containerchain.com.au',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Upgrade-Insecure-Requests': '1',
            'Origin': 'https://sso.containerchain.com',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Dest': 'document',
            'Referer': 'https://sso.containerchain.com/',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
            'Cookie': cookie,
        }
        response = requests.post(url, headers=headers, data=urlencode(payload_dict), allow_redirects=False)
        return response.cookies.get_dict()['LIVE_8760']

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def search_my_notifications(self, start_date, end_date, container_number, notification_number, cookie):
        """查询指定日期范围内的通知时间槽"""
        try:
            url = "https://live.containerchain.com.au/api/accounts/21087/notifications/mynotificationtimeslots"
            payload = {
                "fromDate": start_date,
                "toDate": end_date,
                "containerNumber": container_number,
                "notificationNumber": notification_number,
                "status": "",
                "forTransporter": "true",
            }
            headers = {
                'accept': 'application/json, text/plain, */*',
                'cache-control': 'no-cache',
                'cookie': f'LIVE_8760={cookie}',
                'pragma': 'no-cache',
                'priority': 'u=1, i',
                'referer': 'https://live.containerchain.com.au/',
                'sec-ch-ua-platform': '"Windows"',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'x-requested-with': 'XMLHttpRequest',
            }
            response = requests.get(url, headers=headers, params=urlencode(payload))
            if response.status_code == 200:
                return {'code': 0, 'msg': '搜索成功', 'data': response.json()}
            logger.warning(f"search_my_notifications 失败: {response.text}")
            return {'code': -1, 'msg': '搜索失败'}
        except Exception:
            logger.error(traceback.format_exc())
            return {'code': -1, 'msg': '搜索失败，服务异常'}

    def gate_movements(self, num):
        """查询箱子的 Gate Movement 记录"""
        self._ensure_authenticated()
        try:
            url = f"https://live.containerchain.com.au/api/notifications/gatemovements/{num}"
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
                'App-Version': '1.0.2663',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'cookie': f'LIVE_8760={self._cookie}',
                'Host': 'live.containerchain.com.au',
                'Pragma': 'no-cache',
                'Referer': 'https://live.containerchain.com.au/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return {'code': 0, 'msg': '搜索成功', 'data': response.json()}
            logger.warning(f"gate_movements 失败: {response.text}")
            return {'code': -1, 'msg': '搜索失败'}
        except Exception:
            logger.error(traceback.format_exc())
            return {'code': -1, 'msg': '搜索失败，服务异常'}

    def release_orders(self, num):
        """查询箱子的放箱订单"""
        self._ensure_authenticated()
        try:
            url = f"https://live.containerchain.com.au/api/notifications/releaseorders/v2/{num}"
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8',
                'App-Version': '1.0.2663',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'cookie': f'LIVE_8760={self._cookie}',
                'Host': 'live.containerchain.com.au',
                'Pragma': 'no-cache',
                'Referer': 'https://live.containerchain.com.au/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return {'code': 0, 'msg': '搜索成功', 'data': response.json()}
            logger.warning(f"release_orders 失败: {response.text}")
            return {'code': -1, 'msg': '搜索失败'}
        except Exception:
            logger.error(traceback.format_exc())
            return {'code': -1, 'msg': '搜索失败，服务异常'}

    def search_notifications_by_dates(self, date_list: list) -> list:
        """
        按日期列表批量查询通知时间槽，解析并返回标准化结果

        :param date_list: 日期列表，格式 ["dd/mm/YYYY", ...]
        :return: 每个日期的结果列表，二维结构
        """
        self._ensure_authenticated()
        key_mapping = {
            "facility": "Terminal",
            "notificationNumber": "Booking Ref",
            "vehicle": "Truck Rego",
            "containerNumber": "CTN NUMBER",
            "statusCode": "Status",
            "type": "Type",
        }
        result = []
        for date in date_list:
            start_time = _convert_date(date, "start")
            end_time = _convert_date(date)
            single = self.search_my_notifications(start_time, end_time, "", "", self._cookie)
            data = single.get("data")
            if not data:
                continue
            data = _rename_keys(data, key_mapping)
            for row in data:
                row["Type"] = "Empty Return"
                row["Source"] = "ContainerChain"
                notification_date = row.get("notificationDate", "")
                if notification_date:
                    row["Slot Date"], row["Time"] = _format_datetime(notification_date)
            result.append(data)
        return result
