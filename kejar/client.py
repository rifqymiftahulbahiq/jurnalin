import httpx
from typing import Dict, Any, Optional
from config import KEJAR_BASE_URL
from kejar.browser_session import get_user_cookies_dict


class SessionExpiredError(Exception):
    pass


class _ForceHttpsTransport(httpx.AsyncHTTPTransport):
    """
    Custom transport that rewrites any HTTP redirect to HTTPS.
    Kejar.id sometimes issues 302 to http:// which causes protocol issues.
    """
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
            # Inertia.js header — tells the server this is an XHR (not page navigation)
            # so it returns JSON instead of full HTML page
            "X-Inertia": "true",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{KEJAR_BASE_URL}/student/journal-weekly",
        }
        if headers:
            default_headers.update(headers)

        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=default_headers,
            cookies=cookies,
            timeout=30.0,
            follow_redirects=True,
            max_redirects=10,
        )

    def _force_https_url(self, url: str) -> str:
        """Force any http:// URL to https://"""
        if url.startswith("http://"):
            return "https://" + url[7:]
        return url

    def _check_session_valid(self, response: httpx.Response) -> None:
        """
        Detects session expiry from response.
        Raises SessionExpiredError if redirected to /login or gets HTML back.
        """
        if response.status_code in (401, 403):
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")

        final_url = str(response.url).lower()
        if "/login" in final_url:
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir (redirect ke login).")

        # If content-type is HTML, likely redirected to login page
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir (response HTML bukan JSON).")

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        # Force HTTPS on path
        if path.startswith("http://"):
            path = self._force_https_url(path)
        try:
            response = await self.client.get(path, params=params)
            self._check_session_valid(response)
            response.raise_for_status()
            return response.json()
        except SessionExpiredError:
            raise
        except httpx.TooManyRedirects:
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir (terlalu banyak redirect).")
        except httpx.RemoteProtocolError:
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir (server disconnect).")
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")
            raise

    async def patch(self, path: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Any:
        if path.startswith("http://"):
            path = self._force_https_url(path)
        try:
            response = await self.client.patch(path, data=data, params=params)
            self._check_session_valid(response)
            response.raise_for_status()
            return response.json()
        except SessionExpiredError:
            raise
        except httpx.TooManyRedirects:
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir (terlalu banyak redirect).")
        except httpx.RemoteProtocolError:
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir (server disconnect).")
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")
            raise

    async def post(self, path: str, data: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None) -> Any:
        if path.startswith("http://"):
            path = self._force_https_url(path)
        try:
            response = await self.client.post(path, data=data, json=json_data)
            self._check_session_valid(response)
            response.raise_for_status()
            return response.json()
        except SessionExpiredError:
            raise
        except httpx.TooManyRedirects:
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir (terlalu banyak redirect).")
        except httpx.RemoteProtocolError:
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir (server disconnect).")
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")
            raise

    async def close(self):
        await self.client.aclose()
