<template>
  <div class="cross-transfer">
    <div class="transfer-shell">
      <div class="transfer-topbar">
        <div class="tb-side tb-src">
          <span class="logo-chip s26"><img v-if="srcPan.logo" :src="srcPan.logo" :alt="srcPan.name" @error="hideImg"></span>
          <div class="tb-title">
            <span>{{ srcPan.name || '源网盘' }}</span>
            <small>读取文件指纹</small>
          </div>
          <span class="panel-role">源</span>
        </div>
        <div class="tb-mid">
          <button
            v-if="routeBidirectional"
            type="button"
            class="tb-swap"
            title="交换源与目标"
            @click="swap"
          >
            <i class="fas fa-right-left"></i>
          </button>
          <span v-else class="tb-flow" title="单向线路，不可交换">
            <i class="fas fa-arrow-right-long"></i>
          </span>
          <span v-if="routeBidirectional" class="tb-swap-hint">可交换</span>
        </div>
        <div class="tb-side tb-dst">
          <span class="panel-role dst-role">目标</span>
          <div class="tb-title tb-title-dst">
            <span>{{ dstPan.name || '目标网盘' }}</span>
            <small>秒传命中后转存</small>
          </div>
          <span class="logo-chip s26"><img v-if="dstPan.logo" :src="dstPan.logo" :alt="dstPan.name" @error="hideImg"></span>
        </div>
      </div>

      <div class="transfer-body">
      <div class="panel src">
        <div class="panel-pick">
          <button class="combo" @click="openPicker('src')">
            <span class="c-ic"><i class="fas fa-hdd"></i></span>
            <span class="c-text" :class="{ placeholder: !src }" :title="srcPickerTitle">{{ srcPickerText }}</span>
            <span class="c-caret"><i class="fas fa-chevron-down"></i></span>
          </button>
        </div>
        <div class="tree tree-host" ref="srcTreeRef">
          <div v-if="scanSummary && !phaseStatus" class="tree-scan-banner" :class="{ warn: scanSummary.warn }">
            <i class="fas" :class="scanSummary.warn ? 'fa-triangle-exclamation' : 'fa-circle-check'"></i>
            <span>{{ scanSummary.text }}</span>
          </div>
          <CrossTransferTree v-if="srcTree && srcTree.length" :nodes="srcTree" mode="src" :depth="0" />
          <div v-else-if="!phaseStatus" class="tree-empty">选择源目录后，扫描/试探会在此显示文件与秒传状态</div>
          <div v-if="phaseStatus && (!srcTree || !srcTree.length)" class="tree-phase-fill">
            <div class="tree-phase-card">
              <BusySpinner class="tree-phase-spin" :size="22" color="var(--primary-color)" />
              <p class="tree-phase-title">{{ phaseStatus }}</p>
              <p v-if="isScanPhase" class="tree-phase-sub">{{ isBaiduMd5Route ? '扫描仅列目录，指纹在试探阶段从下载响应头获取' : '子目录较多时需等待片刻，请勿关闭页面' }}</p>
              <div v-if="isScanPhase" class="tree-phase-bar"><div class="tree-phase-bar-indeterminate"></div></div>
            </div>
          </div>
        </div>
      </div>

      <div class="panel dst">
        <div class="panel-pick">
          <button class="combo" @click="openPicker('dst')">
            <span class="c-ic"><i class="fas fa-hdd"></i></span>
            <span class="c-text" :class="{ placeholder: !dst }">{{ dst ? (dst.accName + ' · ' + dst.path) : '选择账号 · 目录' }}</span>
            <span class="c-caret"><i class="fas fa-chevron-down"></i></span>
          </button>
        </div>
        <div class="tree">
          <div v-if="!dstTree || !dstTree.length" class="tree-empty">秒传完成后显示已转存文件</div>
          <CrossTransferTree v-else :nodes="dstTree" mode="dst" :depth="0" />
        </div>
      </div>
      </div>
    </div>

    <div class="ct-footer">
      <div class="ct-footer-bar">
        <div class="ct-footer-left">
          <div class="ft-stats">
            <span class="ft-item"><span class="n">{{ metrics.total }}</span><span class="l">扫描</span></span>
            <span class="ft-sep" aria-hidden="true"></span>
            <span class="ft-item"><span class="n ok">{{ metrics.ok }}</span><span class="l">可秒传</span></span>
            <span class="ft-sep" aria-hidden="true"></span>
            <span class="ft-item"><span class="n no">{{ metrics.no }}</span><span class="l">不可</span></span>
            <span class="ft-sep" aria-hidden="true"></span>
            <span class="ft-item"><span class="n">{{ metrics.done }}</span><span class="l">已转存</span></span>
            <template v-if="relayNotice">
              <span class="ft-sep" aria-hidden="true"></span>
              <span class="ft-item"><span class="n relay">{{ relayNotice.relayQueued }}</span><span class="l">兜底排队</span></span>
            </template>
          </div>
        </div>

        <div class="ct-footer-center">
          <div v-if="showProgressBar" class="ft-center-progress">
            <p v-if="running === 'probe'" class="ft-prog-hint">正在检测目标盘；支持预判时不会实际转存</p>
            <div class="ft-prog-row">
              <div class="ft-track"><i :style="{ width: barWidth + '%' }"></i></div>
              <span class="ft-pct">{{ barWidth }}%</span>
            </div>
          </div>
          <div
            v-else-if="showFooterScrollTips"
            class="ct-footer-scroll-hint"
            :class="{ 'is-clickable': currentFooterTip.action === 'probe-notice' }"
            @click="onFooterTipClick"
          >
            <transition name="ct-tip-fade" mode="out-in">
              <span :key="footerTipIndex" class="ct-footer-scroll-text">
                <i class="fas fa-circle-info"></i>
                {{ currentFooterTip.text }}
              </span>
            </transition>
          </div>
          <a
            v-else-if="relayNotice"
            class="ct-relay-inline-hint"
            :href="relayTasksHref"
            target="_blank"
            rel="noopener"
          >
            <i class="fas fa-circle-info"></i>
            <span>点击查看兜底传输跨盘任务进度</span>
            <i class="fas fa-arrow-up-right-from-square ct-relay-inline-arrow"></i>
          </a>
        </div>

        <div class="footer-island">
          <div ref="settingsMenuRef" class="ct-settings-menu">
            <button
              ref="settingsTriggerRef"
              type="button"
              class="ct-settings-trigger"
              title="传输设置"
              @click="toggleSettingsMenu"
            >
              <i class="fas fa-sliders"></i>
            </button>
            <Teleport to="body">
              <div
                v-if="settingsOpen"
                ref="settingsDropdownRef"
                class="ct-settings-dropdown ct-settings-dropdown-portal"
                :style="settingsDropdownStyle"
              >
                <div class="ct-settings-panel">
                  <div class="ct-settings-block">
                    <div class="ct-settings-label">冲突策略</div>
                    <div class="ct-settings-seg" role="group" aria-label="冲突策略">
                      <button
                        type="button"
                        class="ct-settings-opt"
                        :class="{ active: effectiveConflict === 'skip' }"
                        :disabled="targetSkipUnsupported"
                        :title="targetSkipUnsupported ? `${dstName}不支持跳过` : '目标已有同名文件时不再传输'"
                        @click="targetSkipUnsupported ? null : (conflict = 'skip')"
                      >跳过</button>
                      <button
                        type="button"
                        class="ct-settings-opt"
                        :class="{ active: effectiveConflict === 'rename' }"
                        :disabled="targetRenameUnsupported"
                        :title="targetRenameUnsupported ? `${dstName}不支持自动重命名` : ''"
                        @click="targetRenameUnsupported ? null : (conflict = 'rename')"
                      >重命名</button>
                      <button
                        type="button"
                        class="ct-settings-opt"
                        :class="{ active: effectiveConflict === 'overwrite' }"
                        :disabled="targetOverwriteUnsupported"
                        :title="targetOverwriteUnsupported ? `${dstName}不支持覆盖` : ''"
                        @click="targetOverwriteUnsupported ? null : (conflict = 'overwrite')"
                      >覆盖</button>
                    </div>
                    <p v-if="effectiveConflict === 'skip'" class="ct-settings-fallback-hint">
                      同名文件不再传输。
                    </p>
                    <p v-else-if="effectiveConflict === 'rename'" class="ct-settings-fallback-hint">
                      同名文件自动改名。
                    </p>
                    <p v-else-if="effectiveConflict === 'overwrite'" class="ct-settings-fallback-hint">
                      同名文件直接覆盖。
                    </p>
                    <p v-else-if="targetOverwriteUnsupported" class="ct-settings-fallback-hint">
                      {{ dstName }}不支持覆盖，同名文件将自动重命名。
                    </p>
                    <p v-else-if="targetRenameUnsupported" class="ct-settings-fallback-hint">
                      {{ dstName }}不支持自动重命名，同名文件将被覆盖。
                    </p>
                  </div>
                  <div class="ct-settings-block">
                    <div class="ct-settings-label">兜底传输</div>
                    <div class="ct-settings-seg" role="group" aria-label="兜底传输">
                      <button
                        type="button"
                        class="ct-settings-opt"
                        :class="{ active: fallback === 'off' }"
                        @click="fallback = 'off'"
                      >关闭</button>
                      <button
                        type="button"
                        class="ct-settings-opt"
                        :class="{ active: fallback === 'on' }"
                        @click="fallback = 'on'"
                      >开启</button>
                    </div>
                    <p class="ct-settings-fallback-hint">
                      {{ fallback === 'on' ? '未命中时中转上传。' : '只执行秒传匹配。' }}
                    </p>
                  </div>
                </div>
              </div>
            </Teleport>
          </div>
          <button
            class="ct-btn"
            :class="running === 'probe' ? 'ct-btn-danger' : 'ct-btn-primary'"
            :disabled="running === 'probe' ? false : !canProbe"
            @click="running === 'probe' ? stopRun() : probe()"
          >
            <i :class="running === 'probe' ? 'fas fa-stop' : 'fas fa-magnifying-glass'"></i>
            {{ running === 'probe' ? '停止试探' : '试探秒传' }}
          </button>
          <button
            class="ct-btn"
            :class="running === 'exec' ? 'ct-btn-danger' : 'ct-btn-go'"
            :disabled="running === 'exec' ? false : !canStart"
            @click="running === 'exec' ? stopRun() : start()"
          >
            <i :class="running === 'exec' ? 'fas fa-stop' : 'fas fa-bolt'"></i>
            {{ running === 'exec' ? '停止' : '开始传输' }}
          </button>
        </div>
      </div>
    </div>

    <FolderPickerModal
      :open="pickerOpen"
      selectable-account
      :accounts="pickerAccounts"
      :account-id="pickerInitialAccountId"
      :initial-path="pickerInitialPath"
      :multi-select="pickerMode === 'src'"
      :initial-location-mode="pickerMode === 'src' ? 'root' : 'preserve'"
      :selection-restore-mode="pickerMode === 'src' ? 'reset' : 'preserve'"
      :title="pickerMode === 'src' ? '选择源目录' : '选择目标目录'"
      :confirm-text="pickerMode === 'src' ? '确认选择' : '选择当前目录'"
      show-refresh
      @close="pickerOpen = false"
      @resolve="onPickerResolve"
    />

    <!-- 线路矩阵弹层：AppModal bare，头部单行 = 标题 + 筛选 + 搜索（对齐 demo） -->
    <AppModal :open="matrixOpen" bare @close="matrixOpen = false">
      <div class="mx-shell">
        <div class="mx-bar">
          <div class="mx-title">秒传星图</div>
          <div class="mx-status">{{ statusText }}</div>
          <button type="button" class="mx-x" title="关闭" @click="matrixOpen = false"><i class="fas fa-xmark"></i></button>
        </div>
        <div class="mx-scroll">
          <div v-if="!routes.length" class="mx-empty">
            <i class="fas fa-filter-circle-xmark"></i>
            <p>没有匹配的线路</p>
            <small>当前暂无可用的秒传组合</small>
          </div>
          <CrossDriveTopologyView
            v-else
            :routes="routes"
            :selected-id="mxSelected ? mxSelected.route.id : null"
            :selected-dir="selectedView ? { from: selectedView.from.driver, to: selectedView.to.driver } : null"
            @select="onMatrixPatchSelect"
            @reselect="mxSelected = null"
          />
        </div>
        <div class="mx-foot">
          <button type="button" class="mx-btn go" :disabled="!mxSelected" @click="applyMatrixSelection">
            使用此线路
          </button>
        </div>
      </div>
    </AppModal>

  </div>
