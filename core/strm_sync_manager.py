import asyncio
import aiohttp
import os
import re
import time
import shutil
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

from config import config_manager, Settings
from core.log_manager import get_writer, LogModule
from core.driver_base import _extra_api_delay
from core.driver_service import build_upstream_download_headers, get_account_driver, resolve_download
from core.strm_security import (
    build_strm_play_path,
    build_strm_v2_play_path,
    decode_strm_file_key,
    sign_strm_path,
)
from database.db import db


DEFAULT_METADATA_EXTENSIONS = "srt;ass;ssa;sub;nfo;jpg;jpeg;png;webp"
DEFAULT_MEDIA_EXTENSIONS = "mp4;mkv;avi;mov;wmv;flv;ts;m2ts;mpg;mpeg;webm;m4v;iso;rmvb;mp3;flac;aac;wav;m4a"

# Linux ext4 等：单路径分量名上限一般为 255 字节（UTF-8）
_STRM_MAX_COMPONENT_BYTES = 255
STRM_LINK_FORMATS = {"v1", "v2"}


@dataclass
class StrmSyncTask:
    id: int
    name: str
    account_id: int
    parent_id: str
    path: str
    recursive: bool
    scan_interval: int
    scan_mode: str
    concurrency: int
    extensions: str
    exclude_dir_keywords: str
    exclude_file_keywords: str
    sync_metadata: bool
    status: str
    api_interval: int = 200
    file_count: int = 0
    last_created_count: int = 0
    last_updated_count: int = 0
    last_deleted_count: int = 0
    last_duration_ms: int = 0
    last_scan: Optional[datetime] = None
    last_scan_status: Optional[str] = None
    error_message: Optional[str] = None
    next_run_time: Optional[datetime] = None
    paused_reason: Optional[str] = None  # None / 'user' / 'account_disabled' / 'auth_failure'
    time_window_enabled: bool = False
    time_start: str = "00:00"
    time_end: str = "00:00"
    schedule_mode: str = "window"  # 'window'=按全局间隔(可叠加时间段闸门)，'daily'=每天 time_start 定时一次
    branch_check_enabled: bool = False
    scanned_dirs: int = 0
    scanned_files: int = 0
    started_at: Optional[datetime] = None


