"""LitePan 配置入口：定义默认值 + 数据库为准的 ConfigManager，兼容同步与异步访问。"""

import secrets
import os
import json
from typing import Any, Dict
from pathlib import Path

APP_NAME = "LitePan"
APP_VERSION = "0.3.2-Beta"

try:
    from core.log_manager import get_writer, LogModule
    _log_available = True
except ImportError:
    _log_available = False


class Settings:
    WEB_HOST: str = '0.0.0.0'
    WEB_PORT: int = 5211
    DATABASE_PATH: str = 'data/litepan.db'
    SECRET_KEY: str = ""
    LOG_LEVEL: str = "INFO"
    LOG_RETENTION_DAYS: int = 10

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    SESSION_TIMEOUT: int = 7200
    OAUTH_SERVER_URL: str = "https://oauth.litepan.top"
    PUBLIC_INDEX_ENABLED: bool = True
    INDEX_ACCOUNT_SWITCH_MODE: str = "dropdown"
    ADMIN_HOME_RETURN_MODE: str = "top_icon"
    STRM_BASE_URL: str = ""
    STRM_TOKEN: str = ""
    STRM_LINK_FORMAT: str = "v1"
    STRM_DEFAULT_SCAN_INTERVAL: int = 120
    STRM_TASK_CONCURRENCY: int = 3
    UPLOAD_TASK_CONCURRENCY: int = 3
    AUTH_ACTIVE_REFRESH_ENABLED: bool = True

    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 1800
    CACHE_PERSISTENCE_ENABLED: bool = True
    CACHE_PERSISTENCE_INTERVAL_SECONDS: int = 600
    CACHE_MAX_ITEMS: int = 10000
    CACHE_MEMORY_LIMIT_MB: int = 512

    WEBDAV_ENABLED: bool = True
    WEBDAV_SMART_CHUNK_ENABLED: bool = True
    WEBDAV_CHUNK_SIZE: int = 262144
    WEBDAV_CACHE_ENABLED: bool = True

    MAX_CONCURRENT_REQUESTS: int = 10
    REQUEST_TIMEOUT: int = 30
    THEME: str = "light"
    ITEMS_PER_PAGE: int = 50

    CACHE_RETENTION_DEFAULT_API_INTERVAL: int = 200
    CACHE_RETENTION_DEFAULT_REFRESH_INTERVAL: int = 60
    STRM_DEFAULT_API_INTERVAL: int = 200
    MO_PROXY_ENABLED: bool = False
    MO_PROXY_URL: str = ""
    MO_PROXY_USERNAME: str = ""
    MO_PROXY_PASSWORD: str = ""
    MO_TMDB_API_KEY: str = ""
    MO_TMDB_LANGUAGE: str = "zh-CN"
    MO_API_REQUEST_INTERVAL_MS: int = 300
    MO_FFPROBE_REQUEST_INTERVAL_MS: int = 3000
    MO_TMDB_REQUEST_INTERVAL_MS: int = 250
    MO_FFPROBE_CONCURRENCY: int = 2
    MO_FFPROBE_TIMEOUT_SECONDS: int = 30
    MO_MIN_CONFIDENCE_THRESHOLD: float = 0.5
    MO_FILE_EXTENSIONS: str = "mkv;mp4;avi;ts;mov;wmv;iso;m2ts;rmvb;flv;m4v;webm"
    MO_METADATA_EXTENSIONS: str = "nfo;ass;ssa;srt;sub;idx;sup;vtt;jpg;jpeg;png;webp;bmp"
    MO_MEDIA_TAG_ORDER: str = '["screen_size","video_codec","audio_codec","audio_channels"]'
    MO_ALIGN_MEDIA_TAGS: bool = False
    MO_MAX_WORKS_PER_RUN: int = 50
    MO_OVERWRITE_EXISTING: bool = False

    @classmethod
    def get_default_value(cls, key: str) -> Any:
        return getattr(cls, key.upper(), None)

    @classmethod
    def get_config_metadata(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "admin_username": {
                "type": "string",
                "description": "管理员用户名",
                "category": "security",
                "default": cls.ADMIN_USERNAME
            },
            "admin_password": {
                "type": "password",
                "description": "管理员密码",
                "category": "security",
                "sensitive": True,
                "default": cls.ADMIN_PASSWORD
            },
            "session_timeout": {
                "type": "integer",
                "description": "会话超时时间",
                "category": "security",
                "unit": "小时",
                "min": 0.5,
                "max": 24,
                "default": cls.SESSION_TIMEOUT / 3600
            },
            "oauth_server_url": {
                "type": "string",
                "description": "OAuth代理服务地址",
                "category": "system",
                "default": cls.OAUTH_SERVER_URL
            },
            "public_index_enabled": {
                "type": "boolean",
                "description": "是否允许匿名访问前台文件列表",
                "category": "system",
                "default": cls.PUBLIC_INDEX_ENABLED
            },
            "index_account_switch_mode": {
                "type": "string",
                "description": "首页账号切换方式",
                "category": "system",
                "default": cls.INDEX_ACCOUNT_SWITCH_MODE
            },
            "admin_home_return_mode": {
                "type": "string",
                "description": "后台返回首页入口方式",
                "category": "system",
                "default": cls.ADMIN_HOME_RETURN_MODE
            },
            "strm_base_url": {
                "type": "string",
                "description": "STRM播放地址基址",
                "category": "system",
                "default": cls.STRM_BASE_URL
            },
            "strm_token": {
                "type": "password",
                "description": "STRM访问令牌",
                "category": "system",
                "sensitive": True,
                "default": cls.STRM_TOKEN
            },
            "strm_link_format": {
                "type": "string",
                "description": "STRM链接格式",
                "category": "system",
                "default": cls.STRM_LINK_FORMAT
            },
            "strm_default_scan_interval": {
                "type": "integer",
                "description": "STRM默认扫描间隔",
                "category": "system",
                "unit": "分钟",
                "min": 1,
                "max": 1440,
                "default": cls.STRM_DEFAULT_SCAN_INTERVAL
            },
            "strm_task_concurrency": {
                "type": "integer",
                "description": "STRM任务并发数",
                "category": "system",
                "unit": "个",
                "min": 1,
                "max": 10,
                "default": cls.STRM_TASK_CONCURRENCY
            },
            "upload_task_concurrency": {
                "type": "integer",
                "description": "上传任务并发数",
                "category": "system",
                "unit": "个",
                "min": 1,
                "max": 5,
                "default": cls.UPLOAD_TASK_CONCURRENCY
            },
            "auth_active_refresh_enabled": {
                "type": "boolean",
                "description": "是否启用主动认证刷新",
                "category": "system",
                "default": cls.AUTH_ACTIVE_REFRESH_ENABLED
            },
            "cache_enabled": {
                "type": "boolean",
                "description": "是否启用缓存",
                "category": "performance",
                "default": cls.CACHE_ENABLED
            },
            "cache_ttl": {
                "type": "integer",
                "description": "缓存过期时间",
                "category": "performance",
                "unit": "分钟",
                "min": 1,
                "max": 1440,
                "default": cls.CACHE_TTL / 60
            },
            "cache_persistence_enabled": {
                "type": "boolean",
                "description": "是否启用缓存持久化",
                "category": "performance",
                "default": cls.CACHE_PERSISTENCE_ENABLED
            },
            "cache_persistence_interval_seconds": {
                "type": "integer",
                "description": "缓存持久化快照间隔",
                "category": "performance",
                "unit": "分钟",
                "min": 1,
                "max": 1440,
                "default": cls.CACHE_PERSISTENCE_INTERVAL_SECONDS // 60
            },
            "cache_max_items": {
                "type": "integer",
                "description": "缓存条目最大数量",
                "category": "performance",
                "unit": "条",
                "min": 1000,
                "max": 1000000,
                "default": cls.CACHE_MAX_ITEMS
            },
            "cache_memory_limit_mb": {
                "type": "integer",
                "description": "缓存内存上限（超80%触发淘汰）",
                "category": "performance",
                "unit": "MB",
                "min": 64,
                "max": 16384,
                "default": cls.CACHE_MEMORY_LIMIT_MB
            },
            "webdav_enabled": {
                "type": "boolean",
                "description": "是否启用WebDAV服务",
                "category": "webdav",
                "default": cls.WEBDAV_ENABLED
            },
            "webdav_smart_chunk_enabled": {
                "type": "boolean",
                "description": "是否启用智能块大小",
                "category": "webdav",
                "default": cls.WEBDAV_SMART_CHUNK_ENABLED
            },
            "webdav_chunk_size": {
                "type": "integer",
                "description": "固定块大小",
                "category": "webdav",
                "unit": "KB",
                "min": 64,
                "max": 8192,
                "default": cls.WEBDAV_CHUNK_SIZE // 1024
            },
            "webdav_cache_enabled": {
                "type": "boolean",
                "description": "是否启用WebDAV缓存优化",
                "category": "webdav",
                "default": cls.WEBDAV_CACHE_ENABLED
            },
            "theme": {
                "type": "select",
                "description": "界面主题",
                "category": "ui",
                "options": [
                    {"value": "light", "label": "浅色主题"},
                    {"value": "dark", "label": "深色主题"},
                    {"value": "auto", "label": "跟随系统"}
                ],
                "default": cls.THEME
            },
            "items_per_page": {
                "type": "integer",
                "description": "每页显示项目数",
                "category": "ui",
                "min": 10,
                "max": 200,
                "default": cls.ITEMS_PER_PAGE
            },
            "cache_retention_default_api_interval": {
                "type": "integer",
                "description": "默认API请求间隔",
                "category": "cache_retention",
                "unit": "毫秒",
                "min": 50,
                "max": 10000,   
                "default": cls.CACHE_RETENTION_DEFAULT_API_INTERVAL
            },
            "cache_retention_default_refresh_interval": {
                "type": "integer",
                "description": "默认刷新间隔",
                "category": "cache_retention",
                "unit": "分钟",
                "min": 5,
                "max": 1440,
                "default": cls.CACHE_RETENTION_DEFAULT_REFRESH_INTERVAL
            },
            "mo_proxy_enabled": {
                "type": "boolean", "description": "启用代理", "category": "media_organize", "default": cls.MO_PROXY_ENABLED
            },
            "mo_proxy_url": {
                "type": "string", "description": "代理地址", "category": "media_organize", "default": cls.MO_PROXY_URL
            },
            "mo_proxy_username": {
                "type": "string", "description": "代理用户名", "category": "media_organize", "default": cls.MO_PROXY_USERNAME
            },
            "mo_proxy_password": {
                "type": "password", "description": "代理密码", "category": "media_organize", "sensitive": True, "default": cls.MO_PROXY_PASSWORD
            },
            "mo_tmdb_api_key": {
                "type": "password", "description": "TMDB API Key", "category": "media_organize", "sensitive": True, "default": cls.MO_TMDB_API_KEY
            },
            "mo_tmdb_language": {
                "type": "string", "description": "TMDB 搜索语言", "category": "media_organize", "default": cls.MO_TMDB_LANGUAGE
            },
            "mo_api_request_interval_ms": {
                "type": "integer", "description": "API额外补偿间隔", "category": "media_organize", "unit": "毫秒", "min": 50, "max": 10000, "default": cls.MO_API_REQUEST_INTERVAL_MS
            },
            "mo_ffprobe_request_interval_ms": {
                "type": "integer", "description": "ffprobe请求间隔", "category": "media_organize", "unit": "毫秒", "min": 500, "max": 30000, "default": cls.MO_FFPROBE_REQUEST_INTERVAL_MS
            },
            "mo_tmdb_request_interval_ms": {
                "type": "integer", "description": "TMDB请求间隔", "category": "media_organize", "unit": "毫秒", "min": 100, "max": 5000, "default": cls.MO_TMDB_REQUEST_INTERVAL_MS
            },
            "mo_ffprobe_concurrency": {
                "type": "integer", "description": "ffprobe并发数", "category": "media_organize", "min": 1, "max": 10, "default": cls.MO_FFPROBE_CONCURRENCY
            },
            "mo_ffprobe_timeout_seconds": {
                "type": "integer", "description": "ffprobe超时", "category": "media_organize", "unit": "秒", "min": 5, "max": 120, "default": cls.MO_FFPROBE_TIMEOUT_SECONDS
            },
            "mo_min_confidence_threshold": {
                "type": "number", "description": "最低置信度阈值", "category": "media_organize", "min": 0.1, "max": 1.0, "default": cls.MO_MIN_CONFIDENCE_THRESHOLD
            },
            "mo_file_extensions": {
                "type": "string", "description": "媒体文件扩展名", "category": "media_organize", "default": cls.MO_FILE_EXTENSIONS
            },
            "mo_metadata_extensions": {
                "type": "string", "description": "元数据文件扩展名", "category": "media_organize", "default": cls.MO_METADATA_EXTENSIONS
            },
            "mo_media_tag_order": {
                "type": "string", "description": "媒体信息标签排序", "category": "media_organize", "default": cls.MO_MEDIA_TAG_ORDER
            },
            "mo_align_media_tags": {
                "type": "boolean", "description": "强迫症模式：同后缀文件保持媒体信息一致", "category": "media_organize", "default": cls.MO_ALIGN_MEDIA_TAGS
            },
            "mo_max_works_per_run": {
                "type": "integer", "description": "每次最多整理作品数（0=不限制）", "category": "media_organize", "min": 0, "max": 10000, "default": cls.MO_MAX_WORKS_PER_RUN
            },
            "mo_overwrite_existing": {
                "type": "boolean", "description": "同名冲突时覆盖（默认跳过）", "category": "media_organize", "default": cls.MO_OVERWRITE_EXISTING
            },
        }
    
    @classmethod
    def get_categories(cls) -> Dict[str, str]:
        return {
            "system": "系统设置",
            "security": "安全设置", 
            "performance": "性能设置",
            "webdav": "WebDAV设置",
            "ui": "界面设置",
            "cache_retention": "缓存保持设置",
            "media_organize": "媒体整理设置",
        }
    
    @classmethod
    def _get_or_create_secret_key(cls):
        """SECRET_KEY 优先级：环境变量 > data/.secret_key 文件 > 随机生成并落盘。"""
        secret_file = Path('data/.secret_key')

        env_secret = os.getenv('SECRET_KEY')
        if env_secret:
            return env_secret

        if secret_file.exists():
            try:
                key = secret_file.read_text(encoding='utf-8').strip()
                if key:
                    return key
            except Exception as e:
                print(f"读取密钥文件失败: {e}")

        new_key = secrets.token_urlsafe(64)
        try:
            secret_file.parent.mkdir(exist_ok=True)
            secret_file.write_text(new_key, encoding='utf-8')
            secret_file.chmod(0o600)
            from datetime import datetime
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] ℹ️ 配置 | 新的SECRET_KEY已生成并保存")
        except Exception as e:
            print(f"保存密钥文件失败: {e}")

        return new_key


