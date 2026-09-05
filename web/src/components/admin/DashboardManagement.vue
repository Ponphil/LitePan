<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref } from "vue";
import { accountsApi } from "@/api/accounts";
import { clearCache, fetchCacheStats, type CacheStats } from "@/api/cache";
import {
  fetchCacheRetentionStats,
  fetchCacheRetentionTasks,
  type CacheRetentionStats,
  type CacheRetentionTask,
} from "@/api/cacheRetention";
import { getApiErrorMessage } from "@/api/client";
import { fetchFuseMounts, type FuseMount } from "@/api/fuse";
import { logsApi, type LogStats } from "@/api/logs";
import { fetchMediaOrganizeTasks, type MediaOrganizeTask } from "@/api/mediaOrganize";
import { fetchNotifications, fetchUnreadCount, type NotificationItem } from "@/api/notifications";
import type { Account } from "@/api/types";
import { fetchStrmTasks, type StrmTask } from "@/api/strm";
import SectionTabBar from "@/components/admin/SectionTabBar.vue";
import AppCardActionButton from "@/components/base/AppCardActionButton.vue";
// 日志面板非默认 tab，按需加载,减小仪表盘首包。
const SystemLogs = defineAsyncComponent(() => import("@/components/admin/SystemLogs.vue"));
import { useSectionTabRoute } from "@/composables/useSectionTabRoute";
import { useAdminPageLoading } from "@/composables/useAdminLoadingBar";
import { toast } from "@/composables/useToast";
import { formatRelativeTimeAgo, formatSize } from "@/utils/format";
import "@/styles/admin-shared.css";

const OVERVIEW_TAB = "overview";
const LOGS_TAB = "logs";
const OVERVIEW_REVEAL_DEADLINE_MS = 1000;
const VALID_TABS = [OVERVIEW_TAB, LOGS_TAB] as const;

const tabs = [
  { key: OVERVIEW_TAB, label: "运行概况" },
  { key: LOGS_TAB, label: "系统日志" },
];

const { activeTab, setActiveTab } = useSectionTabRoute(OVERVIEW_TAB, VALID_TABS);
const logPresetLevel = ref<string | number>("");
const logPresetSeq = ref(0);

const accounts = ref<Account[]>([]);
const cacheStats = ref<CacheStats | null>(null);
const cacheRetentionTasks = ref<CacheRetentionTask[]>([]);
const cacheRetentionStats = ref<CacheRetentionStats | null>(null);
const fuseMounts = ref<FuseMount[]>([]);
const strmTasks = ref<StrmTask[]>([]);
const organizeTasks = ref<MediaOrganizeTask[]>([]);
const notifications = ref<NotificationItem[]>([]);
const unreadCount = ref(0);
const logStats = ref<LogStats | null>(null);
const loading = ref(true);
const refreshing = ref(false);
const clearingCache = ref(false);
const loadError = ref("");
const hasLoadedOverview = ref(false);
let overviewLoadSequence = 0;
useAdminPageLoading("dashboard", computed(() => activeTab.value === OVERVIEW_TAB && loading.value));

const accountCount = computed(() => accounts.value.length);
const activeAccountCount = computed(() => accounts.value.filter((account) => account.is_active).length);
const inactiveAccountCount = computed(() => Math.max(0, accountCount.value - activeAccountCount.value));
const authErrorAccountCount = computed(() => accounts.value.filter((account) => isAccountAuthError(account)).length);
const cooldownAccountCount = computed(() => accounts.value.filter((account) => isAccountCooldown(account)).length);

const enabledStrmCount = computed(
  () => strmTasks.value.filter((task) => isStrmTaskEnabled(task)).length,
);
const enabledCacheCount = computed(() => {
  if (cacheRetentionStats.value) return cacheRetentionStats.value.running;
  return cacheRetentionTasks.value.filter((task) => isCacheTaskEnabled(task)).length;
});
const enabledOrganizeCount = computed(
  () => organizeTasks.value.filter((task) => isOrganizeTaskEnabled(task)).length,
);
const enabledTaskCount = computed(
  () => enabledStrmCount.value + enabledCacheCount.value + enabledOrganizeCount.value,
);
const totalTaskCount = computed(
  () =>
    strmTasks.value.length +
    (cacheRetentionStats.value?.total ?? cacheRetentionTasks.value.length) +
    organizeTasks.value.length,
);
const mountedFuseCount = computed(() => fuseMounts.value.filter((mount) => mount.state === "mounted").length);
const totalFuseCount = computed(() => fuseMounts.value.length);

