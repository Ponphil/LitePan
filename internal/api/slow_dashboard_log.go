package api

import (
	"net/http"
	"time"
)

const slowDashboardRequestThreshold = time.Second

var dashboardOverviewPaths = map[string]struct{}{
	"/api/admin/accounts":                   {},
	"/api/admin/cache-retention/configs":    {},
	"/api/admin/cache-retention/stats":      {},
	"/api/admin/cache/stats":                {},
	"/api/admin/fuse/mounts":                {},
	"/api/admin/media-organize/tasks":       {},
	"/api/admin/notifications":              {},
	"/api/admin/notifications/unread-count": {},
	"/api/admin/strm/tasks":                 {},
	"/api/logs/stats":                       {},
}

func (h *Handler) logSlowDashboardRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet || !isDashboardOverviewPath(r.URL.Path) {
			next.ServeHTTP(w, r)
			return
		}

		startedAt := time.Now()
		next.ServeHTTP(w, r)
		elapsed := time.Since(startedAt)
		if elapsed < slowDashboardRequestThreshold {
			return
		}
		requestLogger(r.Context()).Info(
			"后台概况接口响应较慢",
			"method", r.Method,
			"path", r.URL.Path,
			"duration_ms", elapsed.Milliseconds(),
		)
	})
}

func isDashboardOverviewPath(path string) bool {
	_, ok := dashboardOverviewPaths[path]
	return ok
}
