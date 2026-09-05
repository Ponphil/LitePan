package api

import (
	"compress/gzip"
	"embed"
	"io"
	"io/fs"
	"log/slog"
	"mime"
	"net/http"
	"path"
	"strconv"
	"strings"
	"sync"

	"github.com/go-chi/chi/v5"
	chimw "github.com/go-chi/chi/v5/middleware"
	"github.com/google/uuid"

	"litepan/internal/account"
	"litepan/internal/accountprofile"
	"litepan/internal/adminauth"
	"litepan/internal/aiorganize"
	"litepan/internal/announcement"
	"litepan/internal/apikey"
	"litepan/internal/auth"
	"litepan/internal/automation"
	"litepan/internal/backuprestore"
	"litepan/internal/cache"
	"litepan/internal/cacheretention"
	"litepan/internal/classifyorganize"
	"litepan/internal/coverextract"
	"litepan/internal/crosstransfer"
	"litepan/internal/domain"
	"litepan/internal/embyproxy"
	"litepan/internal/favorites"
	"litepan/internal/file"
	"litepan/internal/fnosproxy"
	"litepan/internal/fusemount"
	"litepan/internal/logx"
	"litepan/internal/mediaorganize"
	"litepan/internal/notification"
	"litepan/internal/offlinedownload"
	"litepan/internal/playback"
	"litepan/internal/quarktv"
	"litepan/internal/settings"
	"litepan/internal/share/dav"
	"litepan/internal/spacecleanup"
	"litepan/internal/strm"
	"litepan/internal/strmscrape"
	"litepan/internal/upload"
)

//go:embed web
var webFS embed.FS

// Deps 是 API 层所需依赖（只依赖接口/服务，不感知具体存储实现）。
type Deps struct {
	Logs              *logx.Manager
	AccountSvc        *account.Service
	AccountProfile    *accountprofile.Service
	Accounts          domain.AccountRepository
	Configs           domain.ConfigRepository
	Settings          *settings.Service
	Cache             *cache.Service
	ListHitTracker    *cache.HitTracker
	Files             *file.Service
	Favorites         *favorites.Service
	Uploads           *upload.Manager
	OfflineDownloads  *offlinedownload.Service
	Playback          *playback.Service
	Strm              *strm.Service
	CacheRetention    *cacheretention.Service
	MediaOrganize     *mediaorganize.Service
	AIOrganize        *aiorganize.Service
	ClassifyOrganize  *classifyorganize.Service
	StrmScrape        *strmscrape.Service
	Automation        *automation.Service
	Fuse              *fusemount.Service
	CrossTransfer     *crosstransfer.Service
	EmbyProxy         *embyproxy.Service
	FnosProxy         *fnosproxy.Service
	QuarkTV           *quarktv.Service
	ApiKeys           *apikey.Service
	Auth              *auth.Service
	AuthSched         *auth.Scheduler
	AdminAuth         *adminauth.Service
	Notifications     *notification.Service
	Announcement      *announcement.Service
	BackupRestore     *backuprestore.Service
	SpaceCleanup      *spacecleanup.Service
	CoverExtract      *coverextract.Service
	DataDir           string
	StrmDir           string
	OnSettingsUpdated func(map[string]string)
}

// Handler 持有处理请求所需的依赖。
type Handler struct {
	bootID            string
	logs              *logx.Manager
	log               *slog.Logger
	accountSvc        *account.Service
	accountProfile    *accountprofile.Service
	settings          *settings.Service
	cache             *cache.Service
	listHits          *cache.HitTracker
	files             *file.Service
	favorites         *favorites.Service
	uploads           *upload.Manager
	offlineDownloads  *offlinedownload.Service
	playback          *playback.Service
	strm              *strm.Service
	cacheRetention    *cacheretention.Service
	mediaOrganize     *mediaorganize.Service
	aiOrganize        *aiorganize.Service
	classifyOrganize  *classifyorganize.Service
	strmScrape        *strmscrape.Service
	automation        *automation.Service
	fuse              *fusemount.Service
	crossTransfer     *crosstransfer.Service
	embyProxy         *embyproxy.Service
	fnosProxy         *fnosproxy.Service
	quarktv           *quarktv.Service
	apiKeys           *apikey.Service
	auth              *auth.Service
	authSched         *auth.Scheduler
	adminAuth         *adminauth.Service
	notifications     *notification.Service
	announcement      *announcement.Service
	backupRestore     *backuprestore.Service
	spaceCleanup      *spacecleanup.Service
	coverExtract      *coverextract.Service
	dataDir           string
	strmDir           string
	onSettingsUpdated func(map[string]string)

	devMu       sync.Mutex
	devUnlocked bool
}