const recentErrorCount = computed(() => logStats.value?.recent_unacknowledged_errors ?? 0);
const recentErrorTotal = computed(() => logStats.value?.recent_errors ?? 0);
const systemStatus = computed(() => {
  if (authErrorAccountCount.value > 0) {
    return { label: "账号需要重新授权", tone: "danger", icon: "fa-triangle-exclamation" };
  }
  if (cooldownAccountCount.value > 0) {
    return { label: "账号认证冷却中", tone: "warn", icon: "fa-clock" };
  }
  if (recentErrorCount.value > 0) return { label: "需要留意", tone: "warn", icon: "fa-triangle-exclamation" };
  if (inactiveAccountCount.value > 0) return { label: "部分账号未启用", tone: "warn", icon: "fa-circle-info" };
  return { label: "运行正常", tone: "ok", icon: "fa-check" };
});
const systemStatusText = computed(() => {
  if (authErrorAccountCount.value > 0) {
    return `${authErrorAccountCount.value} 个账号认证已失效，需要重新授权`;
  }
  if (cooldownAccountCount.value > 0) {
    return `${cooldownAccountCount.value} 个账号认证刷新失败，正在等待系统重试`;
  }
  if (recentErrorCount.value > 0) return `近 24 小时有 ${recentErrorTotal.value} 条错误日志，${recentErrorCount.value} 条待确认`;
  if (recentErrorTotal.value > 0) return "近 24 小时错误已确认，当前无新的待确认错误";
  if (inactiveAccountCount.value > 0) return `${inactiveAccountCount.value} 个账号未启用，其余模块正常`;
  return "账号、任务与缓存服务状态正常";
});
const canJumpToErrorLogs = computed(
  () => recentErrorCount.value > 0 && authErrorAccountCount.value === 0 && cooldownAccountCount.value === 0,
);

const generatedStrmCount = computed(() => strmTasks.value.reduce((sum, task) => sum + (task.generated_count || 0), 0));
const cacheHitRate = computed(() => `${Math.round(cacheStats.value?.hit_rate ?? 0)}%`);
const cacheItemCount = computed(() => cacheStats.value?.total_keys ?? 0);
const cacheSizeLabel = computed(() => formatSize(cacheStats.value?.total_size_bytes ?? 0));
const latestCacheRefresh = computed(() => latestTime(cacheRetentionTasks.value.map((task) => task.last_refresh)));
const latestStrmScan = computed(() => latestTime(strmTasks.value.map((task) => task.last_scan)));
const latestOrganizeRun = computed(() => latestTime(organizeTasks.value.map((task) => task.last_run_at)));

const sortedAccounts = computed(() =>
  [...accounts.value].sort((a, b) => {
    if (a.is_default !== b.is_default) return a.is_default ? -1 : 1;
    if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order;
    return a.id - b.id;
  }),
);
const taskSummaries = computed(() => [
  {
    title: "缓存任务",
    icon: "fa-box-archive",
    count: cacheRetentionStats.value?.total ?? cacheRetentionTasks.value.length,
    enabled: enabledCacheCount.value,
    detail: `${cacheItemCount.value} 条缓存 · ${cacheHitRate.value} 命中率`,
    progress: taskProgress(
      enabledCacheCount.value,
      cacheRetentionStats.value?.total ?? cacheRetentionTasks.value.length,
    ),
    tone: "blue",
    updated: formatRelativeTimeAgo(latestCacheRefresh.value, "从未刷新"),
  },
  {
    title: "STRM 任务",
    icon: "fa-film",
    count: strmTasks.value.length,
    enabled: enabledStrmCount.value,
    detail: `已生成 ${generatedStrmCount.value} 个播放文件`,
    progress: taskProgress(enabledStrmCount.value, strmTasks.value.length),
    tone: "purple",
    updated: formatRelativeTimeAgo(latestStrmScan.value, "从未扫描"),
  },
  {
    title: "目录整理",
    icon: "fa-wand-magic-sparkles",
    count: organizeTasks.value.length,
    enabled: enabledOrganizeCount.value,
    detail: organizeTaskDetail.value,
    progress: taskProgress(enabledOrganizeCount.value, organizeTasks.value.length),
    tone: "amber",
    updated: formatRelativeTimeAgo(latestOrganizeRun.value, "从未执行"),
  },
]);

