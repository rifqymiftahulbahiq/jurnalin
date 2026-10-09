"""
KejarClient — makes API calls to Kejar.id using a Playwright browser context.

Since Kejar.id is an Inertia.js SPA, all requests must be made from within
a real browser session. httpx/requests cannot access the API endpoints directly
because the server redirects everything to the SPA shell page.

We use Playwright's `APIRequestContext` which reuses the browser's cookies and
handles the session correctly.
"""
import json
import logging
from typing import Dict, Any, Optional
from config import KEJAR_BASE_URL
from kejar.browser_session import get_profile_dir, save_user_cookies, get_user_cookies_dict

logger = logging.getLogger("jurnalin.client")


class SessionExpiredError(Exception):
    pass


class KejarClient:
    BASE_URL = KEJAR_BASE_URL

    def __init__(self, telegram_id: int, cookies: Optional[Dict[str, str]] = None, headers: Optional[Dict[str, str]] = None):
        self.telegram_id = telegram_id
        self._playwright = None
        self._browser_context = None
        self._api_request = None
        self._cookies_list = self._load_cookies_list()

        self._extra_headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{KEJAR_BASE_URL}/student/journal-weekly",
            "Accept-Language": "id-ID,id;q=0.9",
        }
        if headers:
            self._extra_headers.update(headers)

    def _load_cookies_list(self):
        """Load cookies as list of dicts with proper domain/path."""
        import os
        from kejar.browser_session import get_cookies_file
        f = get_cookies_file(self.telegram_id)
        if not os.path.exists(f):
            return []
        try:
            with open(f) as fp:
                return json.load(fp)
        except Exception:
            return []

    async def _ensure_context(self):
        """Lazily initialize Playwright API request context."""
        if self._api_request is not None:
            return

        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()

        # Build cookie list for Playwright format
        pw_cookies = []
        for c in self._cookies_list:
            domain = c.get("domain", "app.kejar.id")
            if not domain.startswith(".") and not domain.startswith("app."):
                domain = "app.kejar.id"
            pw_cookies.append({
                "name": c.get("name", ""),
                "value": c.get("value", ""),
                "domain": domain,
                "path": c.get("path", "/"),
                "secure": c.get("secure", True),
                "httpOnly": c.get("httpOnly", False),
            })

        # Create a browser context with the saved cookies
        self._browser_context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=get_profile_dir(self.telegram_id),
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )

        # Override cookies to ensure they're fresh
        if pw_cookies:
            await self._browser_context.clear_cookies()
            await self._browser_context.add_cookies(pw_cookies)

        self._api_request = self._browser_context.request

    def _check_response(self, status: int, url: str, content_type: str, text: str) -> None:
        """Raise SessionExpiredError if response indicates session is gone."""
        if status in (401, 403):
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")
        if "/login" in url.lower():
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir (redirect ke login).")
        if "text/html" in content_type and status == 200:
            # HTML response when we expected JSON = session expired or wrong endpoint
            if "login" in text.lower()[:500] or "kata sandi" in text.lower()[:500]:
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir (halaman login).")

    async def _make_request(self, method: str, path: str, **kwargs) -> Any:
        """Make an API request via Playwright browser context."""
        await self._ensure_context()

        url = path if path.startswith("http") else f"{self.BASE_URL}{path}"

        try:
            resp = await getattr(self._api_request, method)(
                url,
                headers=self._extra_headers,
                **kwargs,
            )
        except Exception as e:
            err = str(e).lower()
            if "net::err" in err or "timeout" in err:
                raise SessionExpiredError(f"Sesi Kejar.id tidak dapat diakses: {e}")
            raise

        status = resp.status
        content_type = resp.headers.get("content-type", "")

        if status in (401, 403):
            raise SessionExpiredError("Sesi Kejar.id sudah berakhir.")

        body_text = await resp.text()

        self._check_response(status, resp.url, content_type, body_text)

        if status == 404:
            from httpx import HTTPStatusError
            raise Exception(f"404 Not Found: {url}")

        if status >= 400:
            raise Exception(f"HTTP {status}: {body_text[:200]}")

        # Parse JSON
        try:
            return json.loads(body_text)
        except json.JSONDecodeError:
            if "text/html" in content_type:
                raise SessionExpiredError("Sesi Kejar.id sudah berakhir (response HTML bukan JSON).")
            raise Exception(f"JSON parse error. Response: {body_text[:200]}")

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        kwargs = {}
        if params:
            kwargs["params"] = params
        return await self._make_request("get", path, **kwargs)

    async def patch(self, path: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Any:
        kwargs = {}
        if data:
            kwargs["form"] = data
        if params:
            kwargs["params"] = params
        return await self._make_request("patch", path, **kwargs)

    async def post(self, path: str, data: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None) -> Any:
        kwargs = {}
        if data:
            kwargs["form"] = data
        if json_data:
            kwargs["data"] = json.dumps(json_data)
        return await self._make_request("post", path, **kwargs)

    async def close(self):
        try:
            if self._browser_context:
                # Save updated cookies before closing
                cookies = await self._browser_context.cookies()
                if cookies:
                    save_user_cookies(self.telegram_id, cookies)
                await self._browser_context.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._api_request = None
        self._browser_context = None
        self._playwright = None
