"""驱动获取与下载公共服务。"""

import json
import asyncio
from time import monotonic
from dataclasses import dataclass
from typing import Dict, Optional, Any

from core.base import FileItem
from core.error_handler import raise_api_error, raise_not_found
from database.db import db

from .account_utils import ensure_account_active, filter_runtime_config, get_account_or_404
from .operation_wrapper import ensure_driver_auth_request_allowed
from .registry import driver_registry


_download_cache: Dict[str, Dict[str, Any]] = {}
_download_locks: Dict[str, asyncio.Lock] = {}

def _get_download_lock(key: str) -> asyncio.Lock:
    if key not in _download_locks:
        _download_locks[key] = asyncio.Lock()
    return _download_locks[key]


async def get_account_driver(account_id: int, db_session=None):
    if db_session is None:
        account = await get_account_or_404(account_id)
    else:
        cursor = await db_session.execute("SELECT * FROM cloud_accounts WHERE id = ?", (account_id,))
        row = await cursor.fetchone()
        if not row:
            raise_not_found("账号")
        account = dict(row)
        account["config"] = json.loads(account.get("config", "{}"))

    ensure_account_active(account)
    return await get_account_driver_instance(account_id, account=account, require_active=False)


async def get_account_driver_instance(
    account_id: int,
    *,
    account: Optional[Dict] = None,
    require_active: bool = True,
    existing_driver_name: Optional[str] = None,
    config_override: Optional[Dict] = None,
):
    account = account or await get_account_or_404(account_id)
    if require_active:
        ensure_account_active(account)

    try:
        return await driver_registry.get_driver_instance(
            account_id=str(account_id),
            driver_name=existing_driver_name or account["driver_type"],
            config=filter_runtime_config(config_override or account["config"]),
        )
    except ValueError as e:
        raise_api_error(str(e), "get_driver_instance", 400)


@dataclass
class ResolvedDownload:
    download_url: str
    file_name: str
    file_size: int
    file_info: Optional[FileItem] = None
    headers: Optional[Dict[str, str]] = None
    effective_mode: Optional[str] = None


async def resolve_download(
    driver,
    file_id: str,
    user_agent: str = "",
    *,
    file_info: Optional[FileItem] = None,
    force_refresh: bool = False,
) -> ResolvedDownload:
    """解析下载地址 + 文件元数据。ttl=0 也会强制给 1s 的窗口防瞬时并发击穿。

    force_refresh=True 时跳过缓存读取（含 1s 兜底窗口），强制向上游重取直链并刷新缓存，
    用于上一条直链已过期/异常需要换一条新链的补救场景。
    """
    config = getattr(driver, "config", None)
    ttl = getattr(config, "download_url_ttl", 0)

    driver_name = getattr(driver, 'name', getattr(driver.__class__, '__name__', 'unknown'))
    cache_key = f"{driver_name}:{file_id}:{user_agent}"

    now = monotonic()

    # 无锁快读：只有驱动明确声明 ttl>0 才走（force_refresh 直接跳过）
    if ttl > 0 and not force_refresh:
        cached = _download_cache.get(cache_key)
        if cached and now - cached["time"] < ttl:
            return cached["result"]

    lock = _get_download_lock(cache_key)
    async with lock:
        # 双重检查；即使驱动 ttl=0，也给 1s 的兜底窗口，避免同一时刻多个请求都去真请求上游
        now = monotonic()
        cached = _download_cache.get(cache_key)
        effective_ttl = max(ttl, 1)
        if not force_refresh and cached and now - cached["time"] < effective_ttl:
            return cached["result"]

        await ensure_driver_auth_request_allowed(driver)

        if hasattr(driver, "get_download_info"):
            download_info = await driver.get_download_info(file_id, user_agent)
            raw_headers = download_info.get("headers")
            effective_mode = (
                download_info.get("effective_mode")
                or download_info.get("download_mode")
            )
            result = ResolvedDownload(
                download_url=download_info["download_url"],
                file_name=download_info.get("file_name") or f"file_{file_id}",
                file_size=int(download_info.get("size") or 0),
                file_info=file_info,
                headers=dict(raw_headers) if raw_headers is not None else None,
                effective_mode=str(effective_mode).strip() if effective_mode else None,
            )
        else:
            actual_file_info = file_info or await driver.file_info(file_id)
            if not actual_file_info:
                raise_not_found("文件")

            result = ResolvedDownload(
                download_url=await driver.get_download_url(file_id, user_agent),
                file_name=actual_file_info.name or f"file_{file_id}",
                file_size=int(actual_file_info.size or 0),
                file_info=actual_file_info,
            )

        _download_cache[cache_key] = {"time": monotonic(), "result": result}

        # 锁表爆炸兜底：简单整体清掉，保留当前 key
        if len(_download_locks) > 1000:
            _download_locks.clear()
            _download_cache.clear()
            _download_locks[cache_key] = lock
            _download_cache[cache_key] = {"time": monotonic(), "result": result}

        return result


def get_driver_download_mode(driver, default: str = "redirect") -> str:
    config = getattr(driver, "config", None)
    return getattr(config, "download_mode", default) or default


def get_effective_download_mode(
    driver,
    download: Optional[ResolvedDownload] = None,
    default: str = "redirect",
) -> str:
    """读取本次下载真正应该使用的模式。

    个别驱动会先按配置尝试 redirect，但上游不一定每次都能给匿名直链。
    此时驱动可在 get_download_info 返回 effective_mode="proxy"，公共层按
    本次结果处理，避免把需要鉴权的上游地址错误 302 给客户端。
    """
    mode = getattr(download, "effective_mode", None) if download else None
    if mode:
        return str(mode).strip() or default
    return get_driver_download_mode(driver, default)


def get_driver_proxy_part_size(driver) -> int:
    """读取驱动声明的「向上游 CDN 单片请求字节数」。

    驱动可在自己的 Config 上声明：
        proxy_part_size: int = 10 * 1024 * 1024  # 例：夸克

    返回 0 表示驱动未声明，由 range_proxy 用全局默认值（DEFAULT_PROXY_PART_SIZE）兜底。
    """
    config = getattr(driver, "config", None)
    try:
        return int(getattr(config, "proxy_part_size", 0) or 0)
    except (TypeError, ValueError):
        return 0


async def build_upstream_download_headers(
    driver,
    file_id: str,
    user_agent: str = "",
    *,
    range_header: Optional[str] = None,
    prefer_identity: bool = False,
    download: Optional[ResolvedDownload] = None,
    headers_override: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    if headers_override is not None:
        headers = dict(headers_override)
    elif download is not None and download.headers is not None:
        headers = dict(download.headers)
    else:
        headers = {}

    has_explicit_headers = headers_override is not None or (
        download is not None and download.headers is not None
    )
    if not headers and not has_explicit_headers and hasattr(driver, "get_download_headers"):
        await ensure_driver_auth_request_allowed(driver)
        headers = await driver.get_download_headers(file_id, user_agent)

    headers = dict(headers or {})
    if user_agent and "User-Agent" not in headers:
        headers["User-Agent"] = user_agent

    headers.setdefault("Accept", "*/*")
    headers.setdefault("Connection", "keep-alive")

    if prefer_identity:
        headers.setdefault("Accept-Encoding", "identity")

    if range_header:
        headers["Range"] = range_header

    return headers