const organizeTaskDetail = computed(() => {
  const failed = organizeTasks.value.filter((task) => (task.last_run_result?.failed ?? 0) > 0).length;
  if (failed > 0) return `${failed} 个任务最近有失败项`;
  const renamed = organizeTasks.value.reduce((sum, task) => sum + (task.last_run_result?.renamed ?? 0), 0);
  return renamed > 0 ? `最近整理 ${renamed} 个条目` : "可预览后手动确认执行";
});

async function loadOverview() {
  const firstLoad = !hasLoadedOverview.value;
  const sequence = ++overviewLoadSequence;
  const errors: unknown[] = [];
  loading.value = firstLoad;
  refreshing.value = !firstLoad;
  loadError.value = "";
  const requests = [
    loadOverviewPart(sequence, accountsApi.list(), (value) => {
      accounts.value = value;
    }, errors),
    loadOverviewPart(sequence, fetchStrmTasks(), (value) => {
      strmTasks.value = value;
    }, errors),
    loadOverviewPart(sequence, fetchCacheRetentionTasks(), (value) => {
      cacheRetentionTasks.value = value.items ?? [];
    }, errors),
    loadOverviewPart(sequence, fetchCacheRetentionStats(), (value) => {
      cacheRetentionStats.value = value;
    }, errors),
    loadOverviewPart(sequence, fetchFuseMounts(), (value) => {
      fuseMounts.value = value;
    }, errors),
    loadOverviewPart(sequence, fetchMediaOrganizeTasks(), (value) => {
      organizeTasks.value = value;
    }, errors),
    loadOverviewPart(sequence, fetchCacheStats(), (value) => {
      cacheStats.value = value;
    }, errors),
    loadOverviewPart(sequence, fetchNotifications({ limit: 1, offset: 0 }), (value) => {
      notifications.value = value.items ?? [];
    }, errors),
    loadOverviewPart(sequence, fetchUnreadCount(), (value) => {
      unreadCount.value = value.count ?? 0;
    }, errors),
    loadOverviewPart(sequence, logsApi().stats(), (value) => {
      logStats.value = value;
    }, errors),
  ];
  const settled = Promise.allSettled(requests);

  await revealOverviewWhenReady(settled);
  if (sequence === overviewLoadSequence) {
    hasLoadedOverview.value = true;
    loading.value = false;
    refreshing.value = false;
  }

  void settled.then(() => {
    if (sequence !== overviewLoadSequence || errors.length === 0) return;
    loadError.value = getApiErrorMessage(errors[0], "部分运行概况加载失败，已保留可用数据");
  });
}

async function loadOverviewPart<T>(
  sequence: number,
  request: Promise<T>,
  assign: (value: T) => void,
  errors: unknown[],
) {
  try {
    const value = await request;
    if (sequence === overviewLoadSequence) assign(value);
  } catch (error) {
    if (sequence === overviewLoadSequence) errors.push(error);
  }
}

function revealOverviewWhenReady(requests: Promise<unknown>) {
  return new Promise<void>((resolve) => {
    let resolved = false;
    let timer: number | undefined;
    const finish = () => {
      if (resolved) return;
      resolved = true;
      if (timer !== undefined) window.clearTimeout(timer);
      resolve();
    };
    timer = window.setTimeout(finish, OVERVIEW_REVEAL_DEADLINE_MS);
    void requests.finally(finish);
  });
}

async function clearDashboardCache() {
  clearingCache.value = true;
  try {
    const res = await clearCache();
    toast.success(`已清空 ${res.cleared_count} 条缓存`);
    cacheStats.value = await fetchCacheStats();
  } catch (e) {
    toast.error(getApiErrorMessage(e, "清空缓存失败"));
  } finally {
    clearingCache.value = false;
  }
}

function openErrorLogs() {
  if (!canJumpToErrorLogs.value) return;
  logPresetLevel.value = 40;
  logPresetSeq.value += 1;
  setActiveTab(LOGS_TAB);
}

function handleLogStatsAcked(next: LogStats) {
  logStats.value = next;
}

function normalizeStatus(status?: string) {
  return (status || "").trim().toLowerCase();
}

function normalizeAuthStatus(account: Account) {
  return normalizeStatus(account.auth_status);
}

function isAccountAuthError(account: Account) {
  return account.is_active && ["token_expired", "failed"].includes(normalizeAuthStatus(account));
}

function isAccountCooldown(account: Account) {
  return account.is_active && normalizeAuthStatus(account) === "cooldown";
}

function isCacheTaskEnabled(task: CacheRetentionTask): boolean {
  return normalizeStatus(task.status) === "running";
}

function isStrmTaskEnabled(task: StrmTask): boolean {
  const status = normalizeStatus(task.status);
  return status === "active" || status === "running";
}