// NewRouter 装配并返回 HTTP 路由（含内嵌管理页面）。
func NewRouter(d Deps) http.Handler {
	apiLog := slog.Default()
	if d.Logs != nil {
		apiLog = d.Logs.For(logx.ModuleAPI)
	}
	h := &Handler{
		bootID:            uuid.NewString(),
		logs:              d.Logs,
		log:               apiLog,
		accountSvc:        d.AccountSvc,
		accountProfile:    d.AccountProfile,
		settings:          d.Settings,
		cache:             d.Cache,
		listHits:          d.ListHitTracker,
		files:             d.Files,
		favorites:         d.Favorites,
		uploads:           d.Uploads,
		offlineDownloads:  d.OfflineDownloads,
		playback:          d.Playback,
		strm:              d.Strm,
		cacheRetention:    d.CacheRetention,
		mediaOrganize:     d.MediaOrganize,
		aiOrganize:        d.AIOrganize,
		classifyOrganize:  d.ClassifyOrganize,
		strmScrape:        d.StrmScrape,
		automation:        d.Automation,
		fuse:              d.Fuse,
		crossTransfer:     d.CrossTransfer,
		embyProxy:         d.EmbyProxy,
		fnosProxy:         d.FnosProxy,
		quarktv:           d.QuarkTV,
		apiKeys:           d.ApiKeys,
		auth:              d.Auth,
		authSched:         d.AuthSched,
		adminAuth:         d.AdminAuth,
		notifications:     d.Notifications,
		announcement:      d.Announcement,
		backupRestore:     d.BackupRestore,
		spaceCleanup:      d.SpaceCleanup,
		coverExtract:      d.CoverExtract,
		dataDir:           d.DataDir,
		strmDir:           d.StrmDir,
		onSettingsUpdated: d.OnSettingsUpdated,
	}

	r := chi.NewRouter()
	r.Use(trackResponseCommit)
	r.Use(chimw.RequestID)
	r.Use(h.attachRequestLogger)
	r.Use(h.logSlowDashboardRequests)
	r.Use(chimw.Recoverer)

	r.Route("/api", func(r chi.Router) {
		r.Get("/internal/cover-source/{token}", h.coverExtractSource)
		r.Get("/health", h.health)
		r.Get("/auth/status", h.authStatus)
		r.Post("/auth/login", h.authLogin)
		r.Post("/auth/logout", h.authLogout)
		r.Post("/auth/reset-password", h.authResetPassword)
		r.Get("/strm/play/{account_id}/{file_key}/t/{token}/n/{filename}", h.strmPlay)
		r.Head("/strm/play/{account_id}/{file_key}/t/{token}/n/{filename}", h.strmPlay)
		r.Get("/strm/play/{account_id}/{file_key}/t/{token}/n/{filename}/s/{signature}", h.strmPlay)
		r.Head("/strm/play/{account_id}/{file_key}/t/{token}/n/{filename}/s/{signature}", h.strmPlay)
		r.Route("/public", func(r chi.Router) {
			r.Use(h.requirePublicOrAdmin)
			r.Get("/accounts", h.publicAccounts)
			r.Get("/system-config", h.publicSystemConfig)
			r.Get("/cache/hit-rate", h.publicCacheHitRate)
		})
		r.Route("/open", func(r chi.Router) {
			r.Post("/automation/events", h.automationWebhook)
		})
		r.Group(func(r chi.Router) {
			r.Use(h.requireAdmin)
			r.Route("/cross-transfer", func(r chi.Router) {
				r.Get("/routes", h.crossTransferRoutes)
				r.Post("/scan", h.crossTransferScan)
				r.Post("/scan/stream", h.crossTransferScanStream)
				r.Post("/probe", h.crossTransferProbe)
				r.Post("/execute", h.crossTransferExecute)
				r.Post("/plain-enqueue", h.crossTransferPlainEnqueue)
			})
			r.Get("/logs", h.listLogs)
			r.Get("/logs/stats", h.logStats)
			r.Post("/logs/ack-errors", h.ackRecentErrors)
			r.Post("/logs/cleanup", h.cleanupLogs)
			r.Post("/logs/cleanup/keep-today", h.cleanupLogsKeepToday)
			r.Post("/logs/cleanup/all", h.cleanupLogsAll)
			r.Route("/admin", func(r chi.Router) {
				r.Get("/system-config", h.adminSystemConfig)
				r.Route("/backups", func(r chi.Router) {
					r.Get("/", h.listBackups)
					r.Post("/", h.createBackup)
					r.Post("/import", h.importBackup)
					r.Get("/status", h.backupRestoreStatus)
					r.Post("/status/ack", h.acknowledgeRestoreStatus)
					r.Delete("/pending", h.cancelPendingRestore)
					r.Post("/restart", h.restartForRestore)
					r.Get("/{id}/download", h.downloadBackup)
					r.Post("/{id}/restore", h.prepareBackupRestore)
					r.Delete("/{id}", h.deleteBackup)
				})
				r.Post("/update-credentials", h.adminUpdateCredentials)
				r.Post("/webdav-config", h.adminWebDAVConfig)
				r.Get("/emby/configs", h.listEmbyConfigs)
				r.Put("/emby/configs", h.replaceEmbyConfigs)
				r.Post("/emby/test", h.testEmbyConfig)
				r.Get("/emby/libraries", h.listEmbyLibraries)
				r.Post("/emby/refresh", h.refreshEmbyLibrary)
				r.Get("/fnos/config", h.getFnosConfig)
				r.Put("/fnos/config", h.updateFnosConfig)
				r.Post("/fnos/test", h.testFnosConfig)
				r.Get("/local-fs/browse", h.browseLocalFS)
				r.Get("/drivers", h.listDrivers)
				r.Get("/dev/state", h.getDevState)
				r.Post("/dev/unlock", h.unlockDevMode)
				r.Get("/accounts", h.listAccounts)
				r.Post("/accounts", h.createAccount)
				r.Get("/accounts/{id}", h.getAccount)
				r.Put("/accounts/{id}", h.updateAccount)
				r.Delete("/accounts/{id}", h.deleteAccount)
				r.Post("/accounts/{id}/toggle", h.toggleAccount)
				r.Post("/accounts/{id}/set-default", h.setDefaultAccount)
				r.Post("/accounts/{id}/refresh-auth", h.refreshAccountAuth)
				r.Post("/accounts/{id}/refresh-profile", h.refreshAccountProfile)
				r.Get("/settings", h.getSettings)
				r.Put("/settings", h.updateSettings)
				r.Route("/api-keys", func(r chi.Router) {
					r.Get("/", h.listApiKeys)
					r.Post("/", h.createApiKey)
					r.Post("/strm/rotate", h.rotateStrmKey)
					r.Put("/{id}", h.updateApiKey)
					r.Post("/{id}/toggle", h.toggleApiKey)
					r.Delete("/{id}", h.deleteApiKey)
				})
				r.Get("/cache/stats", h.cacheStats)
				r.Get("/cache/stats/{id}", h.accountCacheStats)
				r.Post("/clear-cache", h.clearCache)
				r.Route("/cache-retention", func(r chi.Router) {
					r.Get("/configs", h.listRetentionTasks)
					r.Get("/stats", h.getRetentionStats)
					r.Get("/defaults", h.retentionDefaults)
					r.Get("/startup", h.retentionStartupRemaining)
					r.Post("/configs", h.createRetentionTask)
					r.Put("/configs/{id}", h.updateRetentionTask)
					r.Delete("/configs/{id}", h.deleteRetentionTask)
					r.Post("/configs/{id}/toggle", h.toggleRetentionTask)
					r.Post("/configs/{id}/refresh", h.refreshRetentionTask)
					r.Post("/configs/{id}/force-stop", h.forceStopRetentionTask)
					r.Post("/configs/{id}/ack-scope-warn", h.ackRetentionScopeWarn)
				})
				r.Get("/notifications", h.listNotifications)
				r.Get("/notifications/unread-count", h.notificationUnreadCount)
				r.Post("/notifications/read-all", h.markAllNotificationsRead)
				r.Delete("/notifications", h.deleteAllNotifications)
				r.Post("/notifications/{id}/read", h.markNotificationRead)
				r.Delete("/notifications/{id}", h.deleteNotification)
				r.Get("/announcement", h.getAnnouncement)
				r.Post("/announcement/read", h.markAnnouncementRead)
				r.Route("/strm", func(r chi.Router) {
					r.Get("/startup", h.strmStartupRemaining)
					r.Get("/tasks", h.listStrmTasks)
					r.Post("/tasks", h.createStrmTask)
					r.Put("/tasks/{id}", h.updateStrmTask)
					r.Delete("/tasks/{id}", h.deleteStrmTask)
					r.Post("/tasks/{id}/toggle", h.toggleStrmTask)
					r.Post("/tasks/{id}/run", h.runStrmTaskNow)
					r.Post("/tasks/{id}/force-stop", h.forceStopStrmTask)
					r.Get("/tasks/{id}/branches", h.listStrmBranches)
					r.Post("/tasks/{id}/branches", h.createStrmBranch)
					r.Put("/tasks/{id}/branches/{branch_id}", h.updateStrmBranch)
					r.Delete("/tasks/{id}/branches/{branch_id}", h.deleteStrmBranch)
					r.Get("/settings", h.getStrmSettings)
					r.Put("/settings", h.updateStrmSettings)
					r.Post("/replace-base-url", h.replaceStrmBaseURL)
					r.Post("/tasks/precheck-account-repair", h.precheckStrmAccountRepair)
					r.Post("/tasks/repair-account-references", h.repairStrmAccountReferences)
					r.Post("/generate-current-directory", h.generateCurrentDirectoryStrm)
					r.Post("/directory-status", h.checkStrmDirectoryStatus)
				})
				r.Route("/tools/115-strm", func(r chi.Router) {
					r.Get("/status", h.get115StrmToolStatus)
					r.Post("/enabled", h.set115StrmToolEnabled)
					r.Post("/cache/clear", h.clear115StrmDirCache)
				})
				r.Route("/tools/local-upload", func(r chi.Router) {
					r.Get("/config", h.getLocalUploadConfig)
					r.Put("/config", h.updateLocalUploadConfig)
					r.Post("/browse", h.browseLocalUpload)
					r.Post("/upload", h.createLocalUploadTasks)
				})
				r.Route("/tools/ai-organize", func(r chi.Router) {
					r.Get("/config", h.getAIOrganizeConfig)
					r.Put("/config", h.updateAIOrganizeConfig)
					r.Post("/test", h.testAIOrganizeConfig)
				})
				r.Route("/tools/classification", func(r chi.Router) {
					r.Get("/config", h.getClassificationConfig)
					r.Put("/config", h.updateClassificationConfig)
					r.Post("/tmdb-detail", h.lookupClassificationTMDBDetail)
				})
				r.Route("/tools/quarktv", func(r chi.Router) {
					r.Get("/status", h.getQuarkTVStatus)
					r.Post("/enabled", h.setQuarkTVEnabled)
					r.Get("/accounts", h.listQuarkTVAccounts)
					r.Post("/bind/start", h.startQuarkTVBind)
					r.Post("/bind/poll", h.pollQuarkTVBind)
					r.Put("/binding/settings", h.updateQuarkTVBindingSettings)
					r.Delete("/bind", h.unbindQuarkTV)
				})
				r.Route("/tools/cleanup", func(r chi.Router) {
					r.Post("/scan", h.scanSpaceCleanup)
					r.Post("/execute", h.executeSpaceCleanup)
					r.Get("/report", h.latestSpaceCleanupReport)
				})
				r.Route("/tools/cover-extract", func(r chi.Router) {
					r.Put("/enabled", h.updateCoverExtractEnabled)
					r.Get("/files", h.listCoverExtractFiles)
					r.Post("/files", h.addCoverExtractFile)
					r.Delete("/files", h.clearCoverExtractFiles)
					r.Delete("/files/{id}", h.removeCoverExtractFile)
					r.Delete("/files/{id}/frames/{frameID}", h.removeCoverFrame)
					r.Put("/files/{id}/target", h.updateCoverExtractTarget)
					r.Post("/extract", h.extractCoverFrames)
					r.Get("/images/{id}", h.coverExtractImage)
					r.Post("/save", h.saveCoverFrame)
					r.Post("/save-composed", h.saveComposedCover)
					r.Get("/runtime", h.coverExtractRuntime)
					r.Post("/runtime/download", h.downloadCoverExtractRuntime)
					r.Get("/style", h.getCoverStyle)
					r.Put("/style", h.putCoverStyle)
				})
				r.Route("/media-organize", func(r chi.Router) {
					r.Get("/tasks", h.listMediaOrganizeTasks)
					r.Post("/tasks", h.createMediaOrganizeTask)
					r.Put("/tasks/{id}", h.updateMediaOrganizeTask)
					r.Delete("/tasks/{id}", h.deleteMediaOrganizeTask)
					r.Post("/tasks/{id}/plan", h.planMediaOrganizeTask)
					r.Get("/tasks/{id}/plan", h.getMediaOrganizePlan)
					r.Delete("/tasks/{id}/plan", h.deleteMediaOrganizePlan)
					r.Put("/tasks/{id}/plan/actions/{action_id}", h.updateMediaOrganizePlanAction)
					r.Delete("/tasks/{id}/plan/actions/{action_id}", h.deleteMediaOrganizePlanAction)
					r.Post("/tasks/{id}/plan/actions/batch-delete", h.batchDeleteMediaOrganizePlanActions)
					r.Post("/tasks/{id}/apply", h.applyMediaOrganizeTask)
					r.Post("/tasks/{id}/run", h.runMediaOrganizeTask)
					r.Post("/tasks/{id}/stop", h.stopMediaOrganizeTask)
					r.Get("/tasks/{id}/logs", h.getMediaOrganizeLogs)
					r.Get("/tasks/{id}/progress", h.getMediaOrganizeProgress)
					r.Get("/settings", h.getMediaOrganizeSettings)
					r.Put("/settings", h.updateMediaOrganizeSettings)
					r.Get("/guess-file", h.guessMediaOrganizeFile)
					r.Post("/test-tmdb", h.testMediaOrganizeTMDB)
					r.Get("/search-tmdb", h.searchMediaOrganizeTMDB)
					r.Post("/tasks/{id}/bindings", h.setMediaOrganizeBinding)
				})
				r.Route("/strm-scrape", func(r chi.Router) {
					r.Get("/settings", h.getStrmScrapeSettings)
					r.Put("/settings", h.updateStrmScrapeSettings)
					r.Get("/scope", h.getStrmScrapeScope)
					r.Put("/scope", h.updateStrmScrapeScope)
					r.Get("/scope/directories", h.listStrmScrapeScopeDirectories)
					r.Post("/run", h.runStrmScrape)
					r.Post("/stop", h.stopStrmScrape)
					r.Get("/progress", h.getStrmScrapeProgress)
					r.Get("/items", h.listStrmScrapeItems)
					r.Post("/refresh-index", h.refreshStrmScrapeIndex)
					r.Post("/rematch", h.rematchStrmScrapeItem)
					r.Post("/rescrape", h.rescrapeStrmScrapeItem)
					r.Post("/mark-normal", h.markStrmScrapeNormal)
					r.Get("/poster", h.getStrmScrapePoster)
				})
				r.Route("/automation", func(r chi.Router) {
					r.Get("/rules", h.listAutomationRules)
					r.Post("/rules", h.createAutomationRule)
					r.Put("/rules/{id}", h.updateAutomationRule)
					r.Delete("/rules/{id}", h.deleteAutomationRule)
					r.Post("/rules/{id}/toggle", h.toggleAutomationRule)
					r.Post("/rules/{id}/run", h.runAutomationRule)
					r.Post("/validate", h.validateAutomationRule)
					r.Get("/runs", h.listAutomationRuns)
					r.Post("/runs/clear", h.clearAutomationRuns)
					r.Get("/options", h.automationOptions)
				})
				r.Route("/fuse", func(r chi.Router) {
					r.Get("/status", h.fuseStatus)
					r.Put("/config", h.updateFuseConfig)
					r.Get("/read-cache", h.getFuseReadCache)
					r.Put("/read-cache", h.updateFuseReadCache)
					r.Post("/read-cache/clear", h.clearFuseReadCache)
					r.Get("/mounts", h.listFuseMounts)
					r.Post("/mounts", h.createFuseMount)
					r.Put("/mounts/{id}", h.updateFuseMount)
					r.Delete("/mounts/{id}", h.deleteFuseMount)
					r.Post("/mounts/{id}/mount", h.mountFuse)
					r.Post("/mounts/{id}/unmount", h.unmountFuse)
				})
			})
			r.Post("/oauth/start", h.startOAuth)
			r.Get("/oauth/status/{session_id}", h.oauthStatus)
			r.Post("/oauth/confirm-received/{session_id}", h.oauthConfirmReceived)
			r.Post("/qr/start", h.startQRLogin)
			r.Post("/qr/poll", h.pollQRLogin)
		})
		r.Route("/files", func(r chi.Router) {
			r.Group(func(r chi.Router) {
				r.Use(h.requirePublicOrAdmin)
				r.Get("/list", h.listFiles)
				r.Get("/info", h.fileInfo)
				r.Get("/download", h.downloadFile)
				r.Head("/download", h.downloadFile)
			})
			r.Group(func(r chi.Router) {
				r.Use(h.requireAdmin)
				r.Delete("/delete", h.deleteFiles)
				r.Post("/move", h.moveFiles)
				r.Post("/copy", h.copyFiles)
				r.Put("/rename", h.renameFile)
				r.Get("/favorites", h.getFavorites)
				r.Put("/favorites", h.saveFavorites)
				r.Post("/name-align/preview", h.previewNameAlign)
				r.Post("/name-align/apply", h.applyNameAlign)
				r.Post("/create-folder", h.createFolder)
				r.Post("/upload-task", h.createUploadTask)
				r.Get("/upload/runtime", h.getUploadRuntime)
				r.Put("/upload/runtime", h.updateUploadRuntime)
				r.Get("/upload/tasks", h.listUploadTasks)
				r.Get("/upload/tasks/stream", h.streamUploadTasks)
				r.Get("/upload/tasks/{taskID}", h.getUploadTask)
				r.Post("/upload/tasks/{taskID}/pause", h.pauseUploadTask)
				r.Post("/upload/tasks/{taskID}/resume", h.resumeUploadTask)
				r.Delete("/upload/tasks/{taskID}", h.deleteUploadTask)
				r.Post("/upload/tasks/batch-pause", h.batchPauseUploadTasks)
				r.Post("/upload/tasks/batch-delete", h.batchDeleteUploadTasks)
				r.Route("/offline-download", func(r chi.Router) {
					r.Get("/capabilities", h.offlineDownloadCapabilities)
					r.Post("/urls", h.addOfflineURLs)
					r.Post("/torrent/prepare", h.prepareOfflineTorrent)
					r.Post("/torrent", h.addOfflineTorrent)
					r.Get("/tasks", h.listOfflineDownloadTasks)
					r.Post("/tasks/refresh", h.refreshOfflineDownloadTasks)
					r.Post("/tasks/batch-delete", h.batchDeleteOfflineDownloadTasks)
					r.Delete("/tasks/{taskID}", h.deleteOfflineDownloadTask)
				})
			})
		})
	})

	davLog := apiLog
	if d.Logs != nil {
		davLog = d.Logs.For(logx.ModuleWebDAV)
	}
	davSrv := dav.New(dav.Deps{
		Logs:         davLog,
		Files:        d.Files,
		Playback:     d.Playback,
		Accounts:     d.Accounts,
		Configs:      d.Configs,
		Cache:        d.Cache,
		Settings:     d.Settings,
		DataDir:      d.DataDir,
		TempRegistry: d.Uploads.TempRegistry(),
	})

	sub, err := fs.Sub(webFS, "web")
	if err != nil {
		panic(err) // 编译期内嵌，理论上不会失败
	}
	r.Handle("/*", spaHandler(sub))

	return davBypass(davSrv, r)
}

