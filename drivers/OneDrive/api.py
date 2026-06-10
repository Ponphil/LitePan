"""OneDrive / Microsoft Graph API 端点与响应辅助方法。"""

from typing import Any, Dict


class OneDriveAPI:
    BASE_URL = "https://graph.microsoft.com/v1.0"
    USER_AGENT = "LitePan/0.3.0-beta"

    ENDPOINTS = {
        "me": "/me",
        "drive": "/me/drive",
        "root": "/me/drive/root",
        "root_children": "/me/drive/root/children",
        "path_item": "/me/drive/root:/{item_path}:",
        "path_children": "/me/drive/root:/{item_path}:/children",
        "item": "/me/drive/items/{item_id}",
        "item_children": "/me/drive/items/{item_id}/children",
        "copy": "/me/drive/items/{item_id}/copy",
    }

    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }


class OneDriveApiHelper:
    @staticmethod
    def build_headers(access_token: str = "") -> Dict[str, str]:
        headers = OneDriveAPI.HEADERS.copy()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    @staticmethod
    def extract_error_message(response: Dict[str, Any]) -> str:
        error = response.get("error") if isinstance(response, dict) else None
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or error)
        return str(response or "")

    @staticmethod
    def is_token_expired(status: int, response: Dict[str, Any] = None) -> bool:
        if status in (401, 403):
            return True
        error = response.get("error") if isinstance(response, dict) else None
        code = str(error.get("code") or "").lower() if isinstance(error, dict) else ""
        message = str(error.get("message") or "").lower() if isinstance(error, dict) else ""
        return (
            "invalidauthenticationtoken" in code
            or "token" in message and ("expired" in message or "invalid" in message)
        )