function isOrganizeTaskEnabled(task: MediaOrganizeTask): boolean {
  return normalizeStatus(task.status) !== "paused";
}

function taskProgress(enabled: number, total: number) {
  if (enabled <= 0 || total <= 0) return 0;
  return Math.max(8, Math.min(100, Math.round((enabled / total) * 100)));
}

function latestTime(values: Array<string | undefined>) {
  let latest = 0;
  for (const value of values) {
    if (!value) continue;
    const time = new Date(value).getTime();
    if (!Number.isNaN(time) && time > latest) latest = time;
  }
  return latest > 0 ? new Date(latest).toISOString() : "";
}

function parseAccountConfig(account: Account): Record<string, unknown> {
  if (!account.config) return {};
  try {
    const parsed = JSON.parse(account.config);
    return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : {};
  } catch {
    return {};
  }
}

function downloadModeLabel(account: Account) {
  const config = parseAccountConfig(account);
  const mode = String(config.download_mode ?? config.downloadMode ?? "").toLowerCase();
  const driverType = account.driver_type.toLowerCase();
  if (mode === "proxy") return "本机代理";
  if (mode === "redirect") return "302 直链";
  if (driverType.includes("baidu") || driverType.includes("quark")) return "本机代理";
  return "302 直链";
}

function downloadModeIcon(account: Account) {
  return downloadModeLabel(account) === "本机代理" ? "fa-rotate" : "fa-bolt";
}

function accountRowStyle(account: Account) {
  const color = normalizeHexColor(account.driver_card_color) || "#4c74df";
  return {
    "--account-color": color,
    "--account-soft": hexToRgba(color, 0.15),
    "--account-faint": hexToRgba(color, 0.045),
  };
}

function accountStatusClass(account: Account) {
  if (isAccountAuthError(account)) return "is-auth-error";
  if (isAccountCooldown(account)) return "is-cooldown";
  if (!account.is_active) return "is-disabled";
  return "is-active";
}

function accountStatusIcon(account: Account) {
  if (isAccountAuthError(account)) return "fa-triangle-exclamation";
  if (isAccountCooldown(account)) return "fa-clock";
  if (!account.is_active) return "fa-circle-pause";
  return "fa-circle-check";
}

function accountStatusLabel(account: Account) {
  if (isAccountAuthError(account)) return "失效";
  if (isAccountCooldown(account)) return "认证冷却中";
  if (!account.is_active) return "已禁用";
  return "正常";
}

function driverLabel(account: Account) {
  return account.driver_card_name || account.driver_type;
}

function accountSubline(account: Account) {
  return `${account.driver_type}${account.is_default ? " · 默认账号" : ""}`;
}

function fallbackLogoText(account: Account) {
  return (driverLabel(account).trim()[0] || "L").toUpperCase();
}