</template>

<script setup>
import {
  ref,
  reactive,
  computed,
  onMounted,
  onUnmounted,
  onActivated,
  onDeactivated,
  nextTick,
  watch,
} from "vue";
import { useRouter } from "vue-router";
import CrossTransferTree from "./CrossTransferTree.vue";
import BusySpinner from "@/components/base/BusySpinner.vue";
import AppModal from "@/components/base/AppModal.vue";
import CrossDriveTopologyView from "./CrossDriveTopologyView.vue";
import FolderPickerModal from "@/components/file/FolderPickerModal.vue";
import { accountsApi } from "@/api/accounts";
import {
  executeCrossTransferStream,
  listCrossTransferRoutes,
  probeCrossTransferStream,
  scanCrossTransferSourceStream,
} from "@/api/crossTransfer";
import { useConfirm } from "@/composables/useConfirm";
import { toast } from "@/composables/useToast";

const { confirm, showConfirm } = useConfirm();

const SOFT_FOLDER_LIMIT = 10
const router = useRouter()

const CT_SETTINGS_STORAGE_KEY = 'litepan:cross-transfer:settings'
const CT_PROBE_NOTICE_KEY = 'litepan:cross-transfer:probe-notice-dismissed'
const FOOTER_TIP_INTERVAL_MS = 6000
const footerScrollTips = [
  { text: '支持预判的网盘只查询命中；其余网盘通过临时目录试传。点击查看说明。', action: 'probe-notice' },
  { text: '建议每次只选一部影片、一季或少量文件夹，子目录多请分批传输。' },
  { text: '大部分网盘接口不返回sha1或其他哈希值，暂时无法匹配秒传方案。' },
]

const routes = ref([])
const activeId = ref('')
const swapped = ref(false)

const src = ref(null)
const dst = ref(null)
const srcTree = ref(null)
const dstTree = ref(null)
const probeFiles = ref([])

const conflict = ref('skip')
const fallback = ref('off')
const settingsOpen = ref(false)
const settingsMenuRef = ref(null)
const settingsTriggerRef = ref(null)
const settingsDropdownRef = ref(null)
const settingsDropdownStyle = ref({})
const SETTINGS_DROPDOWN_WIDTH = 304
const footerTipIndex = ref(0)
let footerTipTimer = null
let uiActive = false
const running = ref('')
const abortCtrl = ref(null)
const barWidth = ref(0)
const metrics = reactive({ total: 0, ok: 0, no: 0, done: 0 })
const relayNotice = ref(null)
const phaseStatus = ref('')
const scanSummary = ref(null)
const scanLimitReason = ref('')

const pickerOpen = ref(false)
const pickerMode = ref('src')
const pickerAccounts = ref([])
const pickerInitialAccountId = ref(null)
const pickerInitialPath = ref('')

const relayTasksHref = computed(() => (
  router.resolve({ path: '/', query: { taskPanel: 'relay' } }).href
))

