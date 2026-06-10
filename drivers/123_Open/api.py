"""123 云盘开放 API 端点与响应辅助方法。"""

from typing import Any, Dict, Tuple


class Pan123OpenAPI:
    BASE_URL = "https://open-api.123pan.com"
    USER_AGENT = "LitePan/0.3.0-beta"

    ENDPOINTS = {
        "user_info": "/api/v1/user/info",
        "file_list": "/api/v2/file/list",
        "file_detail": "/api/v1/file/detail",
        "file_infos": "/api/v1/file/infos",
        "download": "/api/v1/file/download_info",
        "create_folder": "/upload/v1/file/mkdir",
        "rename": "/api/v1/file/name",
        "move": "/api/v1/file/move",
        "copy": "/api/v1/file/copy",
        "async_copy": "/api/v1/file/async/copy",
        "async_copy_process": "/api/v1/file/async/copy/process",
        "trash": "/api/v1/file/trash",
        "upload_create": "/upload/v2/file/create",
        "upload_complete": "/upload/v2/file/upload_complete",
        "upload_domain": "/upload/v2/file/domain",
        "sha1_reuse": "/upload/v2/file/sha1_reuse",
    }

    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Platform": "open_platform",
    }


class Pan123OpenApiHelper:
    @staticmethod
    def build_headers(access_token: str = "") -> Dict[str, str]:
        headers = Pan123OpenAPI.HEADERS.copy()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    @staticmethod
    def check_success(response: Dict[str, Any]) -> Tuple[bool, str, Any]:
        code = response.get("code", 0)
        message = response.get("message") or response.get("msg") or ""

        if code in (0, "0", None):
            return True, "", code

        if str(code) in ("401", "4010", "4011", "4012"):
            return False, f"Token认证失败: {message or code}", code

        if str(code) == "5066":
            return False, "文件不存在或已被删除", code

        if str(code) == "5113":
            return False, "123云盘开放接口流量已达限制", code

        return False, message or f"123云盘API错误: {code}", code

    @staticmethod
    def is_token_expired(code: Any, message: str = "") -> bool:
        code_text = str(code or "")
        message_text = (message or "").lower()
        return (
            code_text.startswith("401")
            or "access_token" in message_text
            or "token" in message_text and ("过期" in message_text or "invalid" in message_text)
            or "未授权" in message_text
            or "授权" in message_text and "失效" in message_text
        )

    @staticmethod
    def extract_data(response: Dict[str, Any]) -> Any:
        return response.get("data", response)