function normalizeHexColor(color?: string) {
  const raw = (color || "").trim();
  if (/^#[0-9a-fA-F]{6}$/.test(raw)) return raw;
  if (/^#[0-9a-fA-F]{3}$/.test(raw)) {
    const [, r, g, b] = raw;
    return `#${r}${r}${g}${g}${b}${b}`;
  }
  return "";
}

function hexToRgba(hex: string, alpha: number) {
  const normalized = normalizeHexColor(hex);
  if (!normalized) return `rgba(76, 116, 223, ${alpha})`;
  const value = Number.parseInt(normalized.slice(1), 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function notificationLevelClass(level: string) {
  const normalized = level.toLowerCase();
  if (normalized.includes("error") || normalized.includes("danger")) return "is-error";
  if (normalized.includes("warn")) return "is-warn";
  return "is-info";
}

onMounted(() => {
  void loadOverview();
});
</script>

<template>
  <div class="dashboard-page admin-tabbed-page">
    <SectionTabBar :model-value="activeTab" :tabs="tabs" @update:model-value="setActiveTab" />

    <div v-if="activeTab === OVERVIEW_TAB && !loading" class="dashboard-overview">
      <section
        class="dashboard-hero"
        :class="[`dashboard-hero--${systemStatus.tone}`, { 'dashboard-hero--actionable': canJumpToErrorLogs }]"
        :role="canJumpToErrorLogs ? 'button' : undefined"
        :tabindex="canJumpToErrorLogs ? 0 : undefined"
        :aria-label="canJumpToErrorLogs ? '查看错误日志' : undefined"
        @click="openErrorLogs"
        @keydown.enter.prevent="openErrorLogs"
        @keydown.space.prevent="openErrorLogs"
      >
        <div class="dashboard-hero__main">
          <div class="dashboard-hero__icon">
            <i class="fas" :class="systemStatus.icon" />
          </div>
          <div class="dashboard-hero__copy">
            <p class="dashboard-eyebrow">控制台</p>
            <h2>{{ systemStatus.label }}</h2>
            <p class="dashboard-hero__detail">{{ systemStatusText }}</p>
          </div>
        </div>
        <div class="dashboard-hero__metrics" aria-label="运行概况指标">
          <div class="hero-metric">
            <strong>{{ accountCount }}</strong>
            <span>接入</span>
          </div>
          <div class="hero-metric is-green">
            <strong>{{ activeAccountCount }}</strong>
            <span>在线</span>
          </div>
          <div class="hero-metric">
            <strong>{{ enabledTaskCount }}</strong>
            <span>运行任务</span>
          </div>
          <div class="hero-metric" :class="{ 'is-warn': recentErrorCount > 0 }">
            <strong>{{ recentErrorCount }}</strong>
            <span>待确认错误</span>
          </div>
        </div>
      </section>

      <div v-if="loadError" class="dashboard-warning">
        <i class="fas fa-circle-info" />
        <span>{{ loadError }}</span>
        <button type="button" :disabled="refreshing" @click="loadOverview">
          {{ refreshing ? "刷新中..." : "重试" }}
        </button>
      </div>

      <section class="overview-cards" aria-label="运行概况卡片">
        <article class="overview-card">
          <div class="overview-card__icon">
            <i class="fas fa-folder-tree" />
          </div>
          <div>
            <strong>{{ mountedFuseCount }}/{{ totalFuseCount }}</strong>
            <span>FUSE 挂载点</span>
          </div>
        </article>
        <article class="overview-card">
          <div class="overview-card__icon">
            <i class="fas fa-list-check" />
          </div>
          <div>
            <strong>{{ totalTaskCount }}</strong>
            <span>任务总数</span>
          </div>
        </article>
        <article class="overview-card overview-card--cache">
          <div class="overview-card__icon">
            <i class="fas fa-database" />
          </div>
          <div>
            <strong>{{ cacheSizeLabel }}</strong>
            <span>缓存空间</span>
          </div>
          <AppCardActionButton
            class="overview-card__action-layout"
            icon-class="fas fa-trash-can"
            label="清理"
            variant="danger"
            :disabled="clearingCache"
            @click="clearDashboardCache"
          />
        </article>
        <article class="overview-card">
          <div class="overview-card__icon">
            <i class="fas fa-bell" />
          </div>
          <div>
            <strong>{{ unreadCount }}</strong>
            <span>未读通知</span>
          </div>
        </article>
      </section>

      <section class="dashboard-layout">
        <article class="dashboard-panel dashboard-panel--accounts">
          <header class="dashboard-panel__head">
            <div>
              <h3>存储账号</h3>
              <p>{{ accountCount }} 个接入 · {{ activeAccountCount }} 个在线</p>
            </div>
            <button type="button" class="dashboard-link-button" :disabled="refreshing" @click="loadOverview">
              <i class="fas fa-rotate-right" :class="{ 'is-spinning': refreshing }" />
              刷新
            </button>
          </header>

          <div v-if="sortedAccounts.length" class="account-list">
            <div
              v-for="account in sortedAccounts"
              :key="account.id"
              class="account-row"
              :class="{
                'is-disabled': !account.is_active,
                'is-auth-error': isAccountAuthError(account),
                'is-cooldown': isAccountCooldown(account),
              }"
              :style="accountRowStyle(account)"
            >
              <img
                v-if="account.driver_card_logo"
                class="account-logo"
                :src="account.driver_card_logo"
                :alt="driverLabel(account)"
              />
              <div v-else class="account-logo account-logo--text">{{ fallbackLogoText(account) }}</div>
              <div class="account-row__main">
                <strong>
                  {{ account.name }}
                  <span v-if="account.is_default" class="default-tag">默认</span>
                </strong>
                <small>{{ accountSubline(account) }}</small>
              </div>
              <span class="method-tag">
                <i class="fas" :class="downloadModeIcon(account)" />
                {{ downloadModeLabel(account) }}
              </span>
              <span
                class="status-tag"
                :class="accountStatusClass(account)"
                :title="accountStatusLabel(account)"
              >
                <i class="fas" :class="accountStatusIcon(account)" />
                {{ accountStatusLabel(account) }}
              </span>
            </div>
          </div>
          <div v-else class="panel-empty">还没有添加存储账号</div>
        </article>

        <aside class="dashboard-side">
          <article class="dashboard-panel">
            <header class="dashboard-panel__head">
            <div>
              <h3>后台任务</h3>
              <p>{{ totalTaskCount }} 个任务 · {{ enabledTaskCount }} 个运行中</p>
            </div>
          </header>

            <div class="task-list">
              <div v-for="task in taskSummaries" :key="task.title" class="task-row">
                <div class="task-row__icon" :class="`task-row__icon--${task.tone}`">
                  <i class="fas" :class="task.icon" />
                </div>
                <div class="task-row__main">
                  <div class="task-row__title">
                    <strong>{{ task.title }}</strong>
                    <span>{{ task.count }} 个</span>
                  </div>
                  <div class="task-progress" aria-hidden="true">
                    <span :style="{ width: `${task.progress}%` }" />
                  </div>
                  <small>{{ task.detail }} · {{ task.updated }}</small>
                </div>
              </div>
            </div>
          </article>

          <article class="dashboard-panel">
            <header class="dashboard-panel__head">
              <div>
                <h3>日志与通知</h3>
                <p>近 24 小时</p>
              </div>
            </header>

            <div class="log-snapshot">
              <div>
                <strong>{{ logStats?.total ?? 0 }}</strong>
                <span>日志总数</span>
              </div>
              <div>
                <strong>{{ unreadCount }}</strong>
                <span>未读通知</span>
              </div>
            </div>

            <!-- 多条未读通知聚合为一张卡片，避免面板被逐条渲染拉长；仅最新一条做摘要。 -->
            <div v-if="unreadCount > 0" class="notice-list">
              <div
                class="notice-row"
                :class="notificationLevelClass(notifications[0]?.level ?? 'info')"
              >
                <i class="fas fa-bell" />
                <div>
                  <strong>有 {{ unreadCount }} 条未读通知</strong>
                  <small v-if="notifications.length">
                    {{ notifications[0].title }} · {{ formatRelativeTimeAgo(notifications[0].created_at, "") }}
                  </small>
                  <small v-else>点击右上角铃铛查看</small>
                </div>
              </div>
            </div>
            <div v-else class="notice-good">
              <i class="fas fa-check" />
              <div>
                <strong>通知状态正常</strong>
                <small>暂无未处理通知</small>
              </div>
            </div>
          </article>
        </aside>
      </section>
    </div>

    <SystemLogs
      v-else-if="activeTab === LOGS_TAB"
      :preset-level="logPresetLevel"
      :preset-seq="logPresetSeq"
      @acked-errors="handleLogStatsAcked"
    />
  </div>
</template>

<style scoped>
.dashboard-page {
  padding-bottom: 24px;
}

.dashboard-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dashboard-hero,
.overview-card,
.dashboard-panel {
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow-soft);
}

.dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 20px;
  padding: 18px 22px;
  background: linear-gradient(180deg, var(--surface), color-mix(in srgb, var(--brand) 4%, var(--surface)));
}