class StrmSyncManager:
    _FIXED_WRITE_CONCURRENCY = 3

    def __init__(self):
        self._tasks: Dict[int, StrmSyncTask] = {}
        self._running_tasks: Set[int] = set()
        self._queued_tasks: Set[int] = set()
        self._manual_triggered_tasks: Set[int] = set()
        self._pending_run_modes: Dict[int, str] = {}
        self._running_account_ids: Set[int] = set()
        self._task_concurrency_limit = 3
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running_task_futures: Dict[int, asyncio.Task] = {}
        try:
            self._logger = get_writer(LogModule.SYSTEM)
        except RuntimeError:
            self._logger = None
        self._is_running = False
        self._strm_root = Path("strm")
        self._startup_ready_at: float = 0.0
        self._startup_delay_seconds: int = 100
        self._defer_to_cache_retention_seconds: int = 15

    async def _get_runtime_settings(self) -> Tuple[int, int, int]:
        scan_interval = await config_manager.get_async("strm_default_scan_interval")
        task_concurrency = await config_manager.get_async("strm_task_concurrency")
        if task_concurrency is None:
            task_concurrency = 3
            await config_manager.set_async("strm_task_concurrency", int(task_concurrency))
        return int(scan_interval or 60), self._FIXED_WRITE_CONCURRENCY, max(1, min(int(task_concurrency), 10))

    async def initialize(self):
        if not self._logger:
            self._logger = get_writer(LogModule.SYSTEM)
        scan_interval, concurrency, task_concurrency_limit = await self._get_runtime_settings()
        self._task_concurrency_limit = task_concurrency_limit
        tasks = await db.get_strm_sync_tasks()
        previous_running_tasks = set(self._running_tasks)
        previous_queued_tasks = set(self._queued_tasks)
        previous_manual_triggered_tasks = set(self._manual_triggered_tasks)
        previous_pending_run_modes = dict(self._pending_run_modes)
        self._tasks = {}
        for row in tasks:
            last_scan = None
            if row.get("last_scan"):
                try:
                    last_scan = datetime.fromisoformat(str(row["last_scan"]).replace("Z", "+00:00"))
                except Exception:
                    last_scan = None

            task = StrmSyncTask(
                id=int(row["id"]),
                name=str(row["name"]),
                account_id=int(row["account_id"]),
                parent_id=str(row["parent_id"]),
                path=str(row["path"]),
                recursive=True,
                scan_interval=scan_interval,
                scan_mode=str(row.get("scan_mode") or "incremental_missing"),
                concurrency=concurrency,
                extensions=str(row.get("extensions") or ""),
                exclude_dir_keywords=str(row.get("exclude_dir_keywords") or ""),
                exclude_file_keywords=str(row.get("exclude_file_keywords") or ""),
                sync_metadata=bool(row.get("sync_metadata") or False),
                api_interval=int(row.get("api_interval") or Settings.STRM_DEFAULT_API_INTERVAL),
                status=str(row.get("status") or "running"),
                file_count=int(row.get("file_count") or 0),
                last_created_count=int(row.get("last_created_count") or 0),
                last_updated_count=int(row.get("last_updated_count") or 0),
                last_deleted_count=int(row.get("last_deleted_count") or 0),
                last_duration_ms=int(row.get("last_duration_ms") or 0),
                last_scan=last_scan,
                last_scan_status=row.get("last_scan_status"),
                error_message=row.get("error_message"),
                paused_reason=row.get("paused_reason"),
                time_window_enabled=bool(row.get("time_window_enabled") or False),
                time_start=str(row.get("time_start") or "00:00"),
                time_end=str(row.get("time_end") or "00:00"),
                schedule_mode=("daily" if row.get("schedule_mode") == "daily" else "window"),
                branch_check_enabled=bool(row.get("branch_check_enabled") or False),
            )

            if task.status == "running":
                if task.schedule_mode == "daily":
                    task.next_run_time = self._compute_next_run(task, scan_interval)
                elif task.last_scan:
                    task.next_run_time = self._compute_next_run(task, scan_interval, base=task.last_scan)
                else:
                    task.next_run_time = datetime.now()
            else:
                task.next_run_time = None

            self._tasks[task.id] = task

        self._running_tasks = {task_id for task_id in previous_running_tasks if task_id in self._tasks}
        self._queued_tasks = {
            task_id for task_id in previous_queued_tasks
            if task_id in self._tasks and task_id not in self._running_tasks
        }
        self._manual_triggered_tasks = {
            task_id for task_id in previous_manual_triggered_tasks
            if task_id in self._tasks and task_id not in self._running_tasks
        }
        self._pending_run_modes = {
            task_id: mode
            for task_id, mode in previous_pending_run_modes.items()
            if task_id in self._tasks and task_id not in self._running_tasks
        }
        self._running_account_ids = {
            self._tasks[task_id].account_id
            for task_id in self._running_tasks
            if task_id in self._tasks
        }

        self._logger.debug(f"🎞️ STRM同步管理器初始化完成，加载了 {len(self._tasks)} 个任务")

    @property
    def startup_remaining(self) -> int:
        return max(0, int(self._startup_ready_at - time.time()))

    async def start(self):
        if self._is_running:
            return
        self._is_running = True
        self._startup_ready_at = time.time() + self._startup_delay_seconds + self._defer_to_cache_retention_seconds
        self._logger.info(f"STRM 调度器将在 {self._startup_delay_seconds + self._defer_to_cache_retention_seconds}s 后开始执行任务（含 {self._defer_to_cache_retention_seconds}s 缓存保持优先延迟）")
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        self._is_running = False
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        for future in list(self._running_task_futures.values()):
            if not future.done():
                future.cancel()
        if self._running_task_futures:
            await asyncio.gather(*self._running_task_futures.values(), return_exceptions=True)
            self._running_task_futures.clear()

    def _sanitize_task_folder(self, name: str) -> str:
        safe = self._sanitize_path_component(name, kind="task")
        safe = re.sub(r"[\\\\/:*?\"<>|]+", "_", safe).strip()
        return safe or "task"

    def _contains_embedded_null(self, value: str) -> bool:
        return "\x00" in str(value or "")

    def _is_embedded_null_error(self, err: BaseException) -> bool:
        return "null" in str(err).lower()

    def _sanitize_path_component(
        self,
        value: str,
        *,
        kind: str,
        file_id: str = "",
        parent_path: str = "",
    ) -> str:
        raw = str(value or "")
        if not self._contains_embedded_null(raw):
            return raw
        cleaned = raw.replace("\x00", "").strip()
        if self._logger:
            self._logger.warning(
                "STRM路径含隐藏空字符已自动清理: kind=%s file_id=%s parent=%s raw=%r cleaned=%r null_count=%d",
                kind,
                file_id or "-",
                parent_path or "-",
                raw,
                cleaned,
                raw.count("\x00"),
            )
        if cleaned:
            return cleaned
        return {"file": "metadata", "dir": "folder", "folder": "folder", "task": "task"}.get(kind, "item")

    def _log_strm_path_error(
        self,
        err: BaseException,
        *,
        action: str,
        file_id: str = "",
        file_name: str = "",
        relative_dir: Any = "",
        remote_path: str = "",
        local_path: Any = "",
    ) -> None:
        if not self._logger:
            return
        level = "error" if self._is_embedded_null_error(err) else "warning"
        message = (
            f"STRM路径错误({action}): {err} | "
            f"file_id={file_id or '-'} file_name={file_name!r} "
            f"relative_dir={relative_dir or '-'} remote_path={remote_path or '-'} "
            f"local_path={local_path or '-'}"
        )
        getattr(self._logger, level)(message)

    def _get_task_root(self, task_name: str) -> Path:
        return self._strm_root / self._sanitize_task_folder(task_name)

    def _strm_path_has_oversized_component(self, path: Path) -> bool:
        """任一路径段长度超过系统单分量上限则无法创建文件（跳过 STRM，不截断）。"""
        for part in path.parts:
            if part in ("/", "\\", ""):
                continue
            try:
                if len(os.fsencode(part)) > _STRM_MAX_COMPONENT_BYTES:
                    return True
            except Exception:
                return True
        return False

    def _parse_extensions(self, text: str) -> Set[str]:
        default_exts = {
            "mp4", "mkv", "avi", "mov", "wmv", "flv", "ts", "m2ts",
            "mpg", "mpeg", "webm", "m4v", "iso", "rmvb",
            "mp3", "flac", "aac", "wav", "m4a",
        }
        raw = (text or "").strip()
        if not raw:
            return default_exts
        parts = [p.strip().lower().lstrip(".") for p in raw.split(";") if p.strip()]
        return set(parts) or default_exts

    def _parse_optional_extensions(self, text: str) -> Set[str]:
        raw = str(text or "").strip()
        if not raw:
            return set()
        raw = raw.replace(",", ";")
        return {p.strip().lower().lstrip(".") for p in raw.split(";") if p.strip()}

    async def _get_bool_setting(self, key: str, default: bool) -> bool:
        value = await config_manager.get_async(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        text = str(value).strip().lower()
        if text in ("0", "false", "no", "off", ""):
            return False
        if text in ("1", "true", "yes", "on"):
            return True
        return default

    async def _get_int_setting(self, key: str, default: int, min_value: int, max_value: int) -> int:
        value = await config_manager.get_async(key)
        try:
            number = int(value)
        except Exception:
            number = default
        return max(min_value, min(number, max_value))

    async def _get_str_setting(self, key: str, default: str) -> str:
        value = await config_manager.get_async(key)
        if value is None:
            return default
        return str(value or "")

    def _parse_keyword_rules(self, text: str) -> List[str]:
        return [item.strip().lower() for item in str(text or "").split(";") if item.strip()]

    def _matches_keyword_rules(self, text: str, rules: List[str]) -> bool:
        candidate = str(text or "").lower()
        return any(rule in candidate for rule in rules)

    async def _get_strm_base_url(self) -> str:
        value = await config_manager.get_async("strm_base_url")
        configured = str(value or "").strip().rstrip("/")
        if configured:
            return configured
        return f"http://127.0.0.1:{int(Settings.WEB_PORT)}"

    async def _get_strm_link_format(self) -> str:
        value = str(await config_manager.get_async("strm_link_format") or "v1").strip().lower()
        return value if value in STRM_LINK_FORMATS else "v1"

    async def _get_strm_token(self) -> str:
        value = await config_manager.get_async("strm_token")
        token = str(value or "").strip()
        if token:
            return token
        import secrets
        token = secrets.token_urlsafe(32)
        await config_manager.set_async("strm_token", token)
        return token

    async def _scheduler_loop(self):
        while self._is_running:
            remaining = self.startup_remaining
            if remaining > 0:
                await asyncio.sleep(1)
                continue

            _, _, task_concurrency_limit = await self._get_runtime_settings()
            self._task_concurrency_limit = task_concurrency_limit
            now = datetime.now()
            runnable: List[Tuple[int, datetime]] = []
            for task_id, task in self._tasks.items():
                manual_triggered = task_id in self._manual_triggered_tasks
                if task.status != "running" and not manual_triggered:
                    self._queued_tasks.discard(task_id)
                    continue
                if task_id in self._running_tasks:
                    continue
                if not manual_triggered and not self._is_in_time_window(task):
                    continue
                if task.next_run_time and task.next_run_time <= now:
                    runnable.append((task_id, task.next_run_time))

            runnable.sort(key=lambda x: x[1])
            for task_id, _ in runnable:
                self._start_task_if_possible(task_id)

            await asyncio.sleep(2)

    @staticmethod
    def _next_daily_run(time_start: str, base: Optional[datetime] = None) -> datetime:
        """返回下一次每日定时时间：base 当天的 time_start，若已过则取次日同点。"""
        base = base or datetime.now()
        try:
            h, m = map(int, str(time_start or "00:00").split(":"))
        except (ValueError, AttributeError):
            h, m = 0, 0
        candidate = base.replace(hour=h, minute=m, second=0, microsecond=0)
        if candidate <= base:
            candidate += timedelta(days=1)
        return candidate

    def _compute_next_run(self, task: StrmSyncTask, scan_interval: int, base: Optional[datetime] = None) -> datetime:
        """统一计算下次执行时间：每日定时模式忽略全局间隔，按 time_start 排次日；其余按间隔。"""
        if task.schedule_mode == "daily":
            return self._next_daily_run(task.time_start)
        base = base or datetime.now()
        return base + timedelta(minutes=scan_interval)

    @staticmethod
    def _is_in_time_window(task: StrmSyncTask) -> bool:
        if task.schedule_mode == "daily":
            return True
        if not task.time_window_enabled:
            return True
        try:
            now = datetime.now().time()
            start_h, start_m = map(int, task.time_start.split(":"))
            end_h, end_m = map(int, task.time_end.split(":"))
            start_t = datetime.now().replace(hour=start_h, minute=start_m, second=0, microsecond=0).time()
            end_t = datetime.now().replace(hour=end_h, minute=end_m, second=0, microsecond=0).time()
            if start_t <= end_t:
                return start_t <= now <= end_t
            else:
                return now >= start_t or now <= end_t
        except (ValueError, AttributeError):
            return True

    def _can_start_task(self, task: Optional[StrmSyncTask]) -> bool:
        if not task:
            return False
        if len(self._running_tasks) >= self._task_concurrency_limit:
            return False
        if task.account_id in self._running_account_ids:
            return False
        try:
            from core.cache_retention_manager import cache_retention_manager
            if task.account_id in cache_retention_manager.get_running_account_ids():
                return False
        except Exception:
            pass
        return True

    def _start_task_if_possible(self, task_id: int) -> bool:
        task = self._tasks.get(task_id)
        allow_manual = task_id in self._manual_triggered_tasks
        if not task or (task.status != "running" and not allow_manual):
            self._queued_tasks.discard(task_id)
            self._manual_triggered_tasks.discard(task_id)
            return False
        if task_id in self._running_tasks:
            self._queued_tasks.discard(task_id)
            return True
        if not self._can_start_task(task):
            self._queued_tasks.add(task_id)
            return False
        self._queued_tasks.discard(task_id)
        self._manual_triggered_tasks.discard(task_id)
        run_mode = self._pending_run_modes.pop(task_id, "auto")
        self._running_tasks.add(task_id)
        self._running_account_ids.add(task.account_id)
        future = asyncio.create_task(self._run_task(task_id, run_mode=run_mode))
        self._running_task_futures[task_id] = future
        return True

    async def run_task_now(self, task_id: int, run_mode: str = "auto") -> str:
        task = self._tasks.get(task_id)
        if not task:
            return "missing"
        if run_mode not in {"auto", "full", "branch"}:
            run_mode = "auto"
        task.next_run_time = datetime.now()
        if task_id in self._running_tasks:
            self._queued_tasks.discard(task_id)
            return "already_running"
        self._pending_run_modes[task_id] = run_mode
        if task_id in self._queued_tasks:
            return "already_queued"
        self._manual_triggered_tasks.add(task_id)
        if self._start_task_if_possible(task_id):
            return "running"
        self._queued_tasks.add(task_id)
        return "queued"

    async def force_stop_task(self, task_id: int) -> bool:
        """强制停止正在执行的 STRM 任务，不改变状态，不影响下次调度。"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        future = self._running_task_futures.get(task_id)
        if future and not future.done():
            future.cancel()

        self._running_tasks.discard(task_id)
        self._running_task_futures.pop(task_id, None)
        self._pending_run_modes.pop(task_id, None)
        self._running_account_ids.discard(task.account_id)

        if task.next_run_time is None:
            task.next_run_time = datetime.now()

        self._logger.info(f"强制停止 STRM 任务 {task_id}（下次调度不受影响）")
        return True

    def get_running_task_ids(self) -> Set[int]:
        return set(self._running_tasks)

    def get_queued_task_ids(self) -> Set[int]:
        return set(self._queued_tasks)

    def get_running_account_ids(self) -> Set[int]:
        """返回当前正在执行 STRM 任务的账号 ID 集合，供缓存保持管理器跨管理器互斥。"""
        return set(self._running_account_ids)

    async def refresh_tasks_from_db(self):
        await self.initialize()

    async def _collect_files(
        self,
        driver,
        parent_id: str,
        base_posix_path: str,
        recursive: bool,
        extensions: Set[str],
        metadata_extensions: Set[str],
        metadata_max_size_bytes: int,
        min_media_size_bytes: int,
        metadata_parent_enabled: bool,
        exclude_dir_rules: List[str],
        exclude_file_rules: List[str],
        relative_parts: PurePosixPath,
        result: List[Tuple[str, str, str, int, Optional[datetime], PurePosixPath]],
        metadata_result: Optional[List[Tuple[str, str, int, Optional[datetime], PurePosixPath, str]]] = None,
        task: Optional[StrmSyncTask] = None,
        is_root: bool = False,
        skipped_dirs: Optional[Set[PurePosixPath]] = None,
    ) -> bool:
        try:
            files = await driver.list_files(parent_id)
        except Exception as e:
            # 根路径（任务配置的根/各分支根）列举失败：直接失败，让用户知道任务路径已不可用。
            if is_root:
                raise
            # 子目录列举失败（典型：WebDAV 上游某挂载点 404/不可达）：记警告并跳过该子树。
            # 同时登记到 skipped_dirs，清理阶段会保留该子树下已存在的 strm，避免误删。
            if self._logger:
                self._logger.warning(
                    f"STRM跳过无法列举的子目录: account={getattr(task, 'account_id', '-')} "
                    f"base={base_posix_path} rel={str(relative_parts) or '.'} err={e}"
                )
            if skipped_dirs is not None:
                skipped_dirs.add(relative_parts)
            return False
        return await self._collect_files_from_items(
            driver,
            files,
            base_posix_path,
            recursive,
            extensions,
            metadata_extensions,
            metadata_max_size_bytes,
            min_media_size_bytes,
            metadata_parent_enabled,
            exclude_dir_rules,
            exclude_file_rules,
            relative_parts,
            result,
            metadata_result,
            task,
            skipped_dirs,
        )

    async def _collect_files_from_items(
        self,
        driver,
        files: List[Any],
        base_posix_path: str,
        recursive: bool,
        extensions: Set[str],
        metadata_extensions: Set[str],
        metadata_max_size_bytes: int,
        min_media_size_bytes: int,
        metadata_parent_enabled: bool,
        exclude_dir_rules: List[str],
        exclude_file_rules: List[str],
        relative_parts: PurePosixPath,
        result: List[Tuple[str, str, str, int, Optional[datetime], PurePosixPath]],
        metadata_result: Optional[List[Tuple[str, str, int, Optional[datetime], PurePosixPath, str]]] = None,
        task: Optional[StrmSyncTask] = None,
        skipped_dirs: Optional[Set[PurePosixPath]] = None,
    ) -> bool:
        directory_metadata: List[Tuple[str, str, int, Optional[datetime], PurePosixPath, str]] = []
        directory_has_media = False
        subtree_has_media = False
        for item in files:
            item_id = str(item.id)
            name = self._sanitize_path_component(
                str(item.name),
                kind="dir" if item.is_dir else "file",
                file_id=item_id,
                parent_path=str(relative_parts),
            )
            if item.is_dir:
                if self._matches_keyword_rules(name, exclude_dir_rules):
                    continue
                if recursive:
                    child_has_media = await self._collect_files(
                        driver,
                        item_id,
                        base_posix_path,
                        recursive,
                        extensions,
                        metadata_extensions,
                        metadata_max_size_bytes,
                        min_media_size_bytes,
                        metadata_parent_enabled,
                        exclude_dir_rules,
                        exclude_file_rules,
                        relative_parts / name,
                        result,
                        metadata_result,
                        task=task,
                        is_root=False,
                        skipped_dirs=skipped_dirs,
                    )
                    subtree_has_media = subtree_has_media or child_has_media
                continue

            if self._matches_keyword_rules(name, exclude_file_rules):
                continue
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            size = int(getattr(item, "size", 0) or 0)
            if metadata_result is not None and ext in metadata_extensions:
                if metadata_max_size_bytes <= 0 or size <= metadata_max_size_bytes:
                    remote_rel = relative_parts / name
                    remote_path = str(PurePosixPath(base_posix_path) / remote_rel)
                    directory_metadata.append(
                        (item_id, name, size, getattr(item, "modified", None), relative_parts, remote_path)
                    )
                continue
            if ext not in extensions:
                continue
            if min_media_size_bytes > 0 and size < min_media_size_bytes:
                continue

            remote_rel = relative_parts / name
            remote_path = str(PurePosixPath(base_posix_path) / remote_rel)
            directory_has_media = True
            if task:
                task.scanned_files += 1
            result.append(
                (
                    item_id,
                    name,
                    remote_path,
                    size,
                    getattr(item, "modified", None),
                    relative_parts,
                )
            )
        if task:
            task.scanned_dirs += 1
        subtree_has_media = subtree_has_media or directory_has_media
        if metadata_result is not None and (directory_has_media or (metadata_parent_enabled and subtree_has_media)):
            metadata_result.extend(directory_metadata)
        return subtree_has_media

    def _is_strm_under_skipped(
        self,
        strm_rel_text: str,
        task_folder: str,
        skipped_dirs: Set[PurePosixPath],
    ) -> bool:
        """判断某个 strm 文件（相对 strm 根的路径）是否落在被跳过的子树下，落在则清理时应保留。"""
        if not skipped_dirs:
            return False
        strm_path = PurePosixPath(strm_rel_text)
        for skipped in skipped_dirs:
            skipped_text = str(skipped).strip("/")
            prefix = PurePosixPath(task_folder) / skipped_text if skipped_text and skipped_text != "." else PurePosixPath(task_folder)
            try:
                strm_path.relative_to(prefix)
                return True
            except ValueError:
                continue
        return False

    def _media_stem(self, file_name: str) -> str:
        name = str(file_name or "")
        return name.rsplit(".", 1)[0] if "." in name else name

    def _build_local_rel_path(self, task_folder: str, relative_dir: PurePosixPath, file_name: str) -> str:
        safe_name = self._safe_child_name(self._media_stem(file_name))
        local_rel = PurePosixPath(task_folder) / relative_dir / f"{safe_name}.strm"
        return str(local_rel)

    def _build_legacy_local_rel_path(self, task_folder: str, relative_dir: PurePosixPath, file_name: str) -> Optional[str]:
        safe_name = self._safe_child_name(file_name)
        local_rel = PurePosixPath(task_folder) / relative_dir / f"{safe_name}.strm"
        return str(local_rel)

    def _build_play_url(
        self,
        base_url: str,
        account_id: int,
        file_id: str,
        token: str,
        signature_enabled: bool,
        link_format: str = "v1",
    ) -> str:
        if link_format == "v2":
            return f"{base_url}{build_strm_v2_play_path(account_id, file_id, token, signature_enabled)}"

        play_path = build_strm_play_path(account_id, file_id)
        params = [("token", token)]
        if signature_enabled:
            params.append(("sign", sign_strm_path(play_path)))
        return f"{base_url}{play_path}?{urllib.parse.urlencode(params)}"

    def _normalize_display_path(self, path: str) -> str:
        value = "/" + str(path or "").strip("/")
        return "/" if value == "/" else value.rstrip("/")

    def _relative_display_path(self, task_path: str, current_path: str) -> Optional[PurePosixPath]:
        task_norm = self._normalize_display_path(task_path)
        current_norm = self._normalize_display_path(current_path)
        if current_norm == task_norm:
            return PurePosixPath()
        prefix = task_norm.rstrip("/") + "/"
        if current_norm.startswith(prefix):
            return PurePosixPath(current_norm[len(prefix):].strip("/"))
        return None

    def _parse_item_modified(self, value: object) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    async def generate_current_directory_strm(
        self,
        account_id: int,
        current_path: str,
        items: List[Dict[str, object]],
    ) -> Dict[str, int]:
        """按需同步当前目录的浅层 STRM，不递归、不同步元数据。"""
        tasks = await db.get_strm_sync_tasks()
        candidates: List[Tuple[int, Dict[str, object], PurePosixPath]] = []
        current_norm = self._normalize_display_path(current_path)
        for task in tasks:
            if int(task.get("account_id") or 0) != int(account_id):
                continue
            relative_dir = self._relative_display_path(str(task.get("path") or ""), current_norm)
            if relative_dir is None:
                continue
            task_path_len = len(self._normalize_display_path(str(task.get("path") or "")))
            candidates.append((task_path_len, task, relative_dir))

        if not candidates:
            return {
                "matched_task_id": 0,
                "created": 0,
                "updated": 0,
                "skipped_existing": 0,
                "skipped_conflict": 0,
                "skipped_path_too_long": 0,
                "deleted": 0,
                "media_count": 0,
            }

        _task_path_len, task, relative_dir = max(candidates, key=lambda item: item[0])
        task_id = int(task.get("id") or 0)
        task_name = str(task.get("name") or "")
        task_folder = self._sanitize_task_folder(task_name)
        task_root = self._get_task_root(task_name)
        task_root.mkdir(parents=True, exist_ok=True)

        base_url = await self._get_strm_base_url()
        token = await self._get_strm_token()
        link_format = await self._get_strm_link_format()
        signature_enabled = await self._get_bool_setting("strm_signature_enabled", False)
        default_extensions = await self._get_str_setting("strm_default_extensions", DEFAULT_MEDIA_EXTENSIONS)
        extensions = self._parse_extensions(str(task.get("extensions") or "") or default_extensions)
        min_media_size_mb = await self._get_int_setting("strm_min_file_size_mb", 0, 0, 10240)
        min_media_size_bytes = min_media_size_mb * 1024 * 1024
        conflict_policy = self._normalize_conflict_policy(
            await self._get_str_setting("strm_conflict_policy", "size_desc")
        )
        scan_mode = str(task.get("scan_mode") or "incremental_update")

        collected: List[Tuple[str, str, str, int, Optional[datetime], PurePosixPath]] = []
        current_base = self._normalize_display_path(current_norm)
        remote_dir_names: Set[str] = set()
        for item in items or []:
            if bool(item.get("is_dir")):
                name = str(item.get("name") or "").strip()
                if name:
                    remote_dir_names.add(name)
                continue
            file_name = str(item.get("name") or "")
            ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
            if ext not in extensions:
                continue
            size = int(item.get("size") or 0)
            if min_media_size_bytes > 0 and size < min_media_size_bytes:
                continue
            file_id = str(item.get("id") or "")
            if not file_id:
                continue
            remote_path = str(PurePosixPath(current_base) / file_name)
            collected.append(
                (
                    file_id,
                    file_name,
                    remote_path,
                    size,
                    self._parse_item_modified(item.get("modified")),
                    relative_dir,
                )
            )

        selected, skipped_conflict = self._select_conflict_winners(collected, conflict_policy)
        created = 0
        updated = 0
        skipped_existing = 0
        deleted = 0
        desired_abs_paths: Set[Path] = set()

        skipped_path_too_long = 0
        for file_id, file_name, _remote_path, _size, _modified, item_relative_dir in selected:
            local_rel_path = self._build_local_rel_path(task_folder, item_relative_dir, file_name)
            local_abs_path = task_root / PurePosixPath(local_rel_path).relative_to(task_folder)
            if self._strm_path_has_oversized_component(local_abs_path):
                skipped_path_too_long += 1
                if self._logger:
                    self._logger.warning(
                        f"STRM跳过(路径分量超过{_STRM_MAX_COMPONENT_BYTES}字节): {file_name}"
                    )
                continue
            desired_abs_paths.add(local_abs_path)
            try:
                local_abs_path.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, ValueError) as err:
                self._log_strm_path_error(
                    err,
                    action="mkdir",
                    file_id=file_id,
                    file_name=file_name,
                    relative_dir=item_relative_dir,
                    local_path=local_abs_path,
                )
                continue
            local_exists = local_abs_path.exists()

            if not local_exists:
                legacy_rel_path = self._build_legacy_local_rel_path(task_folder, item_relative_dir, file_name)
                if legacy_rel_path and legacy_rel_path != local_rel_path:
                    legacy_abs_path = task_root / PurePosixPath(legacy_rel_path).relative_to(task_folder)
                    if legacy_abs_path.exists():
                        try:
                            legacy_abs_path.replace(local_abs_path)
                            local_exists = True
                        except OSError as err:
                            if self._logger:
                                self._logger.warning(f"STRM旧格式迁移失败: {legacy_abs_path.name} - {err}")

            url = self._build_play_url(base_url, int(account_id), file_id, token, signature_enabled, link_format)
            if local_exists:
                if scan_mode == "incremental_missing":
                    skipped_existing += 1
                    continue
                try:
                    if local_abs_path.read_text(encoding="utf-8").strip() == url:
                        skipped_existing += 1
                        continue
                except Exception:
                    pass
                updated += 1
            else:
                created += 1
            try:
                local_abs_path.write_text(url + "\n", encoding="utf-8")
            except (OSError, ValueError) as err:
                self._log_strm_path_error(
                    err,
                    action="write",
                    file_id=file_id,
                    file_name=file_name,
                    relative_dir=item_relative_dir,
                    local_path=local_abs_path,
                )
                continue

        if scan_mode in {"incremental_update", "full_sync"}:
            current_local_dir = task_root if str(relative_dir).strip("/") in {"", "."} else task_root / relative_dir
            if current_local_dir.exists() and current_local_dir.is_dir():
                for file_path in current_local_dir.glob("*.strm"):
                    if file_path not in desired_abs_paths:
                        try:
                            file_path.unlink(missing_ok=True)
                            deleted += 1
                        except OSError as err:
                            if self._logger:
                                self._logger.warning(f"STRM当前目录清理失败: {file_path.name} - {err}")
                for child in current_local_dir.iterdir():
                    if not child.is_dir() or child.name in remote_dir_names:
                        continue
                    strm_count = sum(1 for _ in child.rglob("*.strm"))
                    try:
                        shutil.rmtree(child)
                        deleted += strm_count
                    except OSError as err:
                        if self._logger:
                            self._logger.warning(f"STRM当前目录子目录清理失败: {child} - {err}")

        return {
            "matched_task_id": task_id,
            "created": created,
            "updated": updated,
            "skipped_existing": skipped_existing,
            "skipped_conflict": skipped_conflict,
            "skipped_path_too_long": skipped_path_too_long,
            "deleted": deleted,
            "media_count": len(selected),
        }

    def _safe_child_name(self, name: str) -> str:
        safe = self._sanitize_path_component(name, kind="file")
        safe = safe.replace("/", "_").replace("\\", "_").strip()
        return safe or "metadata"

    def _normalize_conflict_policy(self, policy: str) -> str:
        normalized = str(policy or "size_desc")
        if normalized == "quality_then_size":
            return "size_desc"
        if normalized not in {"size_desc", "size_asc", "name_asc"}:
            return "size_desc"
        return normalized

    def _select_conflict_winners(
        self,
        items: List[Tuple[str, str, str, int, Optional[datetime], PurePosixPath]],
        policy: str,
    ) -> Tuple[List[Tuple[str, str, str, int, Optional[datetime], PurePosixPath]], int]:
        grouped: Dict[Tuple[str, str], List[Tuple[str, str, str, int, Optional[datetime], PurePosixPath]]] = {}
        for item in items:
            _file_id, file_name, _remote_path, _size, _modified, relative_dir = item
            stem_key = self._safe_child_name(self._media_stem(file_name)).casefold()
            grouped.setdefault((str(relative_dir), stem_key), []).append(item)

        selected: List[Tuple[str, str, str, int, Optional[datetime], PurePosixPath]] = []
        skipped_count = 0
        normalized_policy = self._normalize_conflict_policy(policy)

        for group_items in grouped.values():
            if len(group_items) == 1:
                selected.append(group_items[0])
                continue

            def stable_tail(item):
                file_id, file_name, _remote_path, _size, _modified, _relative_dir = item
                return str(file_name or "").casefold(), str(file_id)

            if normalized_policy == "size_asc":
                winner = min(group_items, key=lambda item: (int(item[3] or 0), stable_tail(item)))
            elif normalized_policy == "name_asc":
                winner = min(group_items, key=lambda item: stable_tail(item))
            else:
                winner = max(group_items, key=lambda item: (int(item[3] or 0), stable_tail(item)))

            selected.append(winner)
            skipped_count += len(group_items) - 1
            if self._logger:
                for loser in group_items:
                    if loser is winner:
                        continue
                    self._logger.info(
                        f"STRM同名冲突跳过: {loser[1]} 被 {winner[1]} 替代"
                    )

        selected.sort(key=lambda item: (str(item[5]), self._safe_child_name(self._media_stem(item[1])).casefold(), str(item[0])))
        return selected, skipped_count

    _EPISODE_NAME_PATTERN = re.compile(
        r"(?ix)"
        r"("
        r"s\d{1,2}[\s._-]*e\d{1,3}"
        r"|s\d{1,2}[\s._-]*ep\d{1,3}"
        r"|(?<![a-z0-9])ep?[\s._-]*\d{1,3}(?![a-z0-9])"
        r"|第\s*\d{1,4}\s*[集话話]"
        r")"
    )

    def _looks_like_episode_file(self, file_name: str, media_extensions: Set[str]) -> bool:
        name = str(file_name or "")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in media_extensions:
            return False
        return bool(self._EPISODE_NAME_PATTERN.search(name))

    async def _should_auto_add_temporary_branch(
        self,
        driver,
        folder_id: str,
        media_extensions: Set[str],
    ) -> bool:
        try:
            items = await driver.list_files(str(folder_id))
        except Exception as err:
            if self._logger:
                self._logger.debug(f"STRM自动分支候选检查失败: folder_id={folder_id} - {err}")
            return False

        for item in items:
            if getattr(item, "is_dir", False):
                return True
            if self._looks_like_episode_file(str(item.name), media_extensions):
                return True
        return False

    async def _discover_missing_temporary_branches(
        self,
        driver,
        task: StrmSyncTask,
        task_root: Path,
        base_branch: Dict[str, object],
        existing_parent_ids: Set[str],
        media_extensions: Set[str],
        metadata_extensions: Set[str],
        metadata_max_size_bytes: int,
        min_media_size_bytes: int,
        metadata_parent_enabled: bool,
        exclude_dir_rules: List[str],
        exclude_file_rules: List[str],
        base_posix_path: str,
        result: List[Tuple[str, str, str, int, Optional[datetime], PurePosixPath]],
        metadata_result: Optional[List[Tuple[str, str, int, Optional[datetime], PurePosixPath, str]]] = None,
    ) -> Tuple[List[Dict[str, object]], Optional[Set[str]]]:
        """基础分支浅层探测：补扫本地缺失的直接子目录，并按规则自动加入临时分支。"""
        discovered: List[Dict[str, object]] = []
        remote_child_names: Set[str] = set()
        try:
            items = await driver.list_files(str(base_branch.get("parent_id") or ""))
        except Exception as err:
            if self._logger:
                self._logger.warning(f"STRM基础分支探测失败: {base_branch.get('path')} - {err}")
            return discovered, None

        base_relative_text = str(base_branch.get("relative_path") or "").strip("/")
        base_relative = PurePosixPath(base_relative_text) if base_relative_text else PurePosixPath()
        base_path = str(base_branch.get("path") or "").rstrip("/")
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()

        await self._collect_files_from_items(
            driver=driver,
            files=items,
            base_posix_path=base_posix_path,
            recursive=False,
            extensions=media_extensions,
            metadata_extensions=metadata_extensions,
            metadata_max_size_bytes=metadata_max_size_bytes,
            min_media_size_bytes=min_media_size_bytes,
            metadata_parent_enabled=metadata_parent_enabled,
            exclude_dir_rules=exclude_dir_rules,
            exclude_file_rules=exclude_file_rules,
            relative_parts=base_relative,
            result=result,
            metadata_result=metadata_result,
            task=task,
        )

        for item in items:
            if not getattr(item, "is_dir", False):
                continue
            child_id = str(item.id)
            child_name = self._sanitize_path_component(
                str(item.name),
                kind="dir",
                file_id=child_id,
                parent_path=str(base_relative),
            )
            remote_child_names.add(child_name)
            if child_id in existing_parent_ids:
                continue

            child_relative = base_relative / child_name
            child_path = f"{base_path}/{child_name}" if base_path else f"/{child_name}"
            local_child_root = task_root / child_relative
            has_local_strm = local_child_root.exists() and any(local_child_root.rglob("*.strm"))
            if has_local_strm:
                continue

            branch = {
                "id": None,
                "task_id": task.id,
                "account_id": task.account_id,
                "parent_id": child_id,
                "path": child_path,
                "relative_path": str(child_relative),
                "recursive": 1,
                "retention_days": 0,
                "expires_at": None,
                "branch_type": "discovered_child",
                "source": "auto",
                "status": "running",
            }

            if not await self._should_auto_add_temporary_branch(driver, child_id, media_extensions):
                if self._logger:
                    self._logger.debug(f"STRM自动临时分支跳过非剧集目录: {child_path}")
                discovered.append(branch)
                continue
            try:
                branch_id = await db.create_strm_sync_branch(
                    task_id=task.id,
                    account_id=task.account_id,
                    parent_id=child_id,
                    path=child_path,
                    relative_path=str(child_relative),
                    recursive=True,
                    retention_days=30,
                    expires_at=expires_at,
                    branch_type="temporary",
                    source="auto",
                    status="running",
                )
            except Exception as err:
                if self._logger:
                    self._logger.debug(f"STRM自动临时分支创建跳过: {child_path} - {err}")
                discovered.append(branch)
                continue

            existing_parent_ids.add(child_id)
            branch.update({
                "id": branch_id,
                "retention_days": 30,
                "expires_at": expires_at,
                "branch_type": "temporary",
            })
            discovered.append(branch)
            if self._logger:
                self._logger.info(f"STRM自动加入临时分支: {child_path}")

        return discovered, remote_child_names

    def _first_child_name_under_base(
        self,
        relative: PurePosixPath,
        base_relative: PurePosixPath,
    ) -> Optional[str]:
        relative_text = str(relative).strip("/")
        base_text = str(base_relative).strip("/")
        if base_text in {"", "."}:
            suffix = relative_text
        elif relative_text == base_text:
            return None
        elif relative_text.startswith(f"{base_text}/"):
            suffix = relative_text[len(base_text) + 1:]
        else:
            return None
        child_name = suffix.split("/", 1)[0].strip()
        return child_name or None

    def _cleanup_missing_base_child_dirs(
        self,
        task_root: Path,
        base_relative: PurePosixPath,
        remote_child_names: Set[str],
    ) -> int:
        base_text = str(base_relative).strip("/")
        local_base = task_root if base_text in {"", "."} else task_root / base_relative
        if not local_base.exists() or not local_base.is_dir():
            return 0

        deleted = 0
        for child in local_base.iterdir():
            if not child.is_dir() or child.name in remote_child_names:
                continue
            strm_count = sum(1 for _ in child.rglob("*.strm"))
            try:
                shutil.rmtree(child)
                deleted += strm_count
                if self._logger:
                    self._logger.info(f"STRM分支清理远端已删除目录: {child}")
            except OSError as err:
                if self._logger:
                    self._logger.warning(f"STRM分支目录清理失败: {child} - {err}")
        return deleted

    # CDN 直链下载并发上限（115/夸克的 CDN 不走风控 API，多线程下载等同 IDM/Emby 行为）
    _METADATA_CDN_CONCURRENCY = 3

    async def _sync_metadata_files(
        self,
        driver,
        task_root: Path,
        metadata_items: List[Tuple[str, str, int, Optional[datetime], PurePosixPath, str]],
        concurrency: int,
    ) -> int:
        """元数据（nfo / 海报 / 字幕）下载：

        - 生产者(1 协程)：串行调 resolve_download，节流由驱动层 wait_for_request_interval 统一处理；
        - 消费者(N 协程)：并发 HTTP GET CDN 直链写盘，**CDN 不风控**，能显著降低总耗时；
        - 生产者阶段按 file_id 去重，相同 file_id 只 resolve + 下载一次，写到所有 target 路径。

        参数 `concurrency` 仅影响 CDN 下载侧；resolve_download 永远串行。
        """
        if not metadata_items:
            return 0

        # 1. 预聚合：同一 file_id 只下载一次，写到所有 target 路径
        items_by_file_id: Dict[str, Dict[str, Any]] = {}
        seen_paths: Set[str] = set()
        for file_id, file_name, _size, _modified, relative_dir, remote_path in metadata_items:
            file_id = str(file_id)
            safe_name = self._safe_child_name(file_name)
            local_abs_path = task_root / relative_dir / safe_name
            if self._strm_path_has_oversized_component(local_abs_path):
                if self._logger:
                    self._logger.warning(
                        f"STRM元数据跳过(路径分量超过{_STRM_MAX_COMPONENT_BYTES}字节): {remote_path or file_name}"
                    )
                continue
            local_key = str(PurePosixPath(local_abs_path.relative_to(task_root)))
            if local_key in seen_paths:
                continue
            seen_paths.add(local_key)
            if local_abs_path.exists() and local_abs_path.stat().st_size > 0:
                continue
            try:
                expected_size = int(_size or 0)
            except (TypeError, ValueError):
                expected_size = 0
            group = items_by_file_id.setdefault(
                file_id,
                {"expected_size": expected_size, "targets": [], "remote_path": remote_path or file_name},
            )
            if expected_size > 0 and int(group.get("expected_size") or 0) <= 0:
                group["expected_size"] = expected_size
            group["targets"].append((local_abs_path, safe_name))

        if not items_by_file_id:
            if self._logger:
                self._logger.debug(
                    f"STRM元数据同步跳过: 候选={len(metadata_items)} 全部已存在"
                )
            return 0

        created_count = 0
        failed_count = 0
        cdn_concurrency = max(1, min(int(self._METADATA_CDN_CONCURRENCY), 8))
        timeout = aiohttp.ClientTimeout(total=300, connect=30, sock_read=120)
        download_queue: asyncio.Queue = asyncio.Queue(maxsize=cdn_concurrency * 2)

        connector = aiohttp.TCPConnector(
            limit=cdn_concurrency * 2,
            limit_per_host=cdn_concurrency,
            force_close=True,
            enable_cleanup_closed=True,
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            cookie_jar=aiohttp.DummyCookieJar(),
            connector=connector,
        ) as session:
            class _TransientMetadataDownloadError(Exception):
                pass

            class _IntegrityMetadataError(Exception):
                """下载内容完整性不达标（长度对不上）。这类错误重试同一条直链通常无效，
                应由上层重新 resolve 一条新直链再补试。"""
                pass

            async def fetch_metadata_content(
                file_id: str,
                download_url: str,
                headers: dict,
                expected_size: int = 0,
            ) -> bytes:
                """下载单个元数据文件。

                网络类瞬时错误（CDN 断开、超时、5xx）重试同一直链通常即可恢复；
                完整性错误（长度不一致）则立即抛出，交由上层重新 resolve 新直链。
                """
                last_error: Optional[Exception] = None
                transient_errors = (
                    aiohttp.ServerDisconnectedError,
                    aiohttp.ClientPayloadError,
                    aiohttp.ClientOSError,
                    asyncio.TimeoutError,
                    _TransientMetadataDownloadError,
                )
                base_headers = dict(headers or {})
                base_headers.setdefault("Accept", "*/*")
                base_headers.setdefault(
                    "User-Agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                base_headers["Accept-Encoding"] = "identity"
                base_headers["Connection"] = "close"
                base_headers.pop("Cache-Control", None)
                base_headers.pop("Range", None)
                expected_size = max(int(expected_size or 0), 0)

                for attempt in range(3):
                    try:
                        async with session.get(download_url, headers=base_headers) as response:
                            if response.status in {500, 502, 503, 504}:
                                body = await response.text(errors="ignore")
                                raise _TransientMetadataDownloadError(
                                    f"HTTP {response.status}: {body[:200]}"
                                )
                            if response.status >= 400:
                                body = await response.text(errors="ignore")
                                raise Exception(f"HTTP {response.status}: {body[:200]}")

                            chunks = bytearray()
                            async for chunk in response.content.iter_chunked(65536):
                                if chunk:
                                    chunks.extend(chunk)

                            expected_length = (response.headers.get("Content-Length") or "").strip()
                            if expected_length.isdigit() and len(chunks) != int(expected_length):
                                raise _IntegrityMetadataError(
                                    f"Content-Length不一致: expected={expected_length}, got={len(chunks)}"
                                )
                            if expected_size > 0 and len(chunks) != expected_size:
                                raise _IntegrityMetadataError(
                                    f"文件大小不一致: expected={expected_size}, got={len(chunks)}"
                                )
                            return bytes(chunks)
                    except _IntegrityMetadataError:
                        # 完整性错误：同一直链重试无意义，立即抛出由上层重新 resolve
                        raise
                    except transient_errors as err:
                        last_error = err
                        if attempt >= 2:
                            break
                        await asyncio.sleep(0.5 * (attempt + 1))

                raise last_error or Exception("元数据下载失败")

            async def fetch_metadata_resilient(
                file_id: str,
                download_url: str,
                headers: dict,
                expected_size: int = 0,
            ) -> bytes:
                """带“重新 resolve 直链”的下载：先用已有直链下载；遇到完整性/网络错误时，
                重新 resolve 一条新直链并重建 headers 再补试，最多重新 resolve 2 次。
                重新 resolve 的节流仍由驱动层 wait_for_request_interval 统一处理。"""
                url, hdrs, size = download_url, headers, expected_size
                last_error: Optional[Exception] = None
                for resolve_round in range(3):  # 1 次原直链 + 最多 2 次重新 resolve
                    try:
                        return await fetch_metadata_content(file_id, url, hdrs, size)
                    except Exception as err:
                        last_error = err
                        if resolve_round >= 2:
                            break
                        try:
                            # force_refresh 跳过 1s 兜底缓存，确保拿到的是新直链而非刚才那条坏链
                            refreshed = await resolve_download(driver, file_id, "", force_refresh=True)
                            if not refreshed.download_url:
                                raise Exception("无下载地址")
                            url = refreshed.download_url
                            # 只在原本不知道大小时才补；已有扫描列表大小则保留，
                            # 避免被补救直链返回的错误大小拉低校验基准而误收不完整文件
                            refreshed_size = int(getattr(refreshed, "file_size", 0) or 0)
                            if size <= 0 and refreshed_size > 0:
                                size = refreshed_size
                            hdrs = await build_upstream_download_headers(
                                driver, file_id, "", prefer_identity=True
                            )
                        except Exception:
                            break  # 重新 resolve 失败就不再补试，沿用最初的下载错误
                raise last_error or Exception("元数据下载失败")

            async def resolver():
                """串行生产者：resolve_download 的节流由驱动层 wait_for_request_interval 统一处理。"""
                nonlocal failed_count
                try:
                    for file_id, group in items_by_file_id.items():
                        targets = group.get("targets") or []
                        expected_size = int(group.get("expected_size") or 0)
                        remote_path = group.get("remote_path") or file_id
                        try:
                            download = await resolve_download(driver, file_id, "")
                            if not download.download_url:
                                raise Exception("无下载地址")
                            if expected_size <= 0 and int(download.file_size or 0) > 0:
                                expected_size = int(download.file_size or 0)
                            headers = await build_upstream_download_headers(
                                driver,
                                file_id,
                                "",
                                prefer_identity=True,
                            )
                        except Exception as err:
                            failed_count += len(targets)
                            if self._logger:
                                self._logger.warning(
                                    f"STRM元数据获取直链失败: {remote_path} (file_id={file_id}) - {err}"
                                )
                            continue
                        await download_queue.put((file_id, targets, download.download_url, headers, expected_size, remote_path))
                finally:
                    # 哨兵通知所有消费者退出
                    for _ in range(cdn_concurrency):
                        await download_queue.put(None)

            async def downloader():
                """并发消费者：拿到直链就 HTTP GET CDN 写盘，CDN 侧不限速。"""
                nonlocal created_count, failed_count
                while True:
                    msg = await download_queue.get()
                    if msg is None:
                        return
                    file_id, targets, download_url, headers, expected_size, remote_path = msg
                    primary_path, primary_name = targets[0]
                    tmp_path = primary_path.with_name(primary_path.name + ".tmp")
                    try:
                        content = await fetch_metadata_resilient(file_id, download_url, headers, expected_size)

                        primary_path.parent.mkdir(parents=True, exist_ok=True)
                        tmp_path.write_bytes(content)
                        tmp_path.replace(primary_path)
                        created_count += 1

                        # 同 file_id 的其它 target 路径，复用已下载的 content
                        for extra_path, extra_name in targets[1:]:
                            try:
                                extra_path.parent.mkdir(parents=True, exist_ok=True)
                                extra_tmp = extra_path.with_name(extra_path.name + ".tmp")
                                extra_tmp.write_bytes(content)
                                extra_tmp.replace(extra_path)
                                created_count += 1
                            except (OSError, ValueError) as extra_err:
                                failed_count += 1
                                self._log_strm_path_error(
                                    extra_err,
                                    action="metadata_write",
                                    file_id=file_id,
                                    file_name=extra_name,
                                    remote_path=remote_path,
                                    local_path=extra_path,
                                )
                    except (OSError, ValueError) as err:
                        failed_count += len(targets)
                        try:
                            if tmp_path.exists():
                                tmp_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        self._log_strm_path_error(
                            err,
                            action="metadata_write",
                            file_id=file_id,
                            file_name=primary_name,
                            remote_path=remote_path,
                            local_path=primary_path,
                        )
                    except Exception as err:
                        failed_count += len(targets)
                        try:
                            if tmp_path.exists():
                                tmp_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        if self._logger:
                            self._logger.warning(
                                f"STRM元数据下载失败: {remote_path} (file_id={file_id}) - {err}"
                            )

            await asyncio.gather(
                resolver(),
                *[downloader() for _ in range(cdn_concurrency)],
            )

        if self._logger:
            message = (
                f"STRM元数据同步完成: 候选={len(metadata_items)} 实下载={len(items_by_file_id)} "
                f"新增={created_count} 失败={failed_count}"
            )
            if failed_count:
                self._logger.warning(message)
            else:
                self._logger.debug(message)
        return created_count

    async def _auto_pause_task(
        self,
        task: StrmSyncTask,
        *,
        reason: str,
        message: Optional[str],
    ):
        """自动暂停并落库。reason: account_disabled / auth_failure / user。"""
        task.status = "paused"
        task.paused_reason = reason
        task.next_run_time = None
        task.last_scan = datetime.now()
        task.last_scan_status = "error"
        task.error_message = message
        try:
            await db.update_strm_sync_task(
                task.id,
                status="paused",
                paused_reason=reason,
                last_scan=task.last_scan.isoformat(),
                last_scan_status="error",
                error_message=message,
            )
        except Exception as db_err:
            if self._logger:
                self._logger.error(
                    f"写入 STRM 任务自动暂停状态失败: task={task.id} reason={reason} err={db_err}"
                )

    _AUTH_ERROR_KEYWORDS = (
        "认证", "token", "401", "403", "cookie",
        "登录", "permission", "unauthorized",
    )

    def _looks_like_auth_error(self, message: str) -> bool:
        if not message:
            return False
        lowered = message.lower()
        return any(kw in lowered for kw in self._AUTH_ERROR_KEYWORDS)

    async def _run_task(self, task_id: int, run_mode: str = "auto"):
        started_at = datetime.now()
        delay_token = None
        try:
            task = self._tasks.get(task_id)
            if not task:
                return

            # 账号不存在 / 已禁用 / 认证失效：本次直接自动暂停，不要继续跑打爆 API
            account = await db.get_account(task.account_id)
            if not account:
                await self._auto_pause_task(
                    task, reason="account_disabled", message="关联的账号已删除"
                )
                return
            if not account.get("is_active", True):
                await self._auto_pause_task(
                    task, reason="account_disabled", message="关联的账号已禁用"
                )
                return
            account_config = account.get("config", {}) or {}
            if isinstance(account_config, str):
                try:
                    import json as _json
                    account_config = _json.loads(account_config)
                except Exception:
                    account_config = {}
            if account_config.get("auth_status") == "failed":
                await self._auto_pause_task(
                    task,
                    reason="auth_failure",
                    message="关联的账号认证已失效，请重新配置账号认证信息",
                )
                return

            # 初始化进度字段
            task.scanned_dirs = 0
            task.scanned_files = 0
            task.started_at = started_at

            scan_interval, concurrency, task_concurrency_limit = await self._get_runtime_settings()
            task.scan_interval = scan_interval
            task.concurrency = concurrency
            self._task_concurrency_limit = task_concurrency_limit
            base_url = await self._get_strm_base_url()
            link_format = await self._get_strm_link_format()
            if not base_url:
                duration_ms = max(int((datetime.now() - started_at).total_seconds() * 1000), 0)
                await db.update_strm_sync_task(
                    task_id,
                    last_created_count=0,
                    last_updated_count=0,
                    last_deleted_count=0,
                    last_duration_ms=duration_ms,
                    last_scan=datetime.now().isoformat(),
                    last_scan_status="error",
                    error_message="STRM播放地址基址未设置",
                )
                task.last_created_count = 0
                task.last_updated_count = 0
                task.last_deleted_count = 0
                task.last_duration_ms = duration_ms
                task.last_scan = datetime.now()
                task.last_scan_status = "error"
                task.error_message = "STRM播放地址基址未设置"
                task.next_run_time = self._compute_next_run(task, scan_interval)
                return

            token = await self._get_strm_token()
            default_extensions_text = await self._get_str_setting(
                "strm_default_extensions",
                DEFAULT_MEDIA_EXTENSIONS,
            )
            extensions = self._parse_extensions(default_extensions_text)
            exclude_dir_rules = self._parse_keyword_rules(task.exclude_dir_keywords)
            exclude_file_rules = self._parse_keyword_rules(task.exclude_file_keywords)
            signature_enabled = await self._get_bool_setting("strm_signature_enabled", False)
            min_media_size_mb = await self._get_int_setting("strm_min_file_size_mb", 0, 0, 10240)
            min_media_size_bytes = min_media_size_mb * 1024 * 1024
            metadata_extensions_text = await self._get_str_setting(
                "strm_metadata_extensions",
                DEFAULT_METADATA_EXTENSIONS,
            )
            metadata_extensions = self._parse_optional_extensions(metadata_extensions_text)
            metadata_max_size_mb = await self._get_int_setting("strm_metadata_max_size_mb", 10, 1, 1024)
            metadata_max_size_bytes = metadata_max_size_mb * 1024 * 1024
            metadata_parent_enabled = await self._get_bool_setting("strm_metadata_parent_enabled", True)
            conflict_policy = self._normalize_conflict_policy(
                await self._get_str_setting("strm_conflict_policy", "size_desc")
            )

            driver = await get_account_driver(task.account_id)
            if not driver:
                duration_ms = max(int((datetime.now() - started_at).total_seconds() * 1000), 0)
                await db.update_strm_sync_task(
                    task_id,
                    last_created_count=0,
                    last_updated_count=0,
                    last_deleted_count=0,
                    last_duration_ms=duration_ms,
                    last_scan=datetime.now().isoformat(),
                    last_scan_status="error",
                    error_message="驱动实例不可用",
                )
                task.last_created_count = 0
                task.last_updated_count = 0
                task.last_deleted_count = 0
                task.last_duration_ms = duration_ms
                task.last_scan = datetime.now()
                task.last_scan_status = "error"
                task.error_message = "驱动实例不可用"
                task.next_run_time = self._compute_next_run(task, scan_interval)
                return

            delay_token = _extra_api_delay.set(task.api_interval)

            self._strm_root.mkdir(parents=True, exist_ok=True)
            task_folder = self._sanitize_task_folder(task.name)
            task_root = self._get_task_root(task.name)
            task_root.mkdir(parents=True, exist_ok=True)
            deleted_count = 0
            use_branch_check = run_mode == "branch" or (run_mode == "auto" and task.branch_check_enabled)
            branches: List[Dict[str, object]] = []
            if use_branch_check:
                try:
                    await db.delete_expired_strm_sync_branches(task.id)
                except Exception:
                    pass
                branches = await db.get_strm_sync_branches(task.id, only_active=True)
                if not branches:
                    if self._logger:
                        self._logger.info(f"STRM分支检查跳过全量扫描: {task.name} 未配置有效分支")

            # full_sync 不再开头删光重建：改由扫描后的差异清理处理（最终文件集一致）。
            # 这样某个子目录列举失败被跳过时，不会因为先删了再重建不回来而丢失其 strm，
            # 也避免扫描过程中 Emby 恰好扫到一片空目录。
            skipped_dirs: Set[PurePosixPath] = set()

            collected: List[Tuple[str, str, str, int, Optional[datetime], PurePosixPath]] = []
            metadata_collected: List[Tuple[str, str, int, Optional[datetime], PurePosixPath, str]] = []
            base_posix_path = "/" + task.path.strip("/")
            base_posix_path = "/" if base_posix_path == "/" else base_posix_path.rstrip("/")

            cleanup_scopes: List[Tuple[PurePosixPath, bool]] = []
            base_remote_child_names: Dict[PurePosixPath, Set[str]] = {}
            if use_branch_check:
                existing_parent_ids = {str(branch.get("parent_id") or "") for branch in branches}
                scan_branches = list(branches)
                for branch in list(branches):
                    if str(branch.get("branch_type") or "temporary") != "base":
                        continue
                    relative_text = str(branch.get("relative_path") or "").strip("/")
                    branch_relative = PurePosixPath(relative_text) if relative_text else PurePosixPath()
                    branch_path = str(branch.get("path") or "").strip("/")
                    branch_base_posix_path = "/" + branch_path if branch_path else base_posix_path
                    branch_base_posix_path = "/" if branch_base_posix_path == "/" else branch_base_posix_path.rstrip("/")
                    discovered, remote_child_names = await self._discover_missing_temporary_branches(
                        driver,
                        task,
                        task_root,
                        branch,
                        existing_parent_ids,
                        extensions,
                        metadata_extensions,
                        metadata_max_size_bytes,
                        min_media_size_bytes,
                        metadata_parent_enabled,
                        exclude_dir_rules,
                        exclude_file_rules,
                        branch_base_posix_path,
                        collected,
                        metadata_collected if task.sync_metadata and metadata_extensions else None,
                    )
                    if remote_child_names is not None:
                        base_remote_child_names[branch_relative] = remote_child_names
                    scan_branches.extend(discovered)

                filtered_branches: List[Dict[str, object]] = []
                for branch in scan_branches:
                    branch_type = str(branch.get("branch_type") or "temporary")
                    if branch_type != "base":
                        relative_text = str(branch.get("relative_path") or "").strip("/")
                        branch_relative = PurePosixPath(relative_text) if relative_text else PurePosixPath()
                        missing_under_base = False
                        for base_relative, remote_child_names in base_remote_child_names.items():
                            child_name = self._first_child_name_under_base(branch_relative, base_relative)
                            if child_name is not None and child_name not in remote_child_names:
                                missing_under_base = True
                                branch_id = branch.get("id")
                                if branch_id:
                                    try:
                                        await db.delete_strm_sync_branch(int(branch_id))
                                    except Exception:
                                        pass
                                if self._logger:
                                    self._logger.info(f"STRM移除远端已删除目录的临时分支: {branch.get('path')}")
                                break
                        if missing_under_base:
                            continue
                    filtered_branches.append(branch)
                branches = filtered_branches

                for branch in branches:
                    relative_text = str(branch.get("relative_path") or "").strip("/")
                    branch_relative = PurePosixPath(relative_text) if relative_text else PurePosixPath()
                    branch_type = str(branch.get("branch_type") or "temporary")
                    branch_recursive = bool(branch.get("recursive"))
                    if branch_type == "base":
                        branch_recursive = False
                    cleanup_scopes.append((branch_relative, branch_recursive))
                    if branch_type == "base":
                        branch_id = branch.get("id")
                        if branch_id:
                            try:
                                await db.update_strm_sync_branch(
                                    int(branch_id),
                                    last_scan=datetime.now().isoformat(),
                                    last_scan_status="success",
                                    error_message=None,
                                )
                            except Exception:
                                pass
                        continue
                    branch_path = str(branch.get("path") or "").strip("/")
                    branch_base_posix_path = "/" + branch_path if branch_path else base_posix_path
                    branch_base_posix_path = "/" if branch_base_posix_path == "/" else branch_base_posix_path.rstrip("/")
                    await self._collect_files(
                        driver=driver,
                        parent_id=str(branch.get("parent_id") or ""),
                        base_posix_path=branch_base_posix_path,
                        recursive=branch_recursive,
                        extensions=extensions,
                        metadata_extensions=metadata_extensions,
                        metadata_max_size_bytes=metadata_max_size_bytes,
                        min_media_size_bytes=min_media_size_bytes,
                        metadata_parent_enabled=metadata_parent_enabled,
                        exclude_dir_rules=exclude_dir_rules,
                        exclude_file_rules=exclude_file_rules,
                        relative_parts=branch_relative,
                        result=collected,
                        metadata_result=metadata_collected if task.sync_metadata and metadata_extensions else None,
                        task=task,
                        is_root=True,
                        skipped_dirs=skipped_dirs,
                    )
                    branch_id = branch.get("id")
                    if branch_id:
                        try:
                            await db.update_strm_sync_branch(
                                int(branch_id),
                                last_scan=datetime.now().isoformat(),
                                last_scan_status="success",
                                error_message=None,
                            )
                        except Exception:
                            pass
            else:
                await self._collect_files(
                    driver=driver,
                    parent_id=task.parent_id,
                    base_posix_path=base_posix_path,
                    recursive=task.recursive,
                    extensions=extensions,
                    metadata_extensions=metadata_extensions,
                    metadata_max_size_bytes=metadata_max_size_bytes,
                    min_media_size_bytes=min_media_size_bytes,
                    metadata_parent_enabled=metadata_parent_enabled,
                    exclude_dir_rules=exclude_dir_rules,
                    exclude_file_rules=exclude_file_rules,
                    relative_parts=PurePosixPath(),
                    result=collected,
                    metadata_result=metadata_collected if task.sync_metadata and metadata_extensions else None,
                    task=task,
                    is_root=True,
                    skipped_dirs=skipped_dirs,
                )

            collected, conflict_skipped_count = self._select_conflict_winners(collected, conflict_policy)

            semaphore = asyncio.Semaphore(max(1, min(int(concurrency), 20)))
            created_count = 0
            updated_count = 0
            desired_local_rel_paths: Set[str] = set()

            async def handle_one(item: Tuple[str, str, str, int, Optional[datetime], PurePosixPath]):
                nonlocal created_count, updated_count
                file_id, file_name, remote_path, size, modified, relative_dir = item

                local_rel_path = self._build_local_rel_path(task_folder, relative_dir, file_name)
                local_rel_path_text = str(PurePosixPath(local_rel_path))
                local_abs_path = task_root / PurePosixPath(local_rel_path).relative_to(task_folder)
                if self._strm_path_has_oversized_component(local_abs_path):
                    if self._logger:
                        self._logger.warning(
                            f"STRM跳过(路径分量超过{_STRM_MAX_COMPONENT_BYTES}字节): {file_name}"
                        )
                    return
                desired_local_rel_paths.add(local_rel_path_text)
                try:
                    local_abs_path.parent.mkdir(parents=True, exist_ok=True)
                except (OSError, ValueError) as err:
                    self._log_strm_path_error(
                        err,
                        action="mkdir",
                        file_id=file_id,
                        file_name=file_name,
                        relative_dir=relative_dir,
                        remote_path=remote_path,
                        local_path=local_abs_path,
                    )
                    return
                local_exists = local_abs_path.exists()
                migrated_legacy = False
                if not local_exists:
                    legacy_rel_path = self._build_legacy_local_rel_path(task_folder, relative_dir, file_name)
                    if legacy_rel_path and legacy_rel_path != local_rel_path:
                        legacy_abs_path = task_root / PurePosixPath(legacy_rel_path).relative_to(task_folder)
                        if legacy_abs_path.exists():
                            try:
                                legacy_abs_path.replace(local_abs_path)
                                local_exists = True
                                migrated_legacy = True
                            except OSError as err:
                                if self._logger:
                                    self._logger.warning(f"STRM旧格式迁移失败: {legacy_abs_path.name} - {err}")

                if task.scan_mode == "incremental_missing":
                    if local_exists and not migrated_legacy:
                        return
                url = self._build_play_url(base_url, task.account_id, file_id, token, signature_enabled, link_format)
                if local_exists:
                    try:
                        if local_abs_path.read_text(encoding="utf-8").strip() == url:
                            return
                    except Exception:
                        pass
                    pending_update = True
                else:
                    pending_update = False
                try:
                    local_abs_path.write_text(url + "\n", encoding="utf-8")
                    if pending_update:
                        updated_count += 1
                    else:
                        created_count += 1
                except (OSError, ValueError) as err:
                    desired_local_rel_paths.discard(local_rel_path_text)
                    self._log_strm_path_error(
                        err,
                        action="write",
                        file_id=file_id,
                        file_name=file_name,
                        relative_dir=relative_dir,
                        remote_path=remote_path,
                        local_path=local_abs_path,
                    )

            async def guarded(item):
                async with semaphore:
                    await handle_one(item)

            await asyncio.gather(*[guarded(item) for item in collected])

            metadata_created_count = 0
            if task.sync_metadata and self._logger:
                self._logger.debug(
                    f"STRM元数据扫描完成: 候选={len(metadata_collected)} 扩展={';'.join(sorted(metadata_extensions)) or '-'}"
                )
            if task.sync_metadata and metadata_collected:
                metadata_created_count = await self._sync_metadata_files(
                    driver,
                    task_root,
                    metadata_collected,
                    concurrency,
                )

            if task.scan_mode in {"incremental_update", "full_sync"}:
                cleanup_roots = []
                if use_branch_check:
                    cleanup_roots = [(task_root / scope, recursive) for scope, recursive in cleanup_scopes]
                else:
                    cleanup_roots = [(task_root, True)]
                for cleanup_root, recursive_cleanup in cleanup_roots:
                    if not cleanup_root.exists():
                        continue
                    file_iter = cleanup_root.rglob("*.strm") if recursive_cleanup else cleanup_root.glob("*.strm")
                    for file_path in file_iter:
                        rel = str(PurePosixPath(file_path.relative_to(self._strm_root)))
                        if rel not in desired_local_rel_paths:
                            # 子目录这次没列举成功（被跳过），保留其已存在 strm，不当成“已删除”清掉
                            if self._is_strm_under_skipped(rel, task_folder, skipped_dirs):
                                continue
                            try:
                                file_path.unlink(missing_ok=True)
                                deleted_count += 1
                            except Exception:
                                pass
                    if recursive_cleanup:
                        for directory in sorted(cleanup_root.rglob("*"), reverse=True):
                            if directory.is_dir():
                                try:
                                    directory.rmdir()
                                except OSError:
                                    pass
                if use_branch_check:
                    for base_relative, remote_child_names in base_remote_child_names.items():
                        deleted_count += self._cleanup_missing_base_child_dirs(
                            task_root,
                            base_relative,
                            remote_child_names,
                        )

            task.file_count = len(collected)
            task.last_created_count = created_count
            task.last_updated_count = updated_count
            task.last_deleted_count = deleted_count
            task.last_duration_ms = max(int((datetime.now() - started_at).total_seconds() * 1000), 0)
            task.last_scan = datetime.now()
            task.last_scan_status = "success"
            task.error_message = None
            task.next_run_time = self._compute_next_run(task, scan_interval)

            await db.update_strm_sync_task(
                task_id,
                file_count=task.file_count,
                last_created_count=task.last_created_count,
                last_updated_count=task.last_updated_count,
                last_deleted_count=task.last_deleted_count,
                last_duration_ms=task.last_duration_ms,
                last_scan=task.last_scan.isoformat(),
                last_scan_status=task.last_scan_status,
                error_message=None,
            )

            self._logger.debug(
                f"STRM任务完成: {task.name} mode={'branch' if use_branch_check else 'full'} account={task.account_id} path={task.path} files={task.file_count} created={created_count} updated={updated_count} deleted={deleted_count} skipped_conflict={conflict_skipped_count} metadata={metadata_created_count} duration_ms={task.last_duration_ms}"
            )

        except asyncio.CancelledError:
            pass

        except Exception as e:
            failed_task = self._tasks.get(task_id)
            if self._is_embedded_null_error(e):
                self._logger.error(
                    f"STRM任务执行失败(路径含隐藏空字符): {task_id} {e} | "
                    f"task={getattr(failed_task, 'name', '-')} "
                    f"account={getattr(failed_task, 'account_id', '-')} "
                    f"path={getattr(failed_task, 'path', '-')}"
                )
            else:
                self._logger.error(f"STRM任务执行失败: {task_id} {e}")
            error_msg = str(e)
            duration_ms_err = max(int((datetime.now() - started_at).total_seconds() * 1000), 0)
            task = failed_task
            auth_failure = self._looks_like_auth_error(error_msg)

            if auth_failure and task is not None:
                # 认证类错误：走自动暂停，等账号在 admin 那边被修好后由 resume_tasks_by_account 恢复
                task.last_created_count = 0
                task.last_updated_count = 0
                task.last_deleted_count = 0
                task.last_duration_ms = duration_ms_err
                await self._auto_pause_task(
                    task,
                    reason="auth_failure",
                    message=f"认证错误，请检查账号配置: {error_msg[:200]}",
                )
                try:
                    await db.update_strm_sync_task(
                        task_id,
                        last_created_count=0,
                        last_updated_count=0,
                        last_deleted_count=0,
                        last_duration_ms=duration_ms_err,
                    )
                except Exception:
                    pass
            else:
                try:
                    await db.update_strm_sync_task(
                        task_id,
                        last_created_count=0,
                        last_updated_count=0,
                        last_deleted_count=0,
                        last_duration_ms=duration_ms_err,
                        last_scan=datetime.now().isoformat(),
                        last_scan_status="error",
                        error_message=error_msg,
                    )
                except Exception:
                    pass
                if task:
                    task.last_created_count = 0
                    task.last_updated_count = 0
                    task.last_deleted_count = 0
                    task.last_duration_ms = duration_ms_err
                    task.last_scan = datetime.now()
                    task.last_scan_status = "error"
                    task.error_message = error_msg
                    scan_interval, concurrency, task_concurrency_limit = await self._get_runtime_settings()
                    task.scan_interval = scan_interval
                    task.concurrency = concurrency
                    self._task_concurrency_limit = task_concurrency_limit
                    task.next_run_time = self._compute_next_run(task, scan_interval)
        finally:
            if delay_token is not None:
                _extra_api_delay.reset(delay_token)
            self._running_tasks.discard(task_id)
            if task_id in self._running_task_futures:
                del self._running_task_futures[task_id]
            task = self._tasks.get(task_id)
            if task:
                self._running_account_ids.discard(task.account_id)

    def _parse_strm_play_url(self, value: str) -> Optional[Dict[str, Any]]:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parts = urllib.parse.urlsplit(text)
        except Exception:
            return None
        path = parts.path or ""

        v2_match = re.match(r"^/api/strm/v2/play/(\d+)/([^/]+)/t/([^/]+)(?:/s/([^/]+))?/?$", path)
        if v2_match:
            try:
                file_id = decode_strm_file_key(v2_match.group(2))
            except Exception:
                return None
            return {
                "format": "v2",
                "parts": parts,
                "account_id": int(v2_match.group(1)),
                "file_id": file_id,
                "token": urllib.parse.unquote(v2_match.group(3) or ""),
                "signature": v2_match.group(4) or "",
            }

        v1_match = re.match(r"^/api/strm/play/(\d+)/(.*)$", path)
        if v1_match:
            pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
            token = ""
            signature = ""
            for key, item_value in pairs:
                if key == "token":
                    token = item_value
                elif key == "sign":
                    signature = item_value
            return {
                "format": "v1",
                "parts": parts,
                "account_id": int(v1_match.group(1)),
                "file_id": urllib.parse.unquote(v1_match.group(2) or ""),
                "token": token,
                "signature": signature,
                "query_pairs": pairs,
            }
        return None

    def _replace_url_path(self, parts: urllib.parse.SplitResult, new_path: str, query: str = "") -> str:
        return urllib.parse.urlunsplit((
            parts.scheme,
            parts.netloc,
            new_path,
            query,
            parts.fragment,
        ))

    def _replace_v2_token_in_url(self, parsed: Dict[str, Any], new_token: str) -> str:
        parts = parsed["parts"]
        signature_enabled = bool(parsed.get("signature"))
        new_path = build_strm_v2_play_path(
            int(parsed["account_id"]),
            str(parsed["file_id"]),
            new_token,
            signature_enabled,
        )
        return self._replace_url_path(parts, new_path, parts.query)

    def _build_full_play_url(
        self,
        base_url: str,
        account_id: int,
        file_id: str,
        token: str,
        signature_enabled: bool,
        link_format: str,
    ) -> str:
        return self._build_play_url(
            base_url.rstrip("/"),
            account_id,
            file_id,
            token,
            signature_enabled,
            link_format,
        )

    async def replace_strm_domain(self, new_base_url: str) -> Dict[str, int]:
        base = (new_base_url or "").strip().rstrip("/")
        if not base:
            raise ValueError("new_base_url required")
        self._strm_root.mkdir(parents=True, exist_ok=True)

        total = 0
        updated = 0
        for file_path in self._strm_root.rglob("*.strm"):
            total += 1
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                if not lines:
                    continue
                first = lines[0].strip()
                if not first:
                    continue
                replaced = re.sub(r"^https?://[^/]+", base, first)
                if replaced != first:
                    lines[0] = replaced
                    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    updated += 1
            except Exception:
                continue

        await config_manager.set_async("strm_base_url", base)
        return {"total": total, "updated": updated}

    async def replace_strm_token(self, old_token: str, new_token: str) -> Dict[str, int]:
        old_value = str(old_token or "").strip()
        new_value = str(new_token or "").strip()
        if not new_value:
            raise ValueError("new_token required")
        self._strm_root.mkdir(parents=True, exist_ok=True)

        total = 0
        matched = 0
        updated = 0
        for file_path in self._strm_root.rglob("*.strm"):
            total += 1
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                if not lines:
                    continue
                first = lines[0].strip()
                if not first:
                    continue

                parsed = self._parse_strm_play_url(first)
                if not parsed:
                    continue

                changed = False
                # old_value 为空表示"未知旧 token"，此时匹配任意现有 token（含缺失），用于首次设置 token
                def _token_matches(current: str) -> bool:
                    return (not old_value) or (current == old_value)

                if parsed["format"] == "v2":
                    if _token_matches(parsed.get("token") or ""):
                        matched += 1
                        replaced = self._replace_v2_token_in_url(parsed, new_value)
                        changed = replaced != first
                else:
                    parts = parsed["parts"]
                    pairs = parsed.get("query_pairs") or []
                    has_token_param = any(key == "token" for key, _ in pairs)
                    if _token_matches(parsed.get("token") or ""):
                        matched += 1
                        next_pairs = []
                        for key, value in pairs:
                            if key == "token" and value != new_value:
                                value = new_value
                                changed = True
                            next_pairs.append((key, value))
                        # 旧链接没有 token 参数时补上（首次设置 token 的场景）
                        if not has_token_param:
                            next_pairs.append(("token", new_value))
                            changed = True
                        if changed:
                            replaced = urllib.parse.urlunsplit((
                                parts.scheme,
                                parts.netloc,
                                parts.path,
                                urllib.parse.urlencode(next_pairs),
                                parts.fragment,
                            ))

                if changed:
                    lines[0] = replaced
                    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    updated += 1
            except Exception:
                continue

        return {"total": total, "matched": matched, "updated": updated}

    async def replace_strm_link_format(self, link_format: str) -> Dict[str, int]:
        target_format = str(link_format or "v1").strip().lower()
        if target_format not in STRM_LINK_FORMATS:
            raise ValueError("unsupported strm link format")
        default_base_url = await self._get_strm_base_url()
        default_token = await self._get_strm_token()
        self._strm_root.mkdir(parents=True, exist_ok=True)

        total = 0
        matched = 0
        updated = 0
        for file_path in self._strm_root.rglob("*.strm"):
            total += 1
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                if not lines:
                    continue
                first = lines[0].strip()
                parsed = self._parse_strm_play_url(first)
                if not parsed:
                    continue
                matched += 1
                parts = parsed["parts"]
                base_url = (
                    f"{parts.scheme}://{parts.netloc}".rstrip("/")
                    if parts.scheme and parts.netloc
                    else default_base_url
                )
                token = str(parsed.get("token") or "").strip() or default_token
                signature_enabled = bool(str(parsed.get("signature") or "").strip())
                replaced = self._build_full_play_url(
                    base_url,
                    int(parsed["account_id"]),
                    str(parsed["file_id"]),
                    token,
                    signature_enabled,
                    target_format,
                )
                if replaced != first:
                    lines[0] = replaced
                    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    updated += 1
            except Exception:
                continue

        return {"total": total, "matched": matched, "updated": updated}

    async def delete_task_output(self, task_name: str) -> bool:
        task_root = self._get_task_root(task_name)
        if not task_root.exists():
            return False
        shutil.rmtree(task_root, ignore_errors=False)
        return True

    async def pause_tasks_by_account(
        self,
        account_id: int,
        reason: str,
        message: Optional[str] = None,
    ) -> int:
        """账号禁用/认证失效时批量暂停该账号的 STRM 任务，只对 running 生效。"""
        if reason not in ("account_disabled", "auth_failure"):
            if self._logger:
                self._logger.warning(
                    f"STRM pause_tasks_by_account 收到未知 reason: {reason}"
                )
            return 0

        paused = 0
        target_tasks = [
            task for task in list(self._tasks.values())
            if task.account_id == account_id and task.status == "running"
        ]

        for task in target_tasks:
            self._queued_tasks.discard(task.id)
            self._manual_triggered_tasks.discard(task.id)
            future = self._running_task_futures.get(task.id)
            if future and not future.done():
                future.cancel()

        for task in target_tasks:
            try:
                await self._auto_pause_task(task, reason=reason, message=message)
                paused += 1
            except Exception as e:
                if self._logger:
                    self._logger.error(
                        f"按账号暂停 STRM 任务失败: task={task.id} err={e}"
                    )

        if paused > 0 and self._logger:
            self._logger.info(
                f"账号 {account_id} 状态变化({reason})，已暂停 {paused} 个 STRM 同步任务"
            )
        return paused

    async def resume_tasks_by_account(self, account_id: int) -> int:
        """账号恢复可用时只恢复 account_disabled/auth_failure 的任务，不触碰用户手动暂停的。"""
        resumed = 0
        scan_interval, _, _ = await self._get_runtime_settings()
        try:
            for task in list(self._tasks.values()):
                if task.account_id != account_id:
                    continue
                if task.status != "paused":
                    continue
                if task.paused_reason not in ("account_disabled", "auth_failure"):
                    continue

                task.status = "running"
                task.paused_reason = None
                task.error_message = None
                # 同步清掉遗留的错误标记，避免前端错误图标残留
                task.last_scan_status = None
                task.next_run_time = datetime.now()
                await db.update_strm_sync_task(
                    task.id,
                    status="running",
                    paused_reason=None,
                    last_scan_status=None,
                    error_message=None,
                )
                resumed += 1

            if resumed > 0 and self._logger:
                self._logger.info(
                    f"账号 {account_id} 恢复可用，已自动恢复 {resumed} 个 STRM 同步任务"
                )
        except Exception as e:
            if self._logger:
                self._logger.error(f"按账号恢复 STRM 任务失败: {e}")
        return resumed

    async def remove_tasks_by_account(self, account_id: int) -> int:
        target_tasks = [task for task in self._tasks.values() if task.account_id == account_id]
        removed = 0

        for task in target_tasks:
            future = self._running_task_futures.get(task.id)
            if future and not future.done():
                future.cancel()

        running_futures = [
            self._running_task_futures[task.id]
            for task in target_tasks
            if task.id in self._running_task_futures
        ]
        if running_futures:
            await asyncio.gather(*running_futures, return_exceptions=True)

        for task in target_tasks:
            self._running_tasks.discard(task.id)
            self._queued_tasks.discard(task.id)
            self._manual_triggered_tasks.discard(task.id)
            self._running_account_ids.discard(task.account_id)
            self._running_task_futures.pop(task.id, None)
            self._tasks.pop(task.id, None)
            try:
                await self.delete_task_output(task.name)
            except FileNotFoundError:
                pass
            except Exception:
                pass
            removed += 1

        if removed:
            await db.delete_strm_sync_tasks_by_account(account_id)
        return removed


strm_sync_manager = StrmSyncManager()