// chi 不认 WebDAV 方法，/dav 须在外层旁路
func davBypass(dav http.Handler, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/dav" || strings.HasPrefix(r.URL.Path, "/dav/") {
			dav.ServeHTTP(w, r)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func spaHandler(fsys fs.FS) http.Handler {
	fileServer := http.FileServer(http.FS(fsys))
	index, _ := fs.ReadFile(fsys, "index.html")
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upath := strings.TrimPrefix(path.Clean(r.URL.Path), "/")
		if upath == "" {
			upath = "index.html"
		}
		if _, statErr := fs.Stat(fsys, upath); statErr == nil {
			setStaticCacheHeader(w, upath)
			fileServer.ServeHTTP(w, r)
			return
		}
		if _, statErr := fs.Stat(fsys, upath+".gz"); statErr == nil {
			serveCompressedAsset(w, r, fsys, upath)
			return
		}
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		if r.Method != http.MethodHead {
			_, _ = w.Write(index)
		}
	})
}

func serveCompressedAsset(w http.ResponseWriter, r *http.Request, fsys fs.FS, upath string) {
	compressed, err := fsys.Open(upath + ".gz")
	if err != nil {
		http.NotFound(w, r)
		return
	}
	defer compressed.Close()
	info, err := compressed.Stat()
	if err != nil {
		http.Error(w, "静态资源读取失败", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
	w.Header().Set("Content-Type", staticContentType(upath))
	w.Header().Set("Vary", "Accept-Encoding")
	if acceptsGzip(r.Header.Get("Accept-Encoding")) {
		w.Header().Set("Content-Encoding", "gzip")
		w.Header().Set("Content-Length", strconv.FormatInt(info.Size(), 10))
		if r.Method != http.MethodHead {
			_, _ = io.Copy(w, compressed)
		}
		return
	}

	if r.Method == http.MethodHead {
		return
	}
	reader, err := gzip.NewReader(compressed)
	if err != nil {
		http.Error(w, "静态资源解压失败", http.StatusInternalServerError)
		return
	}
	defer reader.Close()
	_, _ = io.Copy(w, reader)
}

func setStaticCacheHeader(w http.ResponseWriter, upath string) {
	if strings.HasPrefix(upath, "assets/") {
		w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
		return
	}
	w.Header().Set("Cache-Control", "no-cache")
}

func staticContentType(name string) string {
	if contentType := mime.TypeByExtension(path.Ext(name)); contentType != "" {
		return contentType
	}
	switch path.Ext(name) {
	case ".mjs", ".js":
		return "text/javascript; charset=utf-8"
	case ".wasm":
		return "application/wasm"
	default:
		return "application/octet-stream"
	}
}

func acceptsGzip(header string) bool {
	wildcard := false
	for _, value := range strings.Split(header, ",") {
		parts := strings.Split(strings.TrimSpace(value), ";")
		coding := strings.ToLower(strings.TrimSpace(parts[0]))
		quality := 1.0
		for _, parameter := range parts[1:] {
			key, raw, found := strings.Cut(strings.TrimSpace(parameter), "=")
			if !found || !strings.EqualFold(key, "q") {
				continue
			}
			parsed, err := strconv.ParseFloat(raw, 64)
			if err != nil {
				quality = 0
			} else {
				quality = parsed
			}
		}
		if coding == "gzip" {
			return quality > 0
		}
		if coding == "*" {
			wildcard = quality > 0
		}
	}
	return wildcard
}