.dashboard-hero--actionable {
  cursor: pointer;
  transition:
    transform 0.16s ease,
    box-shadow 0.16s ease,
    border-color 0.16s ease;
}

.dashboard-hero--actionable:hover,
.dashboard-hero--actionable:focus-visible {
  transform: translateY(-1px);
  box-shadow: var(--shadow-medium);
  border-color: color-mix(in srgb, var(--warning) 24%, var(--border-soft));
  outline: none;
}

.dashboard-hero--warn {
  background: linear-gradient(180deg, var(--surface), color-mix(in srgb, var(--warning) 7%, var(--surface)));
}

.dashboard-hero--danger {
  background: linear-gradient(180deg, var(--surface), color-mix(in srgb, var(--danger) 8%, var(--surface)));
}

.dashboard-hero__main {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.dashboard-hero__icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: var(--radius-md);
  border: 1px solid color-mix(in srgb, var(--success) 22%, var(--border));
  background: color-mix(in srgb, var(--success) 8%, var(--surface));
  color: var(--success);
  font-size: 16px;
}

.dashboard-hero--warn .dashboard-hero__icon {
  border-color: color-mix(in srgb, var(--warning) 28%, var(--border));
  background: color-mix(in srgb, var(--warning) 10%, var(--surface));
  color: var(--warning);
}

.dashboard-hero--danger .dashboard-hero__icon {
  border-color: color-mix(in srgb, var(--danger) 28%, var(--border));
  background: color-mix(in srgb, var(--danger) 10%, var(--surface));
  color: var(--danger);
}