const showProgressBar = computed(() => Boolean(running.value))
const showFooterScrollTips = computed(() => !showProgressBar.value && !relayNotice.value)
const currentFooterTip = computed(() => footerScrollTips[footerTipIndex.value] || footerScrollTips[0])
const isScanPhase = computed(() => phaseStatus.value.includes('扫描'))
const isBaiduMd5Route = computed(() => curRoute.value?.method === 'md5' && srcDriver.value === 'baidu_open')
const sourceRoots = computed(() => Array.isArray(src.value?.sources) ? src.value.sources : [])
const srcPickerText = computed(() => {
  if (!src.value) return '选择账号 · 目录'
  if (sourceRoots.value.length === 1) return `${src.value.accName} · ${sourceRoots.value[0].path}`
  return `${src.value.accName} · 已选 ${sourceRoots.value.length} 个目录`
})
const srcPickerTitle = computed(() => (
  src.value ? sourceRoots.value.map(item => item.path).join('\n') : ''
))

const accounts = ref([])
const srcTreeRef = ref(null)

const curRoute = computed(() => routes.value.find(r => r.id === activeId.value) || null)
const routeBidirectional = computed(() => !!curRoute.value?.bidirectional)
const srcDriver = computed(() => {
  if (!curRoute.value) return ''
  return swapped.value ? curRoute.value.to.driver : curRoute.value.from.driver
})
const dstDriver = computed(() => {
  if (!curRoute.value) return ''
  return swapped.value ? curRoute.value.from.driver : curRoute.value.to.driver
})
const srcPan = computed(() => panOf(srcDriver.value))
const dstPan = computed(() => panOf(dstDriver.value))

const dstMeta = computed(() => {
  if (!curRoute.value) return null
  return swapped.value ? curRoute.value.from : curRoute.value.to
})
const dstName = computed(() => dstMeta.value?.name || '目标盘')
const dstConflictPolicies = computed(() => {
  const p = dstMeta.value?.conflict_policies
  return Array.isArray(p) && p.length ? p : ['skip', 'rename', 'overwrite']
})
const targetSkipUnsupported = computed(() => !dstConflictPolicies.value.includes('skip'))
const targetOverwriteUnsupported = computed(() => !dstConflictPolicies.value.includes('overwrite'))
const targetRenameUnsupported = computed(() => !dstConflictPolicies.value.includes('rename'))
const effectiveConflict = computed(() => {
  if (conflict.value === 'skip' && targetSkipUnsupported.value) return 'rename'
  if (conflict.value === 'overwrite' && targetOverwriteUnsupported.value) return 'rename'
  if (conflict.value === 'rename' && targetRenameUnsupported.value) return 'overwrite'
  return conflict.value
})

const canProbe = computed(() => !!src.value && !!dst.value && !running.value)
const canStart = computed(() => !!src.value && !!dst.value && !!curRoute.value && !running.value)

function panOf(driver) {
  const r = curRoute.value
  if (!r) return {}
  if (r.from.driver === driver) return r.from
  if (r.to.driver === driver) return r.to
  return {}
}
function accountsFor(driver) {
  return accounts.value.filter(a => a.driver_type === driver && a.is_active !== false)
}

const hideImg = (e) => { e.target.style.display = 'none' }
const notify = (type, msg) => { toast[type](msg) }

function clearRelayNotice() {
  relayNotice.value = null
}

function clearSourceSelection() {
  src.value = null
  srcTree.value = null
  probeFiles.value = []
  scanSummary.value = null
  scanLimitReason.value = ''
  phaseStatus.value = ''
  metrics.total = 0
  metrics.ok = 0
  metrics.no = 0
  metrics.done = 0
}

function buildScanSummary(scan) {
  const files = scan?.total || 0
  const folders = scan?.shallow_dirs || 0
  if (files <= 0) return null
  const warn = Boolean(scan?.truncated) || folders > SOFT_FOLDER_LIMIT
  const pending = (scan?.files || []).filter(f => !f.hash && f.source_file_id).length
  let text = `已扫描 ${files} 个文件`
  if (folders) text += `、${folders} 个子文件夹（一至二级合计）`
  if (pending && isBaiduMd5Route.value) text += `，${pending} 个待试探时计算指纹`
  if (scan?.truncated) {
    text += `。${scan.truncated_reason || '扫描结果不完整'}，已禁止继续试探或传输。`
  } else {
    text += warn ? '。子文件夹较多，扫描较慢，建议缩小范围或分批传输。' : '。'
  }
  return { text, warn }
}

function ensureCompleteScan(scan = null) {
  const reason = scan?.truncated
    ? (scan.truncated_reason || '扫描结果不完整')
    : scanLimitReason.value
  if (!reason) return true
  notify('error', `${reason}，已禁止继续试探或传输，请选择更小的源目录`)
  return false
}

function isProbeNoticeDismissed() {
  try {
    return localStorage.getItem(CT_PROBE_NOTICE_KEY) === '1'
  } catch {
    return false
  }
}

function markProbeNoticeSkipped() {
  try {
    localStorage.setItem(CT_PROBE_NOTICE_KEY, '1')
  } catch {
  }
}

function clearProbeNoticeSkipped() {
  try {
    localStorage.removeItem(CT_PROBE_NOTICE_KEY)
  } catch {
  }
}

async function openProbeNoticeDialog() {
  try {
    const result = await showConfirm({
      title: "试探秒传流程：",
      preset: "cross-transfer-probe-notice",
      checkboxLabel: "不再提示",
      checkboxDefault: isProbeNoticeDismissed(),
      showCancel: false,
      danger: false,
      actions: [{ id: "confirm", label: "我知道了，继续", variant: "primary" }],
    })
    if (result.checked) markProbeNoticeSkipped()
    else clearProbeNoticeSkipped()
    return result.action === "confirm"
  } catch {
    return false
  }
}

async function confirmProbeNotice() {
  if (isProbeNoticeDismissed()) return true
  return openProbeNoticeDialog()
}

function onFooterTipClick() {
  if (currentFooterTip.value?.action !== 'probe-notice') return
  openProbeNoticeDialog()
}

function startFooterTipTimer() {
  stopFooterTipTimer()
  footerTipTimer = setInterval(() => {
    footerTipIndex.value = (footerTipIndex.value + 1) % footerScrollTips.length
  }, FOOTER_TIP_INTERVAL_MS)
}

function stopFooterTipTimer() {
  if (!footerTipTimer) return
  clearInterval(footerTipTimer)
  footerTipTimer = null
}

async function confirmLargeBatch(scan) {
  const files = scan?.total || 0
  const folders = scan?.shallow_dirs || 0
  if (folders <= SOFT_FOLDER_LIMIT) return true
  try {
    await confirm({
      title: "子文件夹较多",
      message: `所选目录下一至二级共有 ${folders} 个子文件夹（共 ${files} 个文件）。递归扫描需逐个目录请求，继续可能较慢。建议每次只选一部影片或一个子目录。`,
      confirmText: "继续",
      cancelText: "取消",
      danger: false,
    });
    return true
  } catch {
    return false
  }
}

function collectTreeFilePaths(nodes) {
  const paths = []
  const walk = (list) => {
    for (const n of list || []) {
      if (n.type === 'dir') walk(n.children)
      else if (n.rel_path) paths.push(n.rel_path)
    }
  }
  walk(nodes)
  return paths
}

function orderFilesByTree(fileList) {
  const fileMap = {}
  fileList.forEach(f => { fileMap[f.rel_path] = f })
  const fileSet = new Set(fileList.map(f => f.rel_path))
  const orderedPaths = collectTreeFilePaths(srcTree.value).filter(p => fileSet.has(p))
  const seen = new Set(orderedPaths)
  for (const f of fileList) {
    if (!seen.has(f.rel_path)) orderedPaths.push(f.rel_path)
  }
  return orderedPaths.map(p => fileMap[p]).filter(Boolean)
}

