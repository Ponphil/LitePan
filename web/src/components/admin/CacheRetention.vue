<template>
  <div class="cache-retention-page">
    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stats-card">
        <div class="stats-icon">
          <i class="fas fa-folder"></i>
        </div>
        <div class="stats-content">
          <div class="stats-number">{{ stats.total_count }}</div>
          <div class="stats-label">配置目录</div>
        </div>
      </div>
      <div class="stats-card">
        <div class="stats-icon running">
          <i class="fas fa-play"></i>
        </div>
        <div class="stats-content">
          <div class="stats-number">{{ stats.running_count }}</div>
          <div class="stats-label">运行中</div>
        </div>
      </div>
      <div class="stats-card">
        <div class="stats-icon paused">
          <i class="fas fa-pause"></i>
        </div>
        <div class="stats-content">
          <div class="stats-number">{{ stats.paused_count }}</div>
          <div class="stats-label">已暂停</div>
        </div>
      </div>
    </div>

    <!-- 启动倒计时 -->
    <div v-if="startupRemaining > 0" class="startup-countdown-banner">
      <i class="fas fa-hourglass-half fa-spin"></i>
      <span>任务启动中，预计 <strong>{{ startupRemaining }}</strong> 秒后开始执行...</span>
    </div>

    <!-- 配置限制提示 -->
    <div v-if="configs.length >= 6" class="limit-warning">
      <i class="fas fa-exclamation-triangle"></i>
      已达到最大配置数量(6个)。如需添加更多目录，建议：
      <ul>
        <li>选择一个父目录并开启"无限递归"</li>
        <li>删除不需要的配置</li>
      </ul>
    </div>

    <!-- 配置列表 -->
    <div class="config-list">
      <div class="list-header">
        <div class="list-filters">
          <label>状态筛选:</label>
          <div class="custom-select" :class="{ open: statusFilterOpen }" @click="toggleStatusFilter" data-type="status-filter">
            <div class="select-trigger">
              <span class="select-value">{{ getStatusFilterText() }}</span>
              <svg class="select-arrow" width="16" height="16" viewBox="0 0 20 20" fill="none">
                <path stroke="#6b7280" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="m6 8 4 4 4-4"/>
              </svg>
            </div>
            <div class="select-dropdown" v-show="statusFilterOpen">
              <div class="select-option" @click.stop="setStatusFilter('all')">全部</div>
              <div class="select-option" @click.stop="setStatusFilter('running')">运行中</div>
              <div class="select-option" @click.stop="setStatusFilter('paused')">已暂停</div>
              <div class="select-option" @click.stop="setStatusFilter('error')">错误</div>
            </div>
          </div>
        </div>
        <div class="action-buttons">
          <button class="btn btn-secondary" @click="refreshAll" :disabled="loading">
            <i class="fas fa-play-circle"></i> 全部执行
          </button>
          <button v-if="!hideHeaderAdd" class="btn btn-primary" @click="showAddDialog" :disabled="configs.length >= 6">
            <i class="fas fa-plus"></i> 添加目录
          </button>
        </div>
      </div>
      
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>目录信息</th>
              <th>最后刷新</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="config in filteredConfigs" :key="config.id" class="config-row">
              <td>
                <div class="config-main" :title="getConfigTitle(config)">
                  <div class="config-name">
                    <div class="config-path">{{ config.path }}</div>
                    <span class="config-inline-status" :class="config.status === 'running' ? 'running' : 'paused'">
                      {{ config.status === 'running' ? '已启用' : '已禁用' }}
                    </span>
                  </div>
                  <div class="config-meta">{{ getConfigMeta(config) }}</div>
                </div>
              </td>
              <td>
                <div class="refresh-inline" :title="getRefreshTitle(config)">
                  <span class="refresh-status-icon" :class="getRefreshStatusClass(config)">
                    <svg v-if="config.last_refresh_status === 'success' && !isConfigExecuting(config.id)" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="m3.5 8.5 3 3 6-7" />
                    </svg>
                    <svg v-else-if="config.last_refresh_status === 'error' && !isConfigExecuting(config.id)" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M8 4.25v4.5" />
                      <circle cx="8" cy="11.75" r=".75" fill="currentColor" stroke="none" />
                      <path d="M8 1.75 14 14.25H2L8 1.75Z" />
                    </svg>
                    <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <circle cx="8" cy="8" r="5.75" />
                      <path d="M8 5.25v3.25l2 1.25" />
                    </svg>
                  </span>
                  <span class="refresh-switch">
                    <span class="refresh-text">{{ getRefreshPrimaryText(config) }}</span>
                    <span class="refresh-summary">{{ getRefreshSummary(config) }}</span>
                  </span>
                </div>
              </td>
              <td>
                <div class="config-action-buttons">
                  <div class="config-status-switch" role="group" aria-label="缓存保持任务启用切换">
                    <button
                      type="button"
                      class="config-status-btn"
                      :class="{ active: config.status === 'running' }"
                      title="启用"
                      @click="setConfigEnabled(config, true)"
                    >
                      <span class="config-status-text">启</span>
                    </button>
                    <button
                      type="button"
                      class="config-status-btn"
                      :class="{ active: config.status !== 'running' }"
                      title="禁用"
                      @click="setConfigEnabled(config, false)"
                    >
                      <span class="config-status-text">禁</span>
                    </button>
                  </div>
                  <button v-if="isConfigExecuting(config.id)" type="button" class="config-action-btn force-stop" title="强制停止" @click="forceStopConfig(config.id)">
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <rect x="3" y="3" width="10" height="10" rx="1.5" />
                    </svg>
                  </button>
                  <button v-else type="button" class="config-action-btn" title="立即执行" @click="refreshConfig(config.id)">
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M8 2v12" />
                      <path d="m4.5 5.5 3.5-3.5 3.5 3.5" />
                    </svg>
                  </button>
                  <button type="button" class="config-action-btn" title="修改" @click="editConfig(config)">
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M2.5 13.5h3l8-8-3-3-8 8v3z" />
                      <path d="M9.5 3.5l3 3" />
                    </svg>
                  </button>
                  <button type="button" class="config-action-btn danger" title="删除" @click="deleteConfig(config.id)">
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M3 4h10" />
                      <path d="M6 4V3.2c0-.7.5-1.2 1.2-1.2h1.6c.7 0 1.2.5 1.2 1.2V4" />
                      <path d="M5 6v7c0 .6.4 1 1 1h4c.6 0 1-.4 1-1V6" />
                      <path d="M7 8v4" />
                      <path d="M9 8v4" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 添加目录模态框 -->
    <div v-if="showAddModal" class="dialog-overlay">
      <div class="dialog" @click="handleModalClick">
        <div class="dialog-header">
          <h3>{{ newConfig.id ? '修改目录' : '添加目录' }}</h3>
          <button @click="closeAddDialog" class="close-btn">&times;</button>
        </div>
        
        <div class="dialog-content add-config-form">
          <!-- 账号和目录选择 -->
          <div class="form-row">
            <div class="form-group">
              <label>选择账号</label>
              <div class="custom-select" :class="{ open: accountSelectOpen }" @click.stop="toggleAccountSelect" data-type="account-select">
                <div class="select-trigger">
                  <span class="select-value">{{ selectedAccount ? selectedAccount.name : '请选择账号' }}</span>
                  <svg class="select-arrow" width="16" height="16" viewBox="0 0 20 20" fill="none">
                    <path stroke="#6b7280" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="m6 8 4 4 4-4"/>
                  </svg>
                </div>
                <div class="select-dropdown" v-show="accountSelectOpen">
                  <div 
                    v-for="account in accounts" 
                    :key="account.id"
                    class="select-option" 
                    @click.stop="selectAccount(account)"
                  >
                    {{ account.name }}
                  </div>
                </div>
              </div>
            </div>
            
            <div class="form-group">
              <label>选择目录</label>
              <div class="input-group">
                <input 
                  v-model="newConfig.path" 
                  type="text" 
                  class="form-input" 
                  placeholder="请选择目录"
                  readonly
                >
                <button 
                  type="button" 
                  class="btn-browse" 
                  @click="browseDirectory"
                >
                  浏览
                </button>
              </div>
            </div>
          </div>
          
          <!-- 配置参数 -->
          <div class="form-row">
            <div class="form-group">
              <label>递归模式</label>
              <div class="custom-select" :class="{ open: recursiveSelectOpen }" @click.stop="toggleRecursiveSelect" data-type="recursive-select">
                <div class="select-trigger">
                  <span class="select-value">{{ newConfig.recursive ? '无限递归' : '单层缓存' }}</span>
                  <svg class="select-arrow" width="16" height="16" viewBox="0 0 20 20" fill="none">
                    <path stroke="#6b7280" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="m6 8 4 4 4-4"/>
                  </svg>
                </div>
                <div class="select-dropdown" v-show="recursiveSelectOpen">
                  <div class="select-option" @click.stop="setRecursiveMode(false)">单层缓存</div>
                  <div class="select-option" @click.stop="setRecursiveMode(true)">无限递归</div>
                </div>
              </div>
            </div>

            <div class="form-group">
              <label>API额外补偿间隔(毫秒)</label>
              <input
                v-model.number="newConfig.api_interval"
                type="number"
                class="form-input"
                min="0"
                max="5000"
              >
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>刷新间隔(分钟)</label>
              <input
                v-model.number="newConfig.refresh_interval"
                type="number"
                class="form-input"
                min="1"
                max="1440"
              >
            </div>

            <div class="form-group">
              <label>执行时间段</label>
              <div class="time-window-display" @click="timePickerVisible = true">
                <span>{{ timeWindowDisplay }}</span>
                <svg class="time-window-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="8.5"></circle>
                  <path d="M12 7.5v5l3.2 2"></path>
                </svg>
              </div>
            </div>
          </div>
        </div>

        <div class="dialog-footer">
          <button @click="saveConfig" class="btn btn-primary" :disabled="saving">
            <i class="fas fa-save"></i> {{ newConfig.id ? '更新配置' : '保存配置' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 时间滚轮选择器 -->
    <TimeWheelPicker
      :visible="timePickerVisible"
      :startTime="newConfig.time_start"
      :endTime="newConfig.time_end"
      :allDay="newConfig.time_window_mode === 'always'"
      @confirm="onTimeWheelConfirm"
      @cancel="closeTimePicker"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import axios from 'axios'
import { useModal } from '@/composables/useModal'
import { useFolderSelector } from '@/composables/useFolderSelector'
import TimeWheelPicker from '@/components/TimeWheelPicker.vue'
import { formatDate } from '@/utils/format.js'

defineProps({
  hideHeaderAdd: {
    type: Boolean,
    default: false
  }
})

// 响应式数据
const loading = ref(false)
const configs = ref([])
const startupRemaining = ref(0)
const accounts = ref([])
const stats = ref({
  total_count: 0,
  running_count: 0,
  paused_count: 0,
  executing_task_ids: []  // 当前正在执行的任务ID列表
})

// 轮询定时器
let statusPollingTimer = null

// 状态筛选
const statusFilter = ref('all')

// 添加配置相关
const showAddModal = ref(false)
const selectedAccount = ref(null)
const selectedPath = ref('')
// 全局默认值（从 API 加载，兜底写死）
const defaultSettings = ref({
  api_interval: 200,
  refresh_interval: 60,
})

const newConfig = ref({
  account_id: null,
  parent_id: '',
  path: '',
  recursive: false,
  api_interval: defaultSettings.value.api_interval,
  refresh_interval: defaultSettings.value.refresh_interval,
  time_window_mode: 'always',
  time_start: '00:00',
  time_end: '00:00'
})
const saving = ref(false)

// 时间选择器
const timePickerVisible = ref(false)

const timeWindowDisplay = computed(() => {
  if (newConfig.value.time_window_mode === 'always') return '全天'
  const [sh, sm] = newConfig.value.time_start.split(':').map(Number)
  const [eh, em] = newConfig.value.time_end.split(':').map(Number)
  const sMin = sh * 60 + sm
  const eMin = eh * 60 + em
  if (sMin < eMin) return `${newConfig.value.time_start}-${newConfig.value.time_end}`
  if (sMin === eMin) return '全天'
  return `${newConfig.value.time_start}-次日${newConfig.value.time_end}`
})

function onTimeWheelConfirm({ startTime, endTime, allDay }) {
  if (allDay) {
    newConfig.value.time_window_mode = 'always'
  } else {
    newConfig.value.time_window_mode = 'custom'
    newConfig.value.time_start = startTime
    newConfig.value.time_end = endTime
  }
  timePickerVisible.value = false
}

function closeTimePicker() {
  timePickerVisible.value = false
}

// 模态框
const { confirm } = useModal()
const { selectFolder } = useFolderSelector()

// 自定义下拉框状态
const statusFilterOpen = ref(false)
const accountSelectOpen = ref(false)
const recursiveSelectOpen = ref(false)
// 计算属性
const filteredConfigs = computed(() => {
  if (statusFilter.value === 'all') {
    return configs.value
  }
  return configs.value.filter(config => config.status === statusFilter.value)
})

const escapeHtml = (text) => {
  if (text === null || text === undefined) return ''
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }
  return String(text).replace(/[&<>"']/g, char => map[char])
}



// 方法
const loadConfigs = async () => {
  try {
    const response = await axios.get('/api/cache-retention/configs')
    
    if (response.data.success) {
      configs.value = response.data.data
      startupRemaining.value = response.data.startup_remaining || 0
      // 同时加载账号列表，用于显示账号名称
      await loadAccounts()
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    window.appNotification.error('加载配置失败')
  }
}

const loadStats = async () => {
  try {
    const response = await axios.get('/api/cache-retention/stats')
    
    if (response.data.success) {
      stats.value = response.data.data
    } else {
      console.error('加载统计失败:', response.data.message)
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 轮询检查执行状态
const startStatusPolling = () => {
  stopStatusPolling()
  const prevExecuting = new Set(stats.value.executing_task_ids || [])
  statusPollingTimer = setInterval(async () => {
    await loadStats()
    if (stats.value.executing_task_ids?.length > 0) {
      await loadConfigs()
    }
    // 检测刚完成的任务并显示结果
    const currentExecuting = new Set(stats.value.executing_task_ids || [])
    for (const id of prevExecuting) {
      if (!currentExecuting.has(id)) {
        const config = configs.value.find(c => c.id === id)
        if (config) {
          const fileCount = Number(config?.file_count || 0)
          const durationText = config?.last_duration_ms ? `，${formatDuration(config.last_duration_ms)}` : ''
          window.appNotification.success(
            `缓存刷新完成 — ${config.scanned_dirs || 0} 个目录 / ${formatFileCount(fileCount)} 个文件${durationText}`
          )
        }
      }
    }
    prevExecuting.clear()
    for (const id of currentExecuting) prevExecuting.add(id)

    if (!stats.value.executing_task_ids || stats.value.executing_task_ids.length === 0) {
      stopStatusPolling()
      await loadConfigs()
    }
  }, 2000)
}

const stopStatusPolling = () => {
  if (statusPollingTimer) {
    clearInterval(statusPollingTimer)
    statusPollingTimer = null
  }
}

const handleVisibilityChange = () => {
  if (!document.hidden && stats.value?.executing_task_ids?.length > 0) {
    startStatusPolling()
  }
}

// 检查配置是否正在执行
const isConfigExecuting = (configId) => {
  return stats.value.executing_task_ids && stats.value.executing_task_ids.includes(configId)
}

const loadAccounts = async () => {
  try {
    const response = await axios.get('/api/cache-retention/accounts')
    
    if (response.data.success) {
      accounts.value = response.data.data
    } else {
      console.error('加载账号失败:', response.data.message)
      window.appNotification.error('加载账号失败: ' + response.data.message)
    }
  } catch (error) {
    console.error('加载账号失败:', error)
    window.appNotification.error('加载账号失败: ' + error.message)
  }
}

const showAddDialog = async () => {
  try {
    // 先加载账号列表
    await loadAccounts()
    showAddModal.value = true
    // 重置表单
    selectedAccount.value = null
    newConfig.value = {
      id: null, // 重置ID
      account_id: null,
      parent_id: '',
      path: '',
      recursive: false,
      api_interval: defaultSettings.value.api_interval,
      refresh_interval: defaultSettings.value.refresh_interval,
      time_window_mode: 'always',
      time_start: '00:00',
      time_end: '00:00'
    }

    // 添加ESC键关闭功能
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && showAddModal.value) {
        const activeModal = document.querySelector('.modern-modal-overlay')
        if (!activeModal) {
          showAddModal.value = false
          statusFilterOpen.value = false
          accountSelectOpen.value = false
          recursiveSelectOpen.value = false
          document.removeEventListener('keydown', handleKeyDown)
          // 移除焦点，避免自动定位到按钮
          if (document.activeElement) {
            document.activeElement.blur()
          }
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown)
  } catch (error) {
    console.error('加载账号失败:', error)
    window.appNotification.error('加载账号失败')
  }
}

let closeAddDialog = () => {
  showAddModal.value = false
  statusFilterOpen.value = false
  accountSelectOpen.value = false
  recursiveSelectOpen.value = false
}

const saveConfig = async () => {
  // 验证必填字段
  if (!selectedAccount.value) {
    window.appNotification.warning('请选择账号')
    return
  }
  
  if (!newConfig.value.path) {
    window.appNotification.warning('请选择目录')
    return
  }
  
  if (newConfig.value.api_interval === '' || newConfig.value.api_interval === null || newConfig.value.api_interval === undefined || newConfig.value.api_interval < 0 || newConfig.value.api_interval > 5000) {
    window.appNotification.warning('API额外补偿间隔必须在0-5000毫秒之间')
    return
  }
  
  if (!newConfig.value.refresh_interval || newConfig.value.refresh_interval < 1 || newConfig.value.refresh_interval > 1440) {
    window.appNotification.warning('刷新间隔必须在1-1440分钟之间')
    return
  }
  
  saving.value = true
  try {
    const configData = {
      account_id: selectedAccount.value.id,
      parent_id: newConfig.value.parent_id,
      path: newConfig.value.path,
      recursive: newConfig.value.recursive,
      api_interval: newConfig.value.api_interval,
      refresh_interval: newConfig.value.refresh_interval,
      time_window_enabled: newConfig.value.time_window_mode === 'custom',
      time_start: newConfig.value.time_start,
      time_end: newConfig.value.time_end
    }

    // 判断是新增还是编辑
    const isEdit = newConfig.value.id
    const url = isEdit ? `/api/cache-retention/configs/${newConfig.value.id}` : '/api/cache-retention/configs'
    const method = isEdit ? 'put' : 'post'
    
    const response = await axios[method](url, configData)
    
    if (response.data.success || response.data.message) {
      window.appNotification.success(response.data.message || (isEdit ? '配置更新成功' : '配置保存成功'))
      closeAddDialog()
      await loadConfigs()
      await loadStats()
      if (!isEdit) {
        startStatusPolling()
      }
    } else {
      window.appNotification.error(response.data.message || '保存失败')
    }
  } catch (error) {
    console.error('保存配置失败:', error)
    window.appNotification.error('保存配置失败: ' + (error.response?.data?.message || error.message))
  } finally {
    saving.value = false
  }
}

const toggleConfig = async (configId) => {
  try {
    const response = await axios.post(`/api/cache-retention/configs/${configId}/toggle`)
    if (response.data.message) {
      window.appNotification.success(response.data.message)
    }
    await loadConfigs()
    await loadStats()
  } catch (error) {
    console.error('切换状态失败:', error)
    window.appNotification.error('切换状态失败')
  }
}

const setConfigEnabled = async (config, enabled) => {
  const isRunning = config.status === 'running'
  if ((enabled && isRunning) || (!enabled && !isRunning)) {
    return
  }
  await toggleConfig(config.id)
}

const refreshConfig = async (configId) => {
  try {
    await axios.post(`/api/cache-retention/configs/${configId}/refresh`)
    startStatusPolling()
    // 等待片刻后检查结果：若任务已秒完成则直接展示反馈
    setTimeout(async () => {
      await loadConfigs()
      await loadStats()
      if (!isConfigExecuting(configId)) {
        const config = configs.value.find(c => c.id === configId)
        if (config && config.last_refresh) {
          const fileCount = Number(config?.file_count || 0)
          const durationText = config?.last_duration_ms ? `，${formatDuration(config.last_duration_ms)}` : ''
          window.appNotification.success(
            `缓存刷新完成 — ${config.scanned_dirs || 0} 个目录 / ${formatFileCount(fileCount)} 个文件${durationText}`
          )
          return
        }
      }
      window.appNotification.success('立即执行已启动')
    }, 800)
  } catch (error) {
    console.error('立即执行失败:', error)
    window.appNotification.error('立即执行失败')
  }
}

const forceStopConfig = async (configId) => {
  stopStatusPolling()
  try {
    const response = await axios.post(`/api/cache-retention/configs/${configId}/force-stop`)
    if (response.data.success) {
      window.appNotification.success(response.data.message || '已强制停止')
    } else {
      window.appNotification.info(response.data.message || '任务未在执行中')
    }
    await loadConfigs()
    await loadStats()
    if (stats.value?.executing_task_ids?.length > 0) {
      startStatusPolling()
    }
  } catch (error) {
    console.error('强制停止失败:', error)
    window.appNotification.error('强制停止失败')
    startStatusPolling()
  }
}

const refreshAll = async () => {
  try {
    await axios.post('/api/cache-retention/refresh-all')
    window.appNotification.success('全部执行已启动')
    // 启动轮询检查执行状态
    startStatusPolling()
  } catch (error) {
    console.error('全部执行失败:', error)
    window.appNotification.error('全部执行失败')
  }
}

const deleteConfig = async (configId) => {
  try {
    // 使用统一的模态框确认
    await confirm({
      title: '确认删除',
      content: '确定要删除这个缓存保持配置吗？\n\n删除后该配置将停止缓存刷新，但已缓存的目录数据会保留。',
      confirmText: '删除',
      confirmClass: 'btn-danger',
      icon: 'trash'
    })

    const response = await axios.delete(`/api/cache-retention/configs/${configId}?clear_cache=false`)
    
    window.appNotification.success('删除成功')
    await loadConfigs()
    await loadStats()
  } catch (error) {
    // 用户取消删除
    if (error.message !== 'Modal closed') {
      window.appNotification.error('删除失败: ' + (error.response?.data?.message || error.message))
    }
  }
}

const editConfig = (config) => {
  // 填充编辑数据
  selectedAccount.value = {
    id: config.account_id,
    name: config.account_name
  }
  newConfig.value = {
    id: config.id, // 添加ID用于编辑模式
    account_id: config.account_id,
    parent_id: config.parent_id,
    path: config.path,
    recursive: config.recursive,
    api_interval: config.api_interval,
    refresh_interval: config.refresh_interval,
    time_window_mode: config.time_window_enabled ? 'custom' : 'always',
    time_start: config.time_start || '00:00',
    time_end: config.time_end || '00:00'
  }
  
  // 显示编辑模态框
  showAddModal.value = true
}

const browseDirectory = async () => {
  if (!selectedAccount.value) {
    window.appNotification.warning('请先选择账号')
    return
  }
  const result = await selectFolder(selectedAccount.value.id, {
    initialPath: newConfig.value.path
  })
  if (result) {
    newConfig.value.path = result.path
    newConfig.value.parent_id = result.id
  }
}

// 工具函数
const getStatusText = (status) => {
  const statusMap = {
    'running': '运行中',
    'paused': '已暂停',
    'error': '错误',
    'refreshing': '刷新中'
  }
  return statusMap[status] || status
}

const formatFileCount = (count) => {
  if (count === 0) return '-'
  return count.toLocaleString()
}

const formatDuration = (ms) => {
  if (!ms || ms <= 0) return ''
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const min = Math.floor(seconds / 60)
  const sec = seconds % 60
  return `${min}m${sec}s`
}

const formatLastRefresh = (timestamp) => {
  if (!timestamp) return '从未刷新'
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  return Math.floor(diff / 86400000) + '天前'
}

const formatInterval = (minutes) => {
  if (minutes < 60) return `${minutes}分钟`
  if (minutes < 1440) {
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    if (remainingMinutes === 0) {
      return `${hours}小时`
    } else {
      return `${hours}小时${remainingMinutes}分钟`
    }
  }
  const days = Math.floor(minutes / 1440)
  const remainingHours = Math.floor((minutes % 1440) / 60)
  const remainingMinutes = minutes % 60
  if (remainingHours === 0 && remainingMinutes === 0) {
    return `${days}天`
  } else if (remainingMinutes === 0) {
    return `${days}天${remainingHours}小时`
  } else {
    return `${days}天${remainingHours}小时${remainingMinutes}分钟`
  }
}




const getConfigMeta = (config) => {
  const fileCount = Number(config?.file_count || 0)
  const fileText = config?.last_refresh ? `${formatFileCount(fileCount)} 个文件` : '待统计'
  const recursiveText = config?.recursive ? '无限递归' : '单层缓存'
  return [
    config?.account_name || '未知账号',
    formatInterval(Number(config?.refresh_interval || 0)),
    recursiveText,
    fileText
  ].join(' · ')
}

const getConfigTitle = (config) => {
  return [
    config?.path || '/',
    `账号：${config?.account_name || '未知账号'}`,
    `刷新间隔：${formatInterval(Number(config?.refresh_interval || 0))}`,
    `递归方式：${config?.recursive ? '无限递归' : '单层缓存'}`,
    `文件数：${config?.last_refresh ? formatFileCount(Number(config?.file_count || 0)) : '待统计'}`,
    `创建时间：${formatDate(config?.created_at, '未知时间')}`
  ].join('\n')
}

const getRefreshStatusClass = (config) => {
  if (isConfigExecuting(config.id)) return 'executing'
  return config?.last_refresh_status || 'pending'
}

const getRefreshPrimaryText = (config) => {
  if (isConfigExecuting(config.id)) {
    const elapsedText = getConfigElapsedText(config)
    let text = '执行中'
    if (config.scanned_dirs > 0 || config.scanned_files > 0) {
      text += ` — 已扫 ${config.scanned_dirs} 目录 / ${config.scanned_files} 文件`
    }
    if (elapsedText) text += `，${elapsedText}`
    return text
  }
  return formatLastRefresh(config?.last_refresh)
}

const getRefreshSummary = (config) => {
  if (isConfigExecuting(config.id)) return '刷新中...'
  if (!config?.last_refresh) return '待执行'
  const parts = []
  const fileCount = Number(config?.file_count || 0)
  parts.push(config?.last_refresh ? `${formatFileCount(fileCount)} 个文件` : '待统计')
  if (config?.last_duration_ms > 0) {
    parts.push(formatDuration(config.last_duration_ms))
  }
  parts.push(formatInterval(Number(config?.refresh_interval || 0)))
  return parts.join(' · ')
}

const getRefreshTitle = (config) => {
  if (isConfigExecuting(config.id)) {
    return `当前状态：执行中\n${getConfigMeta(config)}`
  }
  return [
    `最后刷新：${formatLastRefresh(config?.last_refresh)}`,
    `刷新状态：${config?.last_refresh_status || '待执行'}`,
    getConfigMeta(config)
  ].join('\n')
}

const getConfigElapsedText = (config) => {
  const currentDurationMs = Number(config?.current_duration_ms || 0)
  if (currentDurationMs > 0) {
    const elapsed = Math.max(1, Math.floor(currentDurationMs / 1000))
    if (elapsed < 60) return `耗时 ${elapsed}s`
    const min = Math.floor(elapsed / 60)
    const sec = elapsed % 60
    return `耗时 ${min}m${sec}s`
  }
  if (!config?.started_at) return ''
  const started = new Date(config.started_at)
  const now = new Date()
  const elapsedRaw = Math.floor((now - started) / 1000)
  const elapsed = Math.max(1, Number.isFinite(elapsedRaw) ? elapsedRaw : 0)
  if (elapsed < 60) return `耗时 ${elapsed}s`
  const min = Math.floor(elapsed / 60)
  const sec = elapsed % 60
  return `耗时 ${min}m${sec}s`
}

const getAccountName = (accountId) => {
  const account = accounts.value.find(acc => acc.id === accountId)
  return account ? account.name : '未知账号'
}

// 自定义下拉框逻辑
const toggleStatusFilter = () => {
  statusFilterOpen.value = !statusFilterOpen.value
  if (statusFilterOpen.value) {
    nextTick(() => {
      positionDropdown('status-filter')
    })
  }
}

const setStatusFilter = (value) => {
  statusFilter.value = value
  statusFilterOpen.value = false
}

const getStatusFilterText = () => {
  const statusMap = {
    'all': '全部',
    'running': '运行中',
    'paused': '已暂停',
    'error': '错误'
  }
  return statusMap[statusFilter.value] || statusFilter.value
}

const toggleAccountSelect = () => {
  accountSelectOpen.value = !accountSelectOpen.value
  if (accountSelectOpen.value) {
    nextTick(() => {
      positionDropdown('account-select')
    })
  }
}

const selectAccount = (account) => {
  selectedAccount.value = account
  accountSelectOpen.value = false
  if (account) {
    newConfig.value.account_id = account.id
  } else {
    newConfig.value.account_id = null
  }
  newConfig.value.path = ''
  newConfig.value.parent_id = ''
}

const toggleRecursiveSelect = () => {
  recursiveSelectOpen.value = !recursiveSelectOpen.value
  if (recursiveSelectOpen.value) {
    nextTick(() => {
      positionDropdown('recursive-select')
    })
  }
}

const setRecursiveMode = (recursive) => {
  newConfig.value.recursive = recursive
  recursiveSelectOpen.value = false
}

// 动态定位下拉菜单
const positionDropdown = (type) => {
  let selectElement
  if (type === 'status-filter') {
    selectElement = document.querySelector('.list-filters .custom-select')
  } else if (type === 'account-select') {
    selectElement = document.querySelector('.dialog-content .custom-select[data-type="account-select"]')
  } else if (type === 'recursive-select') {
    selectElement = document.querySelector('.dialog-content .custom-select[data-type="recursive-select"]')
  }
  
  if (!selectElement) return
  
  const dropdown = selectElement.querySelector('.select-dropdown')
  if (!dropdown) return
  
  const rect = selectElement.getBoundingClientRect()
  const viewportHeight = window.innerHeight
  const dropdownHeight = 200 // max-height
  
  // 计算位置
  let top = rect.bottom + 4
  let left = rect.left
  let width = rect.width
  
  // 检查是否会超出底部
  if (top + dropdownHeight > viewportHeight) {
    top = rect.top - dropdownHeight - 4
  }
  
  // 应用位置
  dropdown.style.position = 'fixed'
  dropdown.style.top = `${top}px`
  dropdown.style.left = `${left}px`
  dropdown.style.width = `${width}px`
  dropdown.style.zIndex = '100000'
}

const handleClickOutside = (event) => {
  // 关闭状态筛选下拉框
  if (statusFilterOpen.value && !event.target.closest('.list-filters .custom-select')) {
    statusFilterOpen.value = false
  }
  
  // 关闭账号选择下拉框
  if (accountSelectOpen.value && !event.target.closest('.dialog-content .custom-select[data-type="account-select"]')) {
    accountSelectOpen.value = false
  }

  // 关闭递归模式下拉框
  if (recursiveSelectOpen.value && !event.target.closest('.dialog-content .custom-select[data-type="recursive-select"]')) {
    recursiveSelectOpen.value = false
  }

}

// 添加模态框内部点击事件处理
const handleModalClick = (event) => {
  // 如果点击的是模态框内部，但不是下拉菜单，则关闭所有下拉菜单
  if (event.target.closest('.dialog') && !event.target.closest('.custom-select')) {
    statusFilterOpen.value = false
    accountSelectOpen.value = false
    recursiveSelectOpen.value = false
  }
}

// 生命周期
const loadDefaults = async () => {
  try {
    const response = await axios.get('/api/cache-retention/defaults')
    if (response.data.success) {
      defaultSettings.value.refresh_interval = Number(response.data.data.refresh_interval) || 60
      defaultSettings.value.api_interval = Number(response.data.data.api_interval) || 200
    }
  } catch (error) {
    console.error('加载缓存保持默认值失败:', error)
  }
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  loadDefaults()
  await loadConfigs()
  await loadStats()
  if (stats.value?.executing_task_ids?.length > 0) {
    startStatusPolling()
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  stopStatusPolling()
})

defineExpose({
  showAddDialog
})
</script>

<style scoped>
.cache-retention-page {
  /* 移除padding，使用父容器的padding */
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.stats-card {
  background: #fff;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  gap: 16px;
}

.stats-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #4C74DF 0%, #02A6F0 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
}

.stats-icon.running {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.stats-icon.paused {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.stats-content {
  flex: 1;
}

.stats-number {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1;
}

.stats-label {
  font-size: 14px;
  color: #64748b;
  margin-top: 4px;
}

/* 按钮组 */
.btn-group {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

/* 按钮样式 - 确保优先级 */
.btn {
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(135deg, #4C74DF 0%, #02A6F0 100%) !important;
  color: white !important;
  box-shadow: 0 2px 4px rgba(76, 116, 223, 0.3);
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #3b5bdb, #1e88e5) !important;
  color: white !important;
  box-shadow: 0 4px 12px rgba(76, 116, 223, 0.4);
}

.btn-primary:active:not(:disabled) {
  background: linear-gradient(135deg, #2d4bdb, #1565c0) !important;
  transform: translateY(1px);
  box-shadow: 0 2px 4px rgba(76, 116, 223, 0.3);
}

.btn-secondary {
  background: #fff !important;
  color: #1e293b !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.btn-secondary:hover:not(:disabled) {
  background: #f8fafc !important;
  color: #1e293b !important;
  border-color: #cbd5e1 !important;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

/* 限制警告 */
.limit-warning {
  background: #fdf6ec;
  border: 1px solid #f5dab1;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 20px;
  color: #b88230;
  font-size: 14px;
}

.limit-warning i {
  margin-right: 8px;
}

.limit-warning ul {
  margin: 8px 0 0 20px;
}

/* 配置列表 */
.config-list {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.list-header {
  padding: 20px;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.list-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.list-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.list-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.list-filters label {
  font-size: 14px;
  color: #606266;
  margin: 0;
}

/* 自定义下拉框样式 */
.custom-select {
  position: relative;
  width: 100%;
  min-width: 150px;
}

.select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.2s ease;
  height: 40px;
  box-sizing: border-box;
  font-size: 14px;
  color: #374151;
}

.select-trigger:hover {
  border-color: #9ca3af;
}

.custom-select.open .select-trigger {
  border-color: #4C74DF;
  box-shadow: 0 0 0 2px rgba(76, 116, 223, 0.1);
}

.select-value {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.select-arrow {
  transition: transform 0.2s ease;
  color: #6b7280;
}

.custom-select.open .select-arrow {
  transform: rotate(180deg);
}

.select-dropdown {
  position: fixed;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 100000;
  max-height: 200px;
  overflow-y: auto;
}

.custom-select.open .select-dropdown {
  display: block;
}

.select-option {
  padding: 10px 12px;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
  transition: background-color 0.2s ease;
}

.select-option:hover {
  background-color: #f8fafc;
}

.select-option:first-child {
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
}

.select-option:last-child {
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
}

/* 表格容器样式 */
.table-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  margin-top: 20px;
}

/* 确保表格底部圆角 */
.data-table tbody tr:last-child td:first-child {
  border-bottom-left-radius: 12px;
}

.data-table tbody tr:last-child td:nth-child(3) {
  border-bottom-right-radius: 12px;
}

.table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.table th {
  background: #f8fafc;
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #e5e7eb;
  font-size: 14px;
}

.table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}

.table tbody tr:last-child td {
  border-bottom: none;
}

.table tbody tr:hover {
  background: #f9fafb;
}

/* 目录信息 */
.directory-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 40px;
}

.directory-info i {
  color: #409eff;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  line-height: 1;
  min-width: 16px;
  min-height: 16px;
  flex-shrink: 0;
}

.path {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.account-name {
  color: #909399;
  font-size: 12px;
  margin-bottom: 4px;
}

.config-summary {
  display: flex;
  gap: 8px;
}

.tag {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #fff;
}

.tag.interval {
  background: #409eff;
}

.tag.api-interval {
  background: #909399;
}

.tag.recursive {
  background: #e1f3d8;
  color: #67c23a;
}



/* 进度条 */
.progress-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  width: 60px;
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #409eff;
  transition: width 0.3s;
}

.progress-text {
  font-size: 12px;
  color: #909399;
}

/* 刷新信息 */
.refresh-info {
  font-size: 12px;
}

.refresh-info .status {
  margin-top: 2px;
}

.refresh-info .status.success {
  color: #67c23a;
}

.refresh-info .status.error {
  color: #f56c6c;
}

.refresh-info .status.executing {
  color: #409eff;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.config-action-buttons {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}

.config-action-btn {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.config-action-btn svg {
  width: 16px;
  height: 16px;
}

.config-action-btn:hover {
  color: #334155;
  background: #f8fafc;
  border-color: #d8e0ea;
}

.config-action-btn.force-stop {
  color: #ef4444;
}

.config-action-btn.force-stop:hover {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.18);
  color: #dc2626;
}

.config-action-btn.danger:hover {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.18);
  color: #ef4444;
}

.config-status-switch {
  display: inline-flex;
  align-items: center;
  height: 34px;
  padding: 2px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  flex-shrink: 0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  gap: 2px;
  box-sizing: border-box;
}

.config-status-btn {
  min-width: 30px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.config-status-btn:hover {
  color: #334155;
  background: #f8fafc;
}

.config-status-btn.active {
  background: #eef4ff;
  color: #2563eb;
}

.config-status-text {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
}

/* 新的表格样式 */
.data-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  table-layout: fixed;
}

.data-table th {
  background: #f8fafc;
  padding: 14px 16px;
  text-align: left;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
}

.data-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: middle;
}

.data-table th:nth-child(1),
.data-table td:nth-child(1) {
  width: 46%;
}

.data-table th:nth-child(2),
.data-table td:nth-child(2) {
  width: 32%;
}

.data-table th:last-child,
.data-table td:last-child {
  width: 200px;
  text-align: right;
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.config-row {
  transition: background-color 0.18s ease;
}

.config-row:hover {
  background: #fafcff;
}

.config-main {
  min-width: 0;
}

.config-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.config-path {
  min-width: 0;
  color: #0f172a;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.config-inline-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  min-width: 50px;
  height: 24px;
  padding: 0 10px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}

.config-inline-status.running {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

.config-inline-status.paused {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}

.config-meta {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.refresh-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
}

.refresh-status-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.refresh-status-icon svg {
  width: 16px;
  height: 16px;
}

.refresh-status-icon.success {
  color: #10b981;
}

.refresh-status-icon.error {
  color: #ef4444;
}

.refresh-status-icon.pending {
  color: #94a3b8;
}

.refresh-status-icon.executing {
  color: #4c74df;
}

.refresh-status-icon.executing svg {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.refresh-switch {
  display: grid;
  min-width: 0;
}

.refresh-text,
.refresh-summary {
  grid-area: 1 / 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity 0.18s ease;
  font-size: 13px;
}

.refresh-text {
  color: #475569;
}

.refresh-summary {
  color: #64748b;
  opacity: 0;
}

.refresh-switch:hover .refresh-summary {
  opacity: 1;
}

.refresh-switch:hover .refresh-text {
  opacity: 0;
}

/* 账号徽章 */
.account-badge {
  display: inline-block;
  padding: 4px 8px;
  background: #3b82f6;
  color: white;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

/* 间隔徽章 */
.interval-badge {
  display: inline-block;
  color: #374151;
  font-size: 12px;
  font-weight: 500;
}

/* 递归模式徽章 */
.recursion-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.recursion-badge.infinite {
  background: #f59e0b;
  color: white;
}

.recursion-badge.single {
  background: #6b7280;
  color: white;
}

/* 创建时间 */
.created-time {
  color: #6b7280;
  font-size: 12px;
  margin-top: 2px;
}

/* 对话框基础样式 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100000;
  backdrop-filter: blur(4px);
}

.dialog {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  max-width: 700px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  animation: dialogSlideIn 0.3s ease-out;
}

@keyframes dialogSlideIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 30px;
  border-bottom: 1px solid #e9ecef;
  background: #F9FAFB;
  border-top-left-radius: 16px;
  border-top-right-radius: 16px;
}

.dialog-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  color: #6c757d;
  cursor: pointer;
  padding: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f8f9fa;
  color: #495057;
}

.dialog-content {
  padding: 20px 20px 0px 20px;
  overflow: visible;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.dialog-footer {
  padding: 20px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.add-config-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #374151;
  font-size: 14px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 0;
}

.form-group {
  margin-bottom: 0;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.4;
  transition: border-color 0.2s ease;
  box-sizing: border-box;
  height: 40px;
}

.form-input:focus {
  outline: none;
  border-color: #4C74DF;
  box-shadow: 0 0 0 2px rgba(76, 116, 223, 0.1);
}

.form-input.readonly {
  background-color: #f8fafc;
  color: #64748b;
  cursor: pointer;
}

.path-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.path-selector .form-input {
  flex: 1;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #374151;
  margin-bottom: 8px;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: #4C74DF;
}

.checkmark {
  width: 16px;
  height: 16px;
  border: 2px solid #dcdfe6;
  border-radius: 4px;
  position: relative;
}

.checkbox-label input[type="checkbox"]:checked + .checkmark {
  background-color: #409eff;
  border-color: #409eff;
}

.checkmark:after {
  content: "";
  position: absolute;
  display: none;
}

.checkbox-label input[type="checkbox"]:checked + .checkmark:after {
  display: block;
}

.checkmark:after {
  left: 4px;
  top: 0px;
  width: 5px;
  height: 10px;
  border: solid white;
  border-width: 0 3px 3px 0;
  transform: rotate(45deg);
}

.form-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  font-size: 14px;
  color: #333;
  background-color: #fff;
  cursor: pointer;
  transition: border-color 0.3s;
}

.form-select:focus {
  border-color: #409eff;
  outline: none;
}

.form-select option {
  background-color: #fff;
  color: #333;
}

.form-select option:checked {
  background-color: #409eff;
  color: #fff;
}

.form-select option:hover {
  background-color: #f0f7eb;
}

.form-group small {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
  line-height: 1.4;
}

.btn-secondary {
  background: #e0e0e0;
  color: #333;
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 14px;
}

.btn-secondary:hover {
  background-color: #d0d0d0;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #409eff;
  color: #fff;
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.btn-primary:hover {
  background: #337ecc;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 响应式 */
@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .list-header {
    flex-direction: column;
    gap: 12px;
  }

  .list-actions {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .list-filters {
    width: 100%;
  }

  .action-buttons {
    width: 100%;
    justify-content: space-between;
  }

  .action-buttons .btn {
    flex: 1;
  }

  .action-buttons {
    flex-direction: column;
  }

  .form-row {
    flex-direction: column;
    gap: 10px;
  }

  .form-group {
    width: 100%;
  }

  .path-selector {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .btn-browse {
    width: 100%;
  }

  .checkbox-label {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }

  .checkbox-label input[type="checkbox"] {
    width: 20px;
    height: 20px;
  }

  .checkmark {
    width: 20px;
    height: 20px;
  }

  .dialog {
    width: 95%;
    max-height: 95vh;
  }

  .dialog-header h3 {
    font-size: 18px;
  }

  .dialog-footer {
    flex-direction: column;
    gap: 10px;
  }
}

/* 浏览按钮样式 */
.btn-browse {
  background: linear-gradient(135deg, #4C74DF, #02A6F0);
  color: #fff;
  padding: 10px 16px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
  box-shadow: 0 2px 4px rgba(76, 116, 223, 0.3);
}

.btn-browse:hover {
  background: linear-gradient(135deg, #3b5bdb, #1e88e5);
  color: #fff;
  box-shadow: 0 4px 12px rgba(76, 116, 223, 0.4);
}

.btn-browse:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

/* 输入组样式 */
.input-group {
  display: flex;
  align-items: stretch;
  gap: 0;
}

.input-group .form-input {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
  flex: 1;
}

.input-group .btn-browse {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  border-left: none;
  white-space: nowrap;
}

.startup-countdown-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px 20px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #eff6ff 0%, #f0f4ff 100%);
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  color: #1e40af;
  font-size: 14px;
}

.startup-countdown-banner i {
  font-size: 16px;
  color: #3b82f6;
}

.startup-countdown-banner strong {
  font-weight: 700;
  color: #1d4ed8;
}

.time-window-display {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.time-window-display:hover {
  border-color: #4C74DF;
}

.time-window-icon {
  width: 16px;
  height: 16px;
  color: #94a3b8;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: color 0.2s;
}

.time-window-display:hover .time-window-icon {
  color: #4C74DF;
}

</style>