.dashboard-hero__copy {
  min-width: 0;
}

.dashboard-eyebrow {
  margin: 0 0 3px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
}

.dashboard-hero h2,
.dashboard-panel h3 {
  margin: 0;
  color: var(--text);
}

.dashboard-hero h2 {
  font-size: 17px;
  line-height: 1.3;
}

.dashboard-hero p {
  margin: 0;
}

.dashboard-hero__detail {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.dashboard-hero__metrics {
  display: grid;
  grid-template-columns: repeat(4, 86px);
  gap: 8px;
}

.hero-metric {
  min-width: 74px;
  padding-left: 12px;
  border-left: 1px solid var(--border);
}

.hero-metric strong {
  display: block;
  color: var(--text);
  font-size: 20px;
  line-height: 1.15;
}

.hero-metric span {
  color: var(--text-muted);
  font-size: 12px;
}

.hero-metric.is-green strong {
  color: var(--success);
}

.hero-metric.is-warn strong {
  color: var(--warning);
}

.dashboard-warning {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: 1px solid color-mix(in srgb, var(--warning) 32%, var(--border));
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--warning) 10%, var(--surface));
  color: var(--text);
  font-size: 13px;
}

.dashboard-warning span {
  flex: 1;
  min-width: 0;
}

.dashboard-warning button,
.dashboard-link-button {
  border: 0;
  background: transparent;
  color: var(--brand);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.dashboard-warning button:disabled,
.dashboard-link-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.overview-card {
  min-height: 96px;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  align-items: center;
  gap: 13px;
  padding: 18px 20px;
  background: linear-gradient(180deg, var(--surface), color-mix(in srgb, var(--brand) 3%, var(--surface)));
}

.overview-card--cache {
  grid-template-columns: 46px minmax(0, 1fr) auto;
}

.overview-card__icon {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  border: 1px solid color-mix(in srgb, var(--brand) 14%, var(--border));
  background: color-mix(in srgb, var(--brand) 8%, var(--surface));
  color: var(--brand);
  font-size: 16px;
}

.overview-card:nth-child(2) .overview-card__icon {
  border-color: color-mix(in srgb, var(--success) 18%, var(--border));
  background: color-mix(in srgb, var(--success) 8%, var(--surface));
  color: var(--success);
}

.overview-card:nth-child(3) .overview-card__icon {
  border-color: color-mix(in srgb, var(--warning) 18%, var(--border));
  background: color-mix(in srgb, var(--warning) 9%, var(--surface));
  color: var(--warning);
}

.overview-card:nth-child(4) .overview-card__icon {
  border-color: color-mix(in srgb, #8b5cf6 18%, var(--border));
  background: color-mix(in srgb, #8b5cf6 8%, var(--surface));
  color: #8b5cf6;
}

.overview-card strong {
  display: block;
  color: var(--text);
  font-size: 24px;
  line-height: 1.05;
  margin-bottom: 7px;
}

.overview-card span {
  display: block;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.3;
}

.overview-card__action-layout {
  justify-self: end;
}

.dashboard-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(360px, 0.55fr);
  gap: 16px;
}

.dashboard-panel {
  padding: 20px;
}

.dashboard-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.dashboard-panel__head h3 {
  display: flex;
  align-items: center;
  font-size: 15px;
  font-weight: 800;
}

.dashboard-panel__head h3::before {
  display: none;
}

.dashboard-panel__head p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 12px;
}

.dashboard-link-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
}

.is-spinning {
  animation: dashboard-spin 0.9s linear infinite;
}

.account-list,
.dashboard-side,
.task-list,
.notice-list {
  display: grid;
  gap: 10px;
}

.account-list {
  max-height: 532px;
  overflow-x: hidden;
  overflow-y: auto;
}

.account-row {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 0;
  border-radius: var(--radius-md);
  background:
    linear-gradient(
      90deg,
      var(--account-soft),
      color-mix(in srgb, var(--surface) 88%, var(--account-color)) 52%,
      var(--surface)
    ),
    var(--surface);
}

.account-row:nth-child(2n) {
  background:
    linear-gradient(
      90deg,
      var(--account-soft),
      color-mix(in srgb, var(--surface) 92%, var(--account-color)) 58%,
      var(--surface)
    ),
    var(--surface);
}

.account-row.is-disabled {
  opacity: 0.86;
}