function createFileRunContext(fileList) {
  const nodeMap = {}
  const walk = (nodes) => {
    for (const n of nodes || []) {
      if (n.type === 'dir') walk(n.children)
      else nodeMap[n.rel_path] = n
    }
  }
  walk(srcTree.value)
  const fileMap = {}
  fileList.forEach(f => { fileMap[f.rel_path] = f })
  const fileSet = new Set(fileList.map(f => f.rel_path))
  const orderedPaths = collectTreeFilePaths(srcTree.value).filter(p => fileSet.has(p))
  const seen = new Set(orderedPaths)
  for (const f of fileList) {
    if (!seen.has(f.rel_path)) orderedPaths.push(f.rel_path)
  }
  const setNodeRun = (relPath, run) => {
    const node = nodeMap[relPath]
    if (!node) return
    if (run) node.state = 'run'
    else delete node.state
  }
  const clearAllRun = () => {
    for (const p of orderedPaths) setNodeRun(p, false)
  }
  const scrollToFile = (relPath) => {
    nextTick(() => {
      const root = srcTreeRef.value
      if (!root || !relPath) return
      const el = root.querySelector(`[data-rel-path="${CSS.escape(relPath)}"]`)
      if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    })
  }
  return { nodeMap, fileMap, orderedPaths, setNodeRun, clearAllRun, scrollToFile }
}

const matrixOpen = ref(false)
const mxSelected = ref(null)
const statusText = computed(() => {
  if (!selectedView.value) return "请选择线路";
  return `已选：${selectedView.value.from.name} → ${selectedView.value.to.name}（${selectedView.value.method_label}）`;
})
const selectedView = computed(() => {
  const sel = mxSelected.value
  if (!sel) return null
  const r = sel.route
  return sel.reversed
    ? { from: r.to, to: r.from, method_label: r.method_label }
    : { from: r.from, to: r.to, method_label: r.method_label }
})
function openMatrix() {
  // 打开时不预设线路：由用户在配线架中选择
  mxSelected.value = null
  matrixOpen.value = true
}
function onMatrixPatchSelect(route, reversed) {
  mxSelected.value = { route, reversed: Boolean(reversed) }
}
function applyMatrixSelection() {
  const sel = mxSelected.value
  if (!sel) return
  // 直接按所选方向落位（双向线路若选的是反向，则以反向进入主界面，不做“交换”提示）
  activeId.value = sel.route.id
  swapped.value = Boolean(sel.route.bidirectional && sel.reversed)
  reset()
  matrixOpen.value = false
}
defineExpose({ openMatrix })
function swap() {
  if (!curRoute.value || !curRoute.value.bidirectional) return
  swapped.value = !swapped.value
  reset()
  notify('success', `已交换方向：${srcPan.value.name} → ${dstPan.value.name}`)
}

function stopRun() {
  if (!running.value) return
  phaseStatus.value = ''
  try { abortCtrl.value?.abort() } catch {}
}

async function openPicker(mode) {
  if (!curRoute.value) {
    notify("warning", "请先通过「线路选择」选择线路");
    return;
  }
  const driver = mode === "src" ? srcDriver.value : dstDriver.value;
  const panName = panOf(driver).name || driver;
  const accs = accountsFor(driver);
  if (!accs.length) {
    notify("warning", `没有可用的${panName}账号，请先到「存储管理」添加`);
    return;
  }
  const cur = mode === "src" ? src.value : dst.value;
  pickerMode.value = mode;
  pickerAccounts.value = accs;
  pickerInitialAccountId.value = Number(cur?.accId || accs[0]?.id || 0) || null;
  pickerInitialPath.value = mode === 'src' ? '' : (cur?.path || '');
  pickerOpen.value = true;
}

function onPickerResolve(payload) {
  pickerOpen.value = false;
  const mode = pickerMode.value;
  // 同驱动（自环/同盘）线路不允许源与目标是同一个账号
  const selfDriver = Boolean(
    curRoute.value && curRoute.value.from.driver === curRoute.value.to.driver,
  );
  const other = mode === "src" ? dst.value : src.value;
  if (selfDriver && other && other.accId === payload.accountId) {
    notify("warning", "同盘秒传请选择两个不同的账号（源与目标不能是同一账号）");
    return;
  }
  if (mode === "src") {
    const selected = Array.isArray(payload.selections) && payload.selections.length
      ? payload.selections
      : [{
        id: payload.parentId,
        name: payload.path.split('/').filter(Boolean).pop() || '根目录',
        path: payload.path,
        ancestorIds: [],
      }]
    src.value = {
      accId: payload.accountId,
      accName: payload.accountName,
      sources: selected.map(item => ({
        parentId: item.id,
        name: item.name,
        path: item.path || '/',
        ancestorIds: [...(item.ancestorIds || [])],
      })),
    };
    srcTree.value = null;
    probeFiles.value = [];
    scanSummary.value = null;
    scanLimitReason.value = '';
  } else {
    dst.value = {
      accId: payload.accountId,
      accName: payload.accountName,
      parentId: payload.parentId,
      path: payload.path,
    };
  }
  dstTree.value = null;
  resetMetrics();
}

async function scanSource(clearTree = true) {
  if (!src.value || !curRoute.value) return null
  if (clearTree) {
    srcTree.value = null
    resetMetrics()
    scanSummary.value = null
    scanLimitReason.value = ''
  }
  phaseStatus.value = '正在扫描源目录…'
  let scan = null
  let streamError = ''
  try {
    for await (const msg of scanCrossTransferSourceStream({
      source_account_id: Number(src.value.accId),
      sources: sourceRoots.value.map(item => ({
        parent_id: item.parentId,
        display_path: item.path || '/',
        ancestor_ids: item.ancestorIds || [],
      })),
      method: curRoute.value.method,
    }, abortCtrl.value?.signal)) {
      if (msg.event === 'progress') {
        const directories = Number(msg.directories || 0)
        const files = Number(msg.files || 0)
        phaseStatus.value = `正在扫描源目录…已扫描 ${directories} 个目录、${files} 个文件`
      } else if (msg.event === 'end') {
        scan = msg.result
      } else if (msg.event === 'error') {
        streamError = String(msg.message || '扫描失败')
      }
    }
    if (streamError) throw new Error(streamError)
    if (!scan) throw new Error('扫描未返回结果')
    decorateTree(scan.tree)
    srcTree.value = scan.tree
    probeFiles.value = orderFilesByTree(scan.files || [])
    scanLimitReason.value = scan.truncated ? (scan.truncated_reason || '扫描结果不完整') : ''
    metrics.total = scan.total
    if (clearTree) {
      metrics.ok = 0
      metrics.no = 0
      metrics.done = 0
    }
    scanSummary.value = buildScanSummary(scan)
    if (scan.truncated) notify('error', `${scanLimitReason.value}，已禁止继续试探或传输`)
    if (running.value) phaseStatus.value = ''
    return scan
  } catch (e) {
    if (e?.name === 'CanceledError' || e?.name === 'AbortError') return null
    notify('error', '扫描失败: ' + (e?.message || e))
    return null
  } finally {
    if (!running.value) phaseStatus.value = ''
  }
}