class ConfigManager:
    """数据库优先、默认值兜底。内部对 sync 入口做兼容，避免在事件循环中误用 asyncio.run。"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._initialized = False

    def initialize_sync(self):
        if self._initialized:
            return

        self._load_from_db_sync()
        self._initialized = True

    def _load_from_db_sync(self):
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(self._load_from_db_async())
                loop.run_until_complete(task)
            except RuntimeError:
                asyncio.run(self._load_from_db_async())
        except Exception as e:
            print(f"从数据库加载配置失败: {e}")

    async def _load_from_db_sync_async(self):
        try:
            await self._load_from_db_async()
        except Exception as e:
            print(f"从数据库加载配置失败: {e}")

    def initialize_sync_force(self):
        if self._initialized:
            return

        print("强制使用同步配置初始化")
        self._load_from_db_sync()
        self._initialized = True

    async def initialize_async(self):
        if self._initialized:
            return

        await self._load_from_db_async()
        self._initialized = True

    async def _load_from_db_async(self):
        try:
            from database.db import get_db
            db_conn = await get_db()

            async with db_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configs'") as cursor:
                result = await cursor.fetchone()

                if not result:
                    await self._create_config_table_async(db_conn)
                    await self._init_default_configs_async()
                    return

            async with db_conn.execute("SELECT key, value FROM configs") as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    key, value_str = row
                    try:
                        self._cache[key] = json.loads(value_str)
                    except json.JSONDecodeError:
                        self._cache[key] = value_str

                await self._init_default_configs_async()

        except Exception as e:
            print(f"从数据库加载配置失败: {e}")

    async def _create_config_table_async(self, db_conn):
        try:
            await db_conn.execute("""
                CREATE TABLE IF NOT EXISTS configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    description TEXT
                )
            """)
            await db_conn.commit()
        except Exception as e:
            if _log_available:
                config_log = get_writer(LogModule.CONFIG)
                config_log.error(f"创建配置表失败: {e}")
            else:
                print(f"创建配置表失败: {e}")

    def get(self, key: str) -> Any:
        if not self._initialized:
            import asyncio
            try:
                asyncio.get_running_loop()
                print("检测到事件循环，使用默认配置值")
                return Settings.get_default_value(key)
            except RuntimeError:
                self.initialize_sync()

        if key in self._cache:
            return self._cache[key]

        return Settings.get_default_value(key)

    async def get_async(self, key: str) -> Any:
        if not self._initialized:
            await self.initialize_async()

        if key in self._cache:
            return self._cache[key]

        return Settings.get_default_value(key)

    def set(self, key: str, value: Any) -> bool:
        if not self._initialized:
            self.initialize_sync()

        try:
            import asyncio
            try:
                asyncio.get_running_loop()
                print(f"检测到事件循环，跳过同步写入配置: {key}")
                return False
            except RuntimeError:
                asyncio.run(self._set_async(key, value))

            return True
        except Exception as e:
            print(f"设置配置失败: {key}={value}, 错误: {e}")
            return False

    async def set_async(self, key: str, value: Any) -> bool:
        if not self._initialized:
            await self.initialize_async()

        await self._set_async(key, value)
        return True

    async def _set_async(self, key: str, value: Any) -> bool:
        from database.db import get_db
        db_conn = await get_db()

        if not hasattr(self, '_table_created'):
            await self._create_config_table_async(db_conn)
            self._table_created = True

        value_str = json.dumps(value)

        await db_conn.execute(
            "INSERT OR REPLACE INTO configs (key, value) VALUES (?, ?)",
            (key, value_str)
        )

        await db_conn.commit()

        self._cache[key] = value

        return True

    def reset_to_default(self, key: str) -> bool:
        if not self._initialized:
            self.initialize_sync()

        try:
            import asyncio
            try:
                asyncio.get_running_loop()
                print(f"检测到事件循环，跳过同步重置配置: {key}")
                return False
            except RuntimeError:
                asyncio.run(self._reset_to_default_async(key))

            return True
        except Exception as e:
            print(f"重置配置失败: {key}, 错误: {e}")
            return False

    async def _reset_to_default_async(self, key: str) -> bool:
        try:
            from database.db import get_db
            db_conn = await get_db()

            if not hasattr(self, '_table_created'):
                await self._create_config_table_async(db_conn)
                self._table_created = True

            await db_conn.execute("DELETE FROM configs WHERE key = ?", (key,))
            await db_conn.commit()

            if key in self._cache:
                del self._cache[key]

            return True

        except Exception as e:
            print(f"重置配置失败: {key}, 错误: {e}")
            return False

    async def _init_default_configs_async(self):
        try:
            from database.db import get_db
            db_conn = await get_db()

            metadata = Settings.get_config_metadata()
            for key, meta in metadata.items():
                default_value = Settings.get_default_value(key)
                if default_value is not None:
                    if key == "strm_token" and not str(default_value):
                        default_value = secrets.token_urlsafe(32)
                    async with db_conn.execute("SELECT key FROM configs WHERE key = ?", (key,)) as cursor:
                        exists = await cursor.fetchone()

                    if not exists:
                        value_str = json.dumps(default_value)
                        await db_conn.execute(
                            "INSERT INTO configs (key, value) VALUES (?, ?)",
                            (key, value_str)
                        )
                        self._cache[key] = default_value

            await db_conn.commit()
            if _log_available:
                config_log = get_writer(LogModule.CONFIG)
                config_log.debug("默认配置初始化完成")
            else:
                print("✓ 默认配置初始化完成")

        except Exception as e:
            print(f"初始化默认配置失败: {e}")

    def get_all_with_metadata(self) -> list:
        if not self._initialized:
            self.initialize_sync()

        metadata = Settings.get_config_metadata()
        result = []

        for key, meta in metadata.items():
            current_value = self.get(key)
            default_value = meta["default"]

            config_item = {
                "key": key,
                "current_value": current_value,
                "default_value": default_value,
                "is_default": current_value == default_value,
                **meta
            }

            if meta.get("sensitive") and key != "admin_username":
                config_item["current_value"] = "******"

            result.append(config_item)

        return result

    def init_default_configs(self):
        if not self._initialized:
            self.initialize_sync()

        try:
            import asyncio
            try:
                asyncio.get_running_loop()
                print("检测到事件循环，跳过同步初始化默认配置")
                return
            except RuntimeError:
                asyncio.run(self._init_default_configs_async())

        except Exception as e:
            print(f"初始化默认配置失败: {e}")


settings = Settings()
config_manager = ConfigManager()


def get_oauth_server_url() -> str:
    value = config_manager.get("oauth_server_url")
    if not value:
        value = Settings.OAUTH_SERVER_URL
    return str(value).rstrip("/")

Settings.SECRET_KEY = Settings._get_or_create_secret_key()


def get_config(key: str) -> Any:
    return config_manager.get(key)

def set_config(key: str, value: Any) -> bool:
    return config_manager.set(key, value)

def reset_config(key: str) -> bool:
    return config_manager.reset_to_default(key)