.account-row.is-auth-error {
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--danger) 24%, transparent);
  background:
    linear-gradient(
      90deg,
      color-mix(in srgb, var(--danger) 13%, var(--surface)),
      color-mix(in srgb, var(--surface) 90%, var(--danger)) 52%,
      var(--surface)
    ),
    var(--surface);
}

.account-row.is-cooldown {
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--warning) 22%, transparent);
}

.account-logo {
  width: 42px;
  height: 42px;
  object-fit: contain;
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--surface) 55%, transparent);
}

.account-logo--text {
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, var(--account-color), rgba(17, 168, 232, 0.88));
  color: #fff;
  font-weight: 800;
}

.account-row__main {
  min-width: 0;
}

.account-row__main strong {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: var(--text);
  font-size: 14px;
}

.account-row__main small {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.default-tag {
  height: 20px;
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  padding: 0 7px;
  border-radius: var(--radius-pill);
  background: color-mix(in srgb, var(--brand) 10%, var(--surface));
  color: var(--brand);
  font-size: 11px;
  font-weight: 800;
}

.method-tag,
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.method-tag {
  color: var(--text-muted);
}

.method-tag i {
  color: var(--account-color);
  font-size: 11px;
}

.status-tag {
  color: var(--success);
}

.status-tag.is-disabled {
  color: var(--warning);
}

.status-tag.is-cooldown {
  color: var(--warning);
}

.status-tag.is-auth-error {
  color: var(--danger);
}

.panel-empty {
  display: grid;
  place-items: center;
  min-height: 180px;
  border: 1px dashed var(--border-soft);
  border-radius: var(--radius-md);
  color: var(--text-muted);
  font-size: 13px;
}

.task-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-soft);
}

.task-row:last-child {
  border-bottom: 0;
}

.task-row__icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--brand) 8%, var(--surface));
  color: var(--brand);
}

.task-row__icon--purple {
  background: color-mix(in srgb, #8b5cf6 12%, var(--surface));
  color: #8b5cf6;
}

.task-row__icon--amber {
  background: color-mix(in srgb, var(--warning) 10%, var(--surface));
  color: var(--warning);
}

.task-row__main {
  min-width: 0;
}

.task-row__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.task-row__title strong {
  color: var(--text);
  font-size: 14px;
}

.task-row__title span,
.task-row small {
  color: var(--text-muted);
  font-size: 12px;
}

.task-progress {
  height: 4px;
  margin: 8px 0 6px;
  overflow: hidden;
  border-radius: var(--radius-pill);
  background: var(--border-soft);
}

.task-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--brand-gradient-h);
}

.log-snapshot {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}

.log-snapshot > div {
  padding: 14px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
}

.log-snapshot strong {
  display: block;
  color: var(--text);
  font-size: 22px;
  line-height: 1.1;
}

.log-snapshot span {
  color: var(--text-muted);
  font-size: 12px;
}

.notice-row,
.notice-good {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
}

.notice-row > i,
.notice-good > i {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--brand) 10%, var(--surface));
  color: var(--brand);
}

.notice-row.is-warn > i {
  background: color-mix(in srgb, var(--warning) 10%, var(--surface));
  color: var(--warning);
}

.notice-row.is-error > i {
  background: color-mix(in srgb, var(--danger) 10%, var(--surface));
  color: var(--danger);
}

.notice-row strong,
.notice-good strong {
  display: block;
  color: var(--text);
  font-size: 13px;
  line-height: 1.4;
}

.notice-row small,
.notice-good small {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 12px;
}

.notice-good {
  background: color-mix(in srgb, var(--success) 10%, var(--surface));
  border-color: color-mix(in srgb, var(--success) 22%, var(--border));
}

.notice-good > i {
  background: var(--surface);
  color: var(--success);
}

@keyframes dashboard-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1180px) {
  .overview-cards,
  .dashboard-hero__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .dashboard-hero,
  .dashboard-layout {
    grid-template-columns: 1fr;
  }

  .overview-cards {
    grid-template-columns: 1fr;
  }

  .dashboard-hero__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
    gap: 10px;
  }

  .hero-metric {
    min-width: 0;
    padding: 10px 12px;
    border-left: 0;
    border-radius: var(--radius-sm);
    background: var(--surface-sunken);
  }

  .account-row {
    grid-template-columns: 42px minmax(0, 1fr);
  }

  .overview-card--cache {
    grid-template-columns: 46px minmax(0, 1fr);
  }

  .overview-card__action-layout {
    grid-column: 2;
    justify-self: start;
  }

  .method-tag,
  .status-tag {
    justify-self: start;
  }
}
</style>