async function probe() {
  if (!src.value || !dst.value || !curRoute.value) return
  if (!(await confirmProbeNotice())) return
  running.value = 'probe'
  abortCtrl.value = new AbortController()
  barWidth.value = 8

  const scan = await scanSource(true)
  if (!scan) {
    running.value = ''
    barWidth.value = 0
    return
  }
  if (!ensureCompleteScan(scan)) {
    running.value = ''
    barWidth.value = 0
    return
  }
  if (!(await confirmLargeBatch(scan))) {
    clearSourceSelection()
    running.value = ''
    barWidth.value = 0
    return
  }

  const orderedProbeFiles = orderFilesByTree(probeFiles.value)
  const { nodeMap, fileMap, orderedPaths, setNodeRun, clearAllRun, scrollToFile } = createFileRunContext(orderedProbeFiles)
  if (orderedPaths.length) {
    setNodeRun(orderedPaths[0], true)
    scrollToFile(orderedPaths[0])
  }

  let processed = 0
  const probeErrors = new Set()
  let streamError = ''
  try {
    for await (const msg of probeCrossTransferStream({
      source_account_id: src.value.accId,
      target_account_id: dst.value.accId,
      target_parent_id: dst.value.parentId,
      method: curRoute.value.method,
      files: orderedProbeFiles.map((f) => ({
        source_file_id: f.source_file_id,
        rel_path: f.rel_path,
        name: f.name,
        size: f.size,
        hash: f.hash,
      })),
    }, abortCtrl.value?.signal)) {
      if (msg.event === "hashing") {
        const relPath = String(msg.rel_path || "");
        if (relPath) {
          setNodeRun(relPath, true);
          scrollToFile(relPath);
        }
      } else if (msg.event === "item") {
        const relPath = String(msg.rel_path || "");
        const node = nodeMap[relPath];
        if (msg.hash) {
          const f = fileMap[relPath];
          if (f) f.hash = String(msg.hash);
          if (node) node.hash = String(msg.hash);
        }
        setNodeRun(relPath, false);
        if (node) {
          node.reuse = msg.reuse;
          delete node.state;
        }
        const f = fileMap[relPath];
        if (f) f.reuse = msg.reuse;
        if (msg.error) probeErrors.add(String(msg.error));
        if (msg.reuse) metrics.ok++;
        else metrics.no++;
        processed++;
        barWidth.value = metrics.total ? Math.round((processed / metrics.total) * 100) : 0;
        const nextPath = orderedPaths[processed];
        if (nextPath) {
          setNodeRun(nextPath, true);
          scrollToFile(nextPath);
        }
      } else if (msg.event === "end") {
        metrics.ok = Number(msg.ok || 0);
        metrics.no = Number(msg.no || 0);
      } else if (msg.event === "error") {
        streamError = String(msg.message || "试探失败")
        notify("error", streamError)
      }
    }
    if (streamError) {
      return
    } else if (probeErrors.size) {
      const detail = Array.from(probeErrors).slice(0, 2).join('；')
      notify('warning', `目标盘试探报错：${detail}（可秒传 ${metrics.ok}/${metrics.total}，其余可能为未命中或受目标盘限制）`)
    } else {
      notify('success', `试探完成，可秒传 ${metrics.ok}/${metrics.total}`)
    }
  } catch (e) {
    if (e?.name === 'AbortError') notify('warning', '已停止试探')
    else notify('error', '试探失败: ' + (e.message || e))
  } finally {
    abortCtrl.value = null
    clearAllRun()
    phaseStatus.value = ''
    running.value = ''
    setTimeout(() => { barWidth.value = 0 }, 500)
  }
}

async function start() {
  if (!src.value || !dst.value || !curRoute.value) return
  clearRelayNotice()
  running.value = 'exec'
  abortCtrl.value = new AbortController()
  barWidth.value = 12

  if (!probeFiles.value.length) {
    const scan = await scanSource(false)
    if (!scan) {
      running.value = ''
      barWidth.value = 0
      return
    }
    if (!ensureCompleteScan(scan)) {
      running.value = ''
      barWidth.value = 0
      return
    }
    if (!(await confirmLargeBatch(scan))) {
      clearSourceSelection()
      running.value = ''
      barWidth.value = 0
      return
    }
  }
  if (!ensureCompleteScan()) {
    running.value = ''
    barWidth.value = 0
    return
  }

  const files = orderFilesByTree(probeFiles.value)
  if (!files.length) {
    notify('warning', '没有可处理的文件')
    running.value = ''
    barWidth.value = 0
    return
  }

  const { nodeMap, fileMap, orderedPaths, setNodeRun, clearAllRun, scrollToFile } = createFileRunContext(files)
  if (orderedPaths.length) {
    setNodeRun(orderedPaths[0], true)
    scrollToFile(orderedPaths[0])
  }

  const allResults = []
  let processed = 0
  barWidth.value = 20
  try {
    for await (const msg of executeCrossTransferStream({
      source_account_id: src.value.accId,
      source_account_name: src.value.accName,
      source_driver_type: srcDriver.value,
      target_account_id: dst.value.accId,
      target_account_name: dst.value.accName,
      target_driver_type: dstDriver.value,
      target_parent_id: dst.value.parentId,
      target_display_path: dst.value.path,
      method: curRoute.value.method,
      files: files.map(f => ({
        source_file_id: f.source_file_id,
        rel_path: f.rel_path,
        rel_dir: f.rel_dir,
        name: f.name,
        size: f.size,
        hash: f.hash,
      })),
      conflict: effectiveConflict.value,
      fallback: fallback.value === 'on',
    }, abortCtrl.value?.signal)) {
      if (msg.event === 'start') {
        metrics.done = 0
      } else if (msg.event === 'item') {
        const relPath = msg.rel_path
        allResults.push({
          rel_path: msg.rel_path,
          name: msg.name,
          success: msg.success,
          mode: msg.mode,
          file_id: msg.file_id,
          error: msg.error,
        })
        setNodeRun(relPath, false)
        const node = nodeMap[relPath]
        const file = fileMap[relPath]
        if (node) {
          if (msg.mode === 'rapid' && msg.success) {
            node.reuse = true
            node.transferred = true
            delete node.relay
            delete node.skipped
            delete node.transferError
          } else if (msg.mode === 'rapid') {
            node.reuse = false
            delete node.transferred
            delete node.relay
            delete node.skipped
            delete node.transferError
          } else if (msg.mode === 'relay') {
            node.relay = true
            delete node.skipped
            delete node.transferError
          } else if (msg.mode === 'skip' && msg.success) {
            node.skipped = true
            delete node.relay
            delete node.transferError
          } else if (msg.mode === 'error') {
            node.transferError = String(msg.error || '传输失败')
            delete node.transferred
            delete node.relay
            delete node.skipped
          }
          delete node.state
        }
        if (file && msg.mode === 'rapid') file.reuse = Boolean(msg.success)
        if (msg.mode === 'rapid' && msg.success) {
          metrics.done++
          applyTransferResults([msg])
        }
        processed++
        barWidth.value = files.length ? Math.round(20 + processed / files.length * 75) : 100
        const nextPath = orderedPaths[processed]
        if (nextPath) {
          setNodeRun(nextPath, true)
          scrollToFile(nextPath)
        }
      } else if (msg.event === 'end') {
        metrics.done = msg.rapid_done ?? msg.done ?? metrics.done
        metrics.ok = metrics.done
        const skipped = allResults.filter(r => r.mode === 'skip' && r.success).length
        metrics.no = Math.max(0, files.length - metrics.done - (msg.relay_queued || 0) - skipped)
        const rapidResults = allResults.filter(r => r.mode === 'rapid' && r.success)
        buildDstTree(rapidResults, files)
        markRelayQueued(allResults)
        barWidth.value = 100
        const relayQueued = msg.relay_queued || 0
        const skipText = skipped > 0 ? `，跳过 ${skipped}` : ''
        const message = `秒传完成 ${metrics.done}/${files.length}${skipText}`
        if (relayQueued > 0) {
          relayNotice.value = {
            rapidDone: metrics.done,
            total: files.length,
            relayQueued,
          }
        } else {
          notify(metrics.done === files.length ? 'success' : 'warning', message)
        }
      } else if (msg.event === 'error') {
        notify('error', msg.message || '传输失败')
      }
    }
  } catch (e) {
    if (e?.name === 'AbortError') notify('warning', '已停止传输（已处理的文件保留，未处理的已中止）')
    else notify('error', '传输失败: ' + (e.message || e))
  } finally {
    abortCtrl.value = null
    clearAllRun()
    phaseStatus.value = ''
    running.value = ''
    setTimeout(() => { barWidth.value = 0 }, 600)
  }
}

