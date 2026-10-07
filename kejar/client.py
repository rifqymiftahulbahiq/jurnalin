import httpx
from typing import Dict, Any, Optional
from config import KEJAR_BASE_URL
from kejar.browser_session import get_user_cookies_dict


class SessionExpiredError(Exception):
    pass


class KejarClient:
    BASE_URL = KEJAR_BASE_URL

    def __init__(self, telegram_id: int, cookies: Optional[Dict[str, str]] = None, headers: Optional[Dict[str, str]] = None):
        self.telegram_id = telegram_id
        if cookies is None:
            cookies = get_user_cookies_dict(telegram_id)

        default_headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
        }
        if headers:
            default_headers.update(headers)

        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=default_headers,
            cookies=cookies,
            timeout=30.0,
            follow_redirects=True,
        )

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            response = await self.client.get(path, params=params)
            if response.status_code in (401, 403):
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")
            raise

    async def patch(self, path: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            response = await self.client.patch(path, data=data, params=params)
            if response.status_code in (401, 403):
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")
            raise

    async def post(self, path: str, data: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None) -> Any:
        try:
            response = await self.client.post(path, data=data, json=json_data)
            if response.status_code in (401, 403):
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")
            raise

    async def close(self):
        await self.client.aclose()