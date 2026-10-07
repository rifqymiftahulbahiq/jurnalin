import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("jurnalin.discovery")

DISCOVERED_REQUESTS: List[Dict[str, Any]] = []


def record_request(method: str, url: str, query_params: Optional[dict] = None, payload: Optional[dict] = None, status_code: int = 200):
    """
    Safely records XHR/Fetch network requests for discovery.
    NEVER records cookies, auth headers, passwords, or OTP.
    """
    if "app.kejar.id/student/" not in url and "/student/" not in url:
        return

    # Filter out sensitive fields from payload
    safe_payload = None
    if payload and isinstance(payload, dict):
        safe_payload = {}
        for k, v in payload.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in ("password", "token", "cookie", "otp", "auth")):
                continue
            safe_payload[k] = v

    record = {
        "method": method.upper(),
        "url": url,
        "query": query_params or {},
        "payload": safe_payload,
        "status": status_code,
    }

    DISCOVERED_REQUESTS.append(record)
    logger.info(f"Discovered request: {method} {url} [{status_code}]")


def get_discovered_requests() -> List[Dict[str, Any]]:
    return list(DISCOVERED_REQUESTS)


def clear_discovered_requests():
    DISCOVERED_REQUESTS.clear()