function decorateTree(nodes) {
  for (const n of nodes || []) {
    if (n.type === 'dir') {
      n.open = true
      decorateTree(n.children)
    } else {
      n.transferred = false
      delete n.skipped
      if (n.eligible && n.reuse == null) delete n.reuse
    }
  }
}
function markRelayQueued(results) {
  const relayPaths = new Set(results.filter(r => r.mode === 'relay').map(r => r.rel_path))
  const walk = (nodes) => {
    for (const n of nodes || []) {
      if (n.type === 'dir') walk(n.children)
      else if (relayPaths.has(n.rel_path)) {
        n.reuse = false
        n.relay = true
      }
    }
  }
  walk(srcTree.value)
}

function applyTransferResults(results) {
  const okPaths = new Set(results.filter(r => r.success).map(r => r.rel_path))
  const walk = (nodes) => {
    for (const n of nodes || []) {
      if (n.type === 'dir') walk(n.children)
      else if (okPaths.has(n.rel_path)) n.transferred = true
    }
  }
  walk(srcTree.value)
}
function buildDstTree(results, files) {
  const fileByPath = Object.fromEntries(files.map(f => [f.rel_path, f]))
  const tree = []
  const ensureDir = (segments) => {
    let list = tree
    let parent = null
    for (const seg of segments) {
      let node = list.find(x => x.type === 'dir' && x.name === seg)
      if (!node) { node = { id: 'd_' + seg + '_' + list.length, type: 'dir', name: seg, open: true, children: [] }; list.push(node) }
      parent = node
      list = node.children
    }
    return parent ? parent.children : tree
  }
  results.filter(r => r.success).forEach((r, idx) => {
    const f = fileByPath[r.rel_path] || {}
    const segments = (f.rel_dir || '').split('/').filter(Boolean)
    const bucket = ensureDir(segments)
    bucket.push({ id: 'f_' + idx, type: 'file', name: r.name, size: f.size || 0 })
  })
  dstTree.value = tree.length ? tree : null
}

function resetMetrics() { metrics.total = 0; metrics.ok = 0; metrics.no = 0; metrics.done = 0 }
function reset() {
  if (running.value) return
  clearRelayNotice()
  phaseStatus.value = ''
  scanSummary.value = null
  scanLimitReason.value = ''
  src.value = null
  dst.value = null
  srcTree.value = null
  dstTree.value = null
  probeFiles.value = []
  barWidth.value = 0
  resetMetrics()
}

function normalizeRouteDirection(route) {
  if (!route?.bidirectional || route.from?.driver !== '123_open') return route
  return { ...route, from: route.to, to: route.from }
}

async function loadRoutes() {
  try {
    routes.value = (await listCrossTransferRoutes()).map(normalizeRouteDirection)
    // 默认不选中线路：先让用户在矩阵/配线架中选择
  } catch (e) {
    notify('error', '获取线路失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}
async function loadAccounts() {
  try {
    accounts.value = await accountsApi.list()
  } catch (e) {
    notify('error', '获取账号失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}

function loadCtSettings() {
  try {
    const raw = localStorage.getItem(CT_SETTINGS_STORAGE_KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    if (data.conflict === 'skip' || data.conflict === 'rename' || data.conflict === 'overwrite') conflict.value = data.conflict
    if (data.fallback === 'on' || data.fallback === 'off') fallback.value = data.fallback
  } catch {
  }
}

function saveCtSettings() {
  try {
    localStorage.setItem(CT_SETTINGS_STORAGE_KEY, JSON.stringify({
      conflict: conflict.value,
      fallback: fallback.value,
    }))
  } catch {
  }
}

function updateSettingsDropdownPos() {
  const trigger = settingsTriggerRef.value
  if (!trigger) return
  const rect = trigger.getBoundingClientRect()
  const gap = 8
  const center = rect.left + rect.width / 2
  const left = Math.min(
    Math.max(8, center - SETTINGS_DROPDOWN_WIDTH / 2),
    window.innerWidth - SETTINGS_DROPDOWN_WIDTH - 8
  )
  settingsDropdownStyle.value = {
    position: 'fixed',
    left: `${left}px`,
    top: `${rect.top - gap}px`,
    transform: 'translateY(-100%)',
    width: `${SETTINGS_DROPDOWN_WIDTH}px`,
    zIndex: '100000',
  }
}

function toggleSettingsMenu(e) {
  e?.stopPropagation()
  settingsOpen.value = !settingsOpen.value
  if (settingsOpen.value) nextTick(() => updateSettingsDropdownPos())
}

function onDocClick(e) {
  if (!settingsOpen.value) return
  const menu = settingsMenuRef.value
  const panel = settingsDropdownRef.value
  if (menu?.contains(e.target) || panel?.contains(e.target)) return
  settingsOpen.value = false
}

function onSettingsReposition() {
  if (settingsOpen.value) updateSettingsDropdownPos()
}

watch([conflict, fallback], saveCtSettings)
watch(targetSkipUnsupported, (unsupported) => {
  if (unsupported && conflict.value === 'skip') conflict.value = 'rename'
})
watch(targetOverwriteUnsupported, (unsupported) => {
  if (unsupported && conflict.value === 'overwrite') conflict.value = 'rename'
})
watch(targetRenameUnsupported, (unsupported) => {
  if (unsupported && conflict.value === 'rename') conflict.value = 'overwrite'
})
watch(showFooterScrollTips, (show) => {
  if (!uiActive) return
  if (show) startFooterTipTimer()
  else stopFooterTipTimer()
})

function activateUi() {
  if (uiActive) return
  uiActive = true
  document.addEventListener('click', onDocClick)
  window.addEventListener('scroll', onSettingsReposition, true)
  window.addEventListener('resize', onSettingsReposition)
  if (showFooterScrollTips.value) startFooterTipTimer()
}

function deactivateUi() {
  if (!uiActive) return
  uiActive = false
  settingsOpen.value = false
  pickerOpen.value = false
  stopFooterTipTimer()
  document.removeEventListener('click', onDocClick)
  window.removeEventListener('scroll', onSettingsReposition, true)
  window.removeEventListener('resize', onSettingsReposition)
}

onMounted(() => {
  loadCtSettings()
  loadRoutes()
  loadAccounts()
})
onActivated(activateUi)
onDeactivated(deactivateUi)
onUnmounted(() => {
  abortCtrl.value?.abort()
  deactivateUi()
})
</script>

<style scoped>
.cross-transfer {
  color: var(--text);
  --card-bg: var(--surface);
  --app-bg: var(--bg);
  --border-color: var(--border);
  --text-main: var(--text);
  --text-secondary: var(--text-muted);
  --text-regular: var(--text-regular);
  --primary-color: var(--brand);
  --primary-color-end: var(--brand-end);
}.logo-chip { display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto; }.logo-chip img { object-fit: contain; border-radius: var(--radius-sm); }.logo-chip.s26 { width: 26px; height: 26px; }.logo-chip.s26 img { width: 26px; height: 26px; }.transfer-shell {
  margin-top: 0;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-soft);
  overflow: hidden;
}.transfer-topbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: color-mix(in srgb, var(--app-bg) 55%, var(--card-bg));
  border-bottom: 1px solid var(--border-color);
}.tb-side { display: flex; align-items: center; gap: 8px; min-width: 0; }.tb-side.tb-dst { justify-content: flex-end; }.tb-title { min-width: 0; }.tb-title span { display: block; font-weight: 700; font-size: 14px; line-height: 1.25; }.tb-title small { display: block; font-size: 11px; font-weight: 500; color: var(--text-secondary); }.tb-title-dst { text-align: right; }.panel-role { flex-shrink: 0; font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: var(--radius-pill); }.tb-src .panel-role { background: rgba(76,116,223,.12); color: #2952cc; }.dst-role { background: rgba(255,140,66,.16); color: #c2410c; }.tb-mid {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  flex-shrink: 0;
  padding: 0 4px;
  min-height: 46px;
}.tb-flow {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: grid;
  place-items: center;
  font-size: 12px;
  color: var(--primary-color);
  background: rgba(76,116,223,.08);
  border: 1px solid rgba(76,116,223,.14);
}.tb-swap {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(76,116,223,.14);
  background: rgba(76,116,223,.08);
  color: var(--primary-color);
  font-size: 12px;
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: background .2s ease, border-color .2s ease;
}.tb-swap:hover {
  background: rgba(76,116,223,.16);
  border-color: rgba(76,116,223,.3);
}.tb-swap-hint { font-size: 10px; color: var(--text-secondary); white-space: nowrap; line-height: 1; }.transfer-body { display: grid; grid-template-columns: 1fr 1fr; align-items: stretch; }.panel { background: var(--card-bg); min-width: 0; overflow: hidden; display: flex; flex-direction: column; }.panel.src { border-right: 1px solid var(--border-color); }.panel-pick { padding: 12px 16px; border-bottom: 1px solid var(--border-color); box-sizing: border-box; }.combo {
  width: 100%;
  height: 40px;
  box-sizing: border-box;
  border: none;
  border-radius: var(--radius-md);
  padding: 0 14px;
  background: var(--app-bg);
  color: var(--text-main);
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
  transition: background .15s;
}.combo:hover { background: rgba(127,127,127,.12); }.combo .c-ic { color: var(--primary-color); flex: 0 0 auto; line-height: 1; }.combo .c-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 20px;
}.combo .c-text.placeholder { color: var(--text-secondary); }.combo .c-caret { color: var(--text-secondary); flex: 0 0 auto; line-height: 1; }.tree { padding: 6px; height: 300px; overflow: auto; }.tree-host { position: relative; }.tree-empty { color: var(--text-secondary); padding: 28px 12px; text-align: center; }.tree-scan-banner {
  display: flex; align-items: flex-start; gap: 8px;
  margin: 4px 6px 8px; padding: 8px 10px; border-radius: var(--radius-md);
  font-size: 12px; line-height: 1.45; color: var(--text-secondary);
  background: rgba(76,116,223,.06); border: 1px solid rgba(76,116,223,.12);
}.tree-scan-banner i { margin-top: 2px; color: var(--primary-color); flex-shrink: 0; }.tree-scan-banner.warn { color: #b45309; background: rgba(245,158,11,.08); border-color: rgba(245,158,11,.22); }.tree-scan-banner.warn i { color: #d97706; }.tree-phase-fill {
  position: absolute; inset: 0; z-index: 2;
  display: flex; align-items: center; justify-content: center;
  background: color-mix(in srgb, var(--card-bg) 88%, transparent);
}.tree-phase-card {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  width: min(520px, calc(100% - 24px)); padding: 8px 12px; text-align: center;
}.tree-phase-spin { color: var(--primary-color); }.tree-phase-title { margin: 0; max-width: 100%; white-space: nowrap; font-size: 14px; font-weight: 600; color: var(--text-main); }.tree-phase-sub { margin: 0; font-size: 12px; line-height: 1.45; color: var(--text-secondary); }.tree-phase-bar {
  width: 160px; height: 4px; border-radius: var(--radius-pill); overflow: hidden;
  background: var(--app-bg); border: 1px solid var(--border-color);
}.tree-phase-bar-indeterminate {
  width: 40%; height: 100%; border-radius: var(--radius-pill);
  background: linear-gradient(90deg, var(--primary-color), var(--primary-color-end));
  animation: ct-scan-bar 1.2s ease-in-out infinite;
}@keyframes ct-scan-bar {
  0% { transform: translateX(-120%); }
  100% { transform: translateX(320%); }
}.ct-footer {
  margin-top: 10px;
  background: linear-gradient(180deg, var(--card-bg), color-mix(in srgb, var(--app-bg) 40%, var(--card-bg)));
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-soft);
  overflow: visible;
}.ct-footer-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
}.ct-footer-left {
  flex: 0 0 auto;
  min-width: 0;
}.ct-footer-center {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding: 0 6px;
}.ft-center-progress {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}.ft-prog-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.35;
  color: var(--text-secondary);
}.ct-footer-center .ft-prog-row {
  width: 100%;
  max-width: none;
  margin-top: 0;
}.ct-footer-scroll-hint {
  flex: 1;
  width: 100%;
  min-width: 0;
  border: 1px solid rgba(76,116,223,.14);
  background: rgba(76,116,223,.06);
  border-radius: var(--radius-md);
  padding: 6px 10px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.35;
  text-align: left;
}.ct-footer-scroll-hint.is-clickable {
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease;
}.ct-footer-scroll-hint.is-clickable:hover {
  background: rgba(76,116,223,.1);
  border-color: rgba(76,116,223,.28);
}.ct-footer-scroll-text {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}.ct-footer-scroll-text i {
  color: var(--primary-color);
  flex-shrink: 0;
}.ct-tip-fade-enter-active,
.ct-tip-fade-leave-active {
  transition: opacity .28s ease;
}.ct-tip-fade-enter-from,
.ct-tip-fade-leave-to {
  opacity: 0;
}.ct-footer-center .ct-relay-inline-hint {
  flex: 1;
  width: 100%;
  min-width: 0;
  white-space: normal;
}.ct-footer-center .ct-relay-inline-hint > span {
  white-space: normal;
  line-height: 1.35;
}.ft-stats { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }.ft-item { display: inline-flex; align-items: baseline; gap: 4px; white-space: nowrap; }.ft-item .n {
  font-size: 22px; font-weight: 700; letter-spacing: -.02em;
  font-variant-numeric: tabular-nums; color: var(--text-main); line-height: 1;
}.ft-item .n.ok { color: #16a34a; }.ft-item .n.no { color: #94a3b8; }.ft-item .n.relay { color: #2563eb; }.ft-item .l { font-size: 11px; color: var(--text-secondary); }.ft-sep { width: 2px; height: 2px; border-radius: 50%; background: #cbd5e1; flex-shrink: 0; }.ft-prog-row {
  display: flex;
  align-items: center;
  gap: 8px;
}.ft-track {
  flex: 1;
  height: 2px;
  border-radius: var(--radius-pill);
  background: #dde3ea;
  overflow: hidden;
}.ft-track > i {
  display: block;
  height: 100%;
  border-radius: var(--radius-pill);
  background: #16a34a;
  transition: width .18s ease;
}.ft-pct {
  font-size: 12px;
  font-weight: 700;
  color: #16a34a;
  min-width: 36px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}.footer-island {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-soft);
}.footer-island .ct-settings-trigger { border: none; background: transparent; box-shadow: none; }.ct-relay-inline-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(37, 99, 235, .18);
  background: rgba(37, 99, 235, .06);
  color: #2563eb;
  font-size: 13px;
  line-height: 1.35;
  text-decoration: none;
  transition: background .15s ease, border-color .15s ease;
}.ct-relay-inline-hint:hover {
  background: rgba(37, 99, 235, .1);
  border-color: rgba(37, 99, 235, .32);
}.ct-relay-inline-hint > span {
  color: var(--text-secondary);
}.ct-relay-inline-arrow {
  flex-shrink: 0;
  font-size: 11px;
  opacity: .75;
}.ct-settings-menu { position: relative; flex: 0 0 auto; }.ct-settings-trigger {
  width: 38px; height: 38px; border: 1px solid var(--border-color); border-radius: var(--radius-md);
  background: var(--card-bg); color: var(--text-secondary); cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
}.ct-settings-trigger:hover { color: var(--primary-color); border-color: rgba(76,116,223,.35); }.ct-settings-dropdown {
  padding: 12px;
  border-radius: var(--radius-lg);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--surface) 92%, #fff), var(--surface));
  border: 1px solid var(--border);
  box-shadow: 0 14px 34px rgba(15,23,42,.14), 0 2px 8px rgba(15,23,42,.07);
}.ct-settings-dropdown-portal {
  position: fixed;
  z-index: 2000;
}.ct-settings-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}.ct-settings-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}.ct-settings-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
}.ct-settings-seg {
  display: flex;
  gap: 3px;
  padding: 3px;
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--bg) 86%, var(--surface));
  border: 1px solid var(--border);
}.ct-settings-opt {
  flex: 1;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background .15s ease, color .15s ease, box-shadow .15s ease;
}.ct-settings-opt:hover:not(.active) {
  color: var(--text);
  background: color-mix(in srgb, var(--surface) 70%, transparent);
}.ct-settings-opt.active {
  background: var(--surface);
  color: var(--brand);
  box-shadow: 0 1px 5px rgba(15,23,42,.1);
}.ct-settings-opt:disabled {
  cursor: not-allowed;
  opacity: .45;
}.ct-settings-fallback-hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.4;
  color: var(--text-muted);
}.ct-btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 16px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--card-bg); color: var(--text-regular); font-size: 14px; font-weight: 600; cursor: pointer; transition: filter .2s, opacity .2s; white-space: nowrap; }.ct-btn:disabled { opacity: .5; cursor: not-allowed; }.ct-btn-primary { background: linear-gradient(135deg, var(--primary-color), var(--primary-color-end)); border-color: transparent; color: #fff; box-shadow: var(--shadow-brand); }.ct-btn-primary:not(:disabled):hover { filter: brightness(1.06); }.ct-btn-go { background: linear-gradient(135deg, #16a34a, #22c55e); border-color: transparent; color: #fff; box-shadow: var(--shadow-brand); }.ct-btn-go:not(:disabled):hover { filter: brightness(1.06); }.ct-btn-danger { background: rgba(239,68,68,.1); border-color: rgba(239,68,68,.3); color: #dc2626; }.ct-btn-danger:not(:disabled):hover { background: rgba(239,68,68,.18); }:global(:root[data-theme="dark"]) .cross-transfer {
}:global(:root[data-theme="dark"]) .ct-settings-dropdown-portal {
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--surface) 92%, #1f2937), var(--surface));
  border-color: color-mix(in srgb, var(--border) 80%, #fff);
  box-shadow: 0 18px 42px rgba(0,0,0,.42), 0 2px 8px rgba(0,0,0,.24);
}:global(:root[data-skin="brutal"]) .ct-settings-dropdown-portal {
  border: var(--brutal-bw) solid var(--brutal-ink);
  border-radius: 0;
  background: #fff;
  color: var(--brutal-ink);
  box-shadow: 4px 4px 0 var(--brutal-ink);
}:global(:root[data-skin="brutal"]) .ct-settings-label,
:global(:root[data-skin="brutal"]) .ct-settings-fallback-hint {
  color: var(--brutal-ink);
}:global(:root[data-skin="brutal"]) .ct-settings-seg {
  border: var(--brutal-bw) solid var(--brutal-ink);
  border-radius: 0;
  background: var(--brutal-ink);
  padding: 0;
  gap: 0;
}:global(:root[data-skin="brutal"]) .ct-settings-opt {
  border-radius: 0;
  color: var(--brutal-yellow);
  font-weight: 800;
  box-shadow: none;
}:global(:root[data-skin="brutal"]) .ct-settings-opt + .ct-settings-opt {
  border-left: var(--brutal-bw) solid var(--brutal-ink);
}:global(:root[data-skin="brutal"]) .ct-settings-opt:hover:not(.active) {
  background: color-mix(in srgb, #fff 12%, var(--brutal-ink));
  color: var(--brutal-yellow);
}:global(:root[data-skin="brutal"]) .ct-settings-opt.active {
  background: var(--brutal-yellow);
  color: var(--brutal-ink);
  box-shadow: none;
}@media (max-width: 1080px) {
  .transfer-topbar { grid-template-columns: 1fr; gap: 8px; text-align: center; }
  .tb-side.tb-src, .tb-side.tb-dst { justify-content: center; }
  .tb-title-dst { text-align: center; }
  .tb-swap-hint { display: none; }
  .transfer-body { grid-template-columns: 1fr; }
  .panel.src { border-right: none; border-bottom: 1px solid var(--border-color); }
  .ct-footer-bar { flex-wrap: wrap; row-gap: 8px; }
  .ct-footer-center {
    flex: 1 1 100%;
    order: 3;
    padding: 0;
  }
  .ct-footer-center .ft-prog-row { max-width: 100%; }
  .footer-island { margin-left: auto; flex-wrap: wrap; }
}/* ===== 秒传航线图弹层：整套深色（与航线画布一体，参照演示） ===== */
.mx-shell {
  display: flex;
  flex-direction: column;
  width: min(860px, 96vw);
  max-height: 90vh;
  border-radius: 12px; /* 与 AppModal bare 外壳圆角一致，避免四角露白 */
  overflow: hidden;
  background: radial-gradient(1100px 500px at 50% -10%, #1a2f55 0%, #101f3b 48%, #0b1730 100%);
  box-shadow: 0 26px 70px rgba(2, 6, 23, 0.55);
}
.mx-bar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  padding: 18px 22px 6px;
  color: #dbe6ff;
}
.mx-title {
  justify-self: start;
  min-width: 0;
}
.mx-status {
  justify-self: center;
  max-width: 100%;
  min-width: 0;
  text-align: center;
  font-size: 13px;
  color: #9fb0d6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mx-x {
  justify-self: end;
  margin-left: 0;
}
.mx-title {
  font-size: 16px;
  font-weight: 750;
  letter-spacing: 0.02em;
  color: #dbe6ff;
}
.mx-x {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #7f93c4;
  cursor: pointer;
  font-size: 16px;
}
.mx-x:hover { color: #fff; background: rgba(140, 170, 255, 0.14); }
.mx-scroll {
  overflow-y: auto;
  padding: 6px 22px 0;
  color: #dbe6ff;
}
.mx-scroll::-webkit-scrollbar { width: 8px; }
.mx-scroll::-webkit-scrollbar-thumb { background: rgba(140, 170, 255, 0.25); border-radius: 4px; }

.mx-foot {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 22px 18px;
}
.mx-btn {
  border: 1px solid rgba(140, 170, 255, 0.3);
  background: transparent;
  color: #9fb0d6;
  border-radius: 10px;
  padding: 9px 18px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.mx-btn.ghost:hover { color: #fff; background: rgba(140, 170, 255, 0.12); }
.mx-btn.go {
  border-color: transparent;
  color: #fff;
  background: linear-gradient(160deg, #5c83ec, #3f63d6);
  box-shadow: 0 8px 24px rgba(76, 116, 223, 0.45);
}
.mx-btn.go:disabled { opacity: 0.35; cursor: not-allowed; box-shadow: none; }

.mx-empty {
  padding: 46px 12px;
  text-align: center;
  color: #7f93c4;
}
.mx-empty i { font-size: 30px; margin-bottom: 8px; color: #7f93c4; }
.mx-empty p { font-weight: 600; color: #dbe6ff; }
.mx-empty small { font-size: 12px; }

@media (max-width: 640px) {
  .mx-shell {
    width: calc(100vw - 40px);
    max-height: calc(100dvh - 24px);
  }
  .mx-bar {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 6px 10px;
    padding: 14px 12px 4px;
  }
  .mx-title {
    grid-column: 1;
    grid-row: 1;
  }
  .mx-status {
    grid-column: 1 / -1;
    grid-row: 2;
    justify-self: stretch;
    text-align: left;
  }
  .mx-x {
    grid-column: 2;
    grid-row: 1;
  }
  .mx-scroll {
    min-height: 0;
    padding: 6px 8px 0;
  }
  .mx-foot {
    padding: 8px 12px 12px;
  }
  .mx-btn.go {
    width: 100%;
  }
}
</style>
