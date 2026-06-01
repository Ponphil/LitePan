<template>
  <div class="folder-selector-shell">
    <div class="folder-selector-modal-header">
      <h3 class="folder-selector-modal-title">{{ title }}</h3>
      <label class="folder-selector-search" title="仅筛选当前目录下已加载的文件夹">
        <i class="fas fa-search"></i>
        <input
          v-model.trim="filterKeyword"
          type="search"
          placeholder="筛选当前目录文件夹"
          :disabled="loading"
          maxlength="100"
        >
        <button
          v-if="filterKeyword"
          type="button"
          class="folder-selector-search-clear"
          aria-label="清空筛选"
          @click="clearDirectoryFilter"
        >
          <i class="fas fa-times"></i>
        </button>
      </label>
      <button type="button" class="folder-selector-modal-close" @click="$emit('cancel')" aria-label="关闭">×</button>
    </div>

    <div class="folder-selector-content">
      <nav v-if="!locatingInitialPath" class="breadcrumb" style="margin-bottom:2px;">
        <span
          class="breadcrumb-item"
          :class="{ active: pathHistory.length === 1 }"
          data-idx="0"
          @click="navigateToIndex(0)"
        ><span class="breadcrumb-item-label">根目录</span></span>

        <template v-if="hiddenBreadcrumbItems.length">
          <div
            class="breadcrumb-ellipsis-dropdown"
            @mouseenter="openDropdown"
            @mouseleave="scheduleCloseDropdown"
          >
            <span class="breadcrumb-ellipsis" @click.stop="toggleDropdown">...</span>
            <div v-if="dropdownOpen" class="breadcrumb-dropdown">
              <div
                v-for="item in hiddenBreadcrumbItems"
                :key="item.index"
                class="breadcrumb-dropdown-item"
                :title="item.name"
                @click.stop="selectHiddenBreadcrumb(item.index)"
              >
                {{ item.name }}
              </div>
            </div>
          </div>
        </template>

        <template v-for="item in trailingBreadcrumbItems" :key="item.index">
          <span
            class="breadcrumb-item"
            :class="{ active: item.index === pathHistory.length - 1 }"
            :data-idx="item.index"
            :title="item.name"
            @click="navigateToIndex(item.index)"
          ><span class="breadcrumb-item-label">{{ item.name }}</span></span>
        </template>
      </nav>
      <div v-if="!locatingInitialPath && filterKeyword" class="folder-filter-tip">
        仅筛选当前目录，匹配 {{ sortedDirectories.length }} 项
      </div>

      <div v-if="!locatingInitialPath" class="folder-table-header" role="row">
        <button
          v-for="column in sortColumns"
          :key="column.key"
          type="button"
          class="folder-table-heading"
          :class="[`col-${column.key}`, { active: sortKey === column.key }]"
          @click="toggleSort(column.key)"
        >
          <span>{{ column.label }}</span>
          <span class="sort-indicator" :class="getSortClass(column.key)"></span>
        </button>
      </div>

      <div id="move-folder-list" class="file-list folder-table-body" style="margin-bottom:0;">
        <div v-if="showCreateInput" class="file-row move-folder-input folder-row folder-table-row">
          <i class="icon"><SvgIcon name="folder" :size="18" /></i>
          <input
            ref="newFolderInputRef"
            v-model.trim="newFolderName"
            type="text"
            class="file-name move-folder-inputbox"
            placeholder="输入文件夹名称"
            maxlength="100"
            :disabled="creatingFolder"
            @keyup.enter="createFolder"
            @keyup.esc="cancelCreateFolder"
          >
          <button type="button" class="folder-inline-btn confirm" :disabled="creatingFolder" @click="createFolder">
            <i class="fas fa-check"></i>
          </button>
          <button type="button" class="folder-inline-btn cancel" :disabled="creatingFolder" @click="cancelCreateFolder">
            <i class="fas fa-times"></i>
          </button>
        </div>

        <div v-if="loading" class="folder-state">{{ locatingInitialPath ? '正在定位已选目录...' : '加载中...' }}</div>
        <div v-else-if="errorMessage" class="folder-state error">{{ errorMessage }}</div>
        <div v-else-if="!sortedDirectories.length" class="folder-state">
          {{ filterKeyword ? '当前目录没有匹配的文件夹' : '没有子目录' }}
        </div>
        <template v-else>
          <div
            v-for="dir in sortedDirectories"
            :key="dir.id"
            class="file-row move-folder-item folder-row folder-table-row"
            @click="openDirectory(dir)"
          >
            <div class="folder-name-cell">
              <i class="icon"><SvgIcon name="folder" :size="18" /></i>
              <span
                :ref="el => setFolderNameRef(dir.id, el)"
                class="file-name"
                :class="{ truncated: isFolderNameTruncated(dir.id) }"
              >{{ dir.name }}</span>
              <span v-if="isFolderNameTruncated(dir.id)" class="folder-name-tooltip">{{ dir.name }}</span>
            </div>
            <span class="folder-time-cell">{{ formatFolderModified(dir.modified_time) }}</span>
          </div>
        </template>
      </div>
    </div>

    <div class="folder-selector-modal-footer">
      <button
        v-if="allowCreateFolder"
        type="button"
        class="folder-selector-secondary-btn"
        :disabled="loading || creatingFolder"
        @click="showCreateFolderInput"
      >
        <i class="fas fa-folder-plus"></i>
        新建文件夹
      </button>
      <button
        v-if="showRefreshButton"
        type="button"
        class="folder-selector-secondary-btn"
        :disabled="loading || creatingFolder"
        @click="refreshCurrentDirectory"
      >
        <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i>
        刷新
      </button>
      <div class="folder-selector-footer-spacer" aria-hidden="true"></div>
      <button type="button" class="folder-selector-confirm-btn" :disabled="loading || creatingFolder" @click="selectCurrent">
        <i class="fas fa-check"></i>
        {{ confirmText }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import SvgIcon from '../icons/SvgIcon.vue'

const props = defineProps({
  accountId: {
    type: [Number, String],
    required: true
  },
  title: {
    type: String,
    default: '选择目录'
  },
  confirmText: {
    type: String,
    default: '选择当前目录'
  },
  rootId: {
    type: [Number, String],
    default: '0'
  },
  initialPath: {
    type: String,
    default: ''
  },
  excludedFolderIds: {
    type: Array,
    default: () => []
  },
  allowCreateFolder: {
    type: Boolean,
    default: false
  },
  showRefreshButton: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['resolve', 'cancel'])

const loading = ref(false)
const creatingFolder = ref(false)
const locatingInitialPath = ref(false)
const errorMessage = ref('')
const directories = ref([])
const currentPath = ref('root')
const currentDisplayPath = ref('/')
const pathHistory = ref([{ id: 'root', name: '根目录' }])
const dropdownOpen = ref(false)
const showCreateInput = ref(false)
const newFolderName = ref('')
const newFolderInputRef = ref(null)
const truncatedFolderIds = ref(new Set())
const filterKeyword = ref('')
const sortKey = ref('name')
const sortOrder = ref('asc')
let dropdownCloseTimer = null
const folderNameRefs = new Map()

const normalizedRootId = computed(() => String(props.rootId ?? '0'))
const excludedFolderIdSet = computed(() => new Set((props.excludedFolderIds || []).map(id => String(id))))
const effectiveCurrentId = computed(() => currentPath.value === 'root' ? normalizedRootId.value : currentPath.value)
const sortColumns = [
  { key: 'name', label: '名称' },
  { key: 'modified_time', label: '修改时间' }
]

const hiddenBreadcrumbItems = computed(() => {
  if (pathHistory.value.length <= 3) return []
  return pathHistory.value.slice(1, -2).map((item, offset) => ({
    ...item,
    index: offset + 1
  }))
})

const trailingBreadcrumbItems = computed(() => {
  const startIndex = hiddenBreadcrumbItems.value.length ? pathHistory.value.length - 2 : 1
  return pathHistory.value.slice(startIndex).map((item, offset) => ({
    ...item,
    index: startIndex + offset
  }))
})

const visibleDirectories = computed(() => (
  directories.value.filter(dir => !excludedFolderIdSet.value.has(String(dir.id)))
))

const filteredDirectories = computed(() => {
  const keyword = filterKeyword.value.trim().toLowerCase()
  if (!keyword) return visibleDirectories.value
  return visibleDirectories.value.filter(dir => String(dir.name || '').toLowerCase().includes(keyword))
})

const sortedDirectories = computed(() => {
  const order = sortOrder.value === 'desc' ? -1 : 1
  return [...filteredDirectories.value].sort((a, b) => compareDirectories(a, b, sortKey.value, order))
})

const compareDirectories = (a, b, key, order) => {
  if (key === 'modified_time') {
    return compareNullableNumber(toTimestamp(a?.modified_time), toTimestamp(b?.modified_time), order)
  }
  return String(a?.name || '').localeCompare(String(b?.name || ''), 'zh-CN', {
    numeric: true,
    sensitivity: 'base'
  }) * order
}

const compareNullableNumber = (a, b, order) => {
  const aValid = Number.isFinite(a)
  const bValid = Number.isFinite(b)
  if (!aValid && !bValid) return 0
  if (!aValid) return 1
  if (!bValid) return -1
  return (a - b) * order
}

const toTimestamp = (value) => {
  if (!value) return NaN
  const ts = new Date(value).getTime()
  return Number.isFinite(ts) ? ts : NaN
}

const toggleSort = (key) => {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    return
  }
  sortKey.value = key
  sortOrder.value = key === 'name' ? 'asc' : 'desc'
}

const getSortClass = (key) => {
  if (sortKey.value !== key) return ''
  return sortOrder.value
}

const formatFolderModified = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const updateDisplayPath = () => {
  const names = pathHistory.value.slice(1).map(item => String(item.name || '').trim()).filter(Boolean)
  const path = '/' + names.join('/')
  currentDisplayPath.value = path === '/' ? path : path.replace(/\/+$/, '')
}

const resetCreateFolderState = () => {
  showCreateInput.value = false
  newFolderName.value = ''
}

const clearDirectoryFilter = () => {
  filterKeyword.value = ''
}

const setFolderNameRef = (id, el) => {
  const key = String(id)
  if (el) {
    folderNameRefs.set(key, el)
  } else {
    folderNameRefs.delete(key)
  }
}

const isFolderNameTruncated = (id) => truncatedFolderIds.value.has(String(id))

const updateTruncatedFolderNames = async () => {
  await nextTick()
  const next = new Set()
  folderNameRefs.forEach((el, id) => {
    if (el && el.scrollWidth > el.clientWidth + 1) {
      next.add(id)
    }
  })
  truncatedFolderIds.value = next
}

const resetToRootState = () => {
  currentPath.value = 'root'
  currentDisplayPath.value = '/'
  pathHistory.value = [{ id: 'root', name: '根目录' }]
  resetCreateFolderState()
  clearDirectoryFilter()
}

const getInitialPathSegments = () => {
  return String(props.initialPath || '')
    .split('/')
    .map(item => item.trim())
    .filter(Boolean)
}

const fetchDirectoryList = async (parentId = 'root', options = {}) => {
  const requestParentId = parentId === 'root' ? normalizedRootId.value : String(parentId)
  const params = new URLSearchParams({ parent_id: requestParentId })
  if (options.forceRefresh) {
    params.set('force_refresh', 'true')
  }
  const response = await axios.get(`/api/cache-retention/accounts/${props.accountId}/directories?${params.toString()}`)
  if (!response.data.success) {
    throw new Error(response.data.message || '加载失败')
  }
  return response.data.data || []
}

const loadDirectories = async (parentId = 'root', options = {}) => {
  loading.value = true
  errorMessage.value = ''
  dropdownOpen.value = false
  try {
    directories.value = await fetchDirectoryList(parentId, options)
  } catch (error) {
    directories.value = []
    errorMessage.value = error?.response?.data?.message || error?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const initializeDirectory = async () => {
  resetToRootState()
  const segments = getInitialPathSegments()
  if (!segments.length) {
    await loadDirectories()
    return
  }

  loading.value = true
  locatingInitialPath.value = true
  errorMessage.value = ''
  dropdownOpen.value = false

  try {
    let parentId = 'root'
    const history = [{ id: 'root', name: '根目录' }]

    for (const segment of segments) {
      const list = await fetchDirectoryList(parentId)
      const matched = list.find(dir => String(dir.name || '').trim() === segment)
      if (!matched) {
        throw new Error(`目录不存在: ${segment}`)
      }
      parentId = String(matched.id)
      history.push({ id: parentId, name: String(matched.name || segment) })
    }

    currentPath.value = parentId
    pathHistory.value = history
    updateDisplayPath()
    directories.value = await fetchDirectoryList(parentId)
  } catch (error) {
    resetToRootState()
    try {
      directories.value = await fetchDirectoryList('root')
    } catch (rootError) {
      directories.value = []
      errorMessage.value = rootError?.response?.data?.message || rootError?.message || '加载失败'
    }
    window.appNotification?.warning('已保存目录不存在或无法定位，已打开根目录')
  } finally {
    locatingInitialPath.value = false
    loading.value = false
  }
}

const refreshCurrentDirectory = async () => {
  resetCreateFolderState()
  await loadDirectories(currentPath.value, { forceRefresh: true })
}

const openDirectory = async (dir) => {
  currentPath.value = String(dir.id)
  pathHistory.value = [...pathHistory.value, { id: currentPath.value, name: String(dir.name) }]
  updateDisplayPath()
  resetCreateFolderState()
  clearDirectoryFilter()
  await loadDirectories(currentPath.value)
}

const navigateToIndex = async (index) => {
  if (index < 0 || index >= pathHistory.value.length) return
  pathHistory.value = pathHistory.value.slice(0, index + 1)
  currentPath.value = pathHistory.value[index].id
  updateDisplayPath()
  resetCreateFolderState()
  clearDirectoryFilter()
  await loadDirectories(currentPath.value)
}

const clearDropdownTimer = () => {
  if (dropdownCloseTimer) {
    clearTimeout(dropdownCloseTimer)
    dropdownCloseTimer = null
  }
}

const openDropdown = () => {
  clearDropdownTimer()
  dropdownOpen.value = true
}

const scheduleCloseDropdown = () => {
  clearDropdownTimer()
  dropdownCloseTimer = setTimeout(() => {
    dropdownOpen.value = false
  }, 120)
}

const toggleDropdown = () => {
  clearDropdownTimer()
  dropdownOpen.value = !dropdownOpen.value
}

const selectHiddenBreadcrumb = async (index) => {
  dropdownOpen.value = false
  await navigateToIndex(index)
}

const showCreateFolderInput = () => {
  if (!props.allowCreateFolder || creatingFolder.value) {
    return
  }
  clearDirectoryFilter()
  showCreateInput.value = true
}

const cancelCreateFolder = () => {
  if (creatingFolder.value) return
  resetCreateFolderState()
}

const createFolder = async () => {
  const folderName = String(newFolderName.value || '').trim()
  if (!folderName) {
    window.appNotification?.warning('请输入文件夹名称')
    return
  }
  if (folderName.length > 100) {
    window.appNotification?.warning('文件夹名称不能超过100个字符')
    return
  }
  if (visibleDirectories.value.some(dir => String(dir.name || '').toLowerCase() === folderName.toLowerCase())) {
    window.appNotification?.warning('当前目录已存在同名文件夹')
    return
  }

  creatingFolder.value = true
  try {
    const formData = new FormData()
    formData.append('account_id', props.accountId)
    formData.append('path', effectiveCurrentId.value)
    formData.append('name', folderName)

    const response = await axios.post('/api/files/create-folder', formData)
    if (!response.data?.success) {
      throw new Error(response.data?.message || '创建文件夹失败')
    }

    window.appNotification?.success(response.data?.message || '文件夹创建成功')
    const createdFolderId = String(response.data?.data?.folder_id || '')
    resetCreateFolderState()
    await loadDirectories(currentPath.value)

    const createdFolder = visibleDirectories.value.find(dir =>
      (createdFolderId && String(dir.id) === createdFolderId) ||
      String(dir.name || '').toLowerCase() === folderName.toLowerCase()
    )

    if (createdFolder) {
      await openDirectory(createdFolder)
    }
  } catch (error) {
    window.appNotification?.error(error.response?.data?.message || error.message || '创建文件夹失败')
  } finally {
    creatingFolder.value = false
  }
}

const selectCurrent = () => {
  emit('resolve', {
    id: currentPath.value === 'root' ? normalizedRootId.value : currentPath.value,
    path: currentDisplayPath.value || '/'
  })
}

watch(
  () => [props.accountId, props.rootId, props.initialPath],
  async () => {
    await initializeDirectory()
  },
  { immediate: true }
)

watch(showCreateInput, async (visible) => {
  if (visible) {
    await nextTick()
    newFolderInputRef.value?.focus()
    newFolderInputRef.value?.select?.()
  }
})

watch(
  sortedDirectories,
  () => {
    updateTruncatedFolderNames()
  },
  { flush: 'post' }
)

onMounted(() => {
  window.addEventListener('resize', updateTruncatedFolderNames)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateTruncatedFolderNames)
})
</script>

<style scoped>
.folder-selector-shell {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  max-height: 100%;
  box-sizing: border-box;
  overflow: visible;
}

.folder-selector-modal-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 24px 0;
}

.folder-selector-modal-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  flex-shrink: 0;
}

.folder-selector-search {
  width: 220px;
  height: 36px;
  margin-left: auto;
  padding: 0 10px;
  border-radius: 18px;
  background: #f5f7fa;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 8px;
  box-sizing: border-box;
}

.folder-selector-search i {
  flex-shrink: 0;
  font-size: 13px;
}

.folder-selector-search input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: #334155;
  font-size: 13px;
}

.folder-selector-search input::placeholder {
  color: #9aa4b2;
}

.folder-selector-search input:disabled {
  cursor: not-allowed;
}

.folder-selector-search-clear {
  width: 18px;
  height: 18px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.folder-selector-search-clear:hover {
  color: #475569;
}

.folder-selector-modal-close {
  background: none;
  border: none;
  color: #999;
  font-size: 20px;
  line-height: 1;
  width: 24px;
  height: 24px;
  padding: 0;
  cursor: pointer;
}

.folder-selector-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 20px 24px 12px;
  box-sizing: border-box;
  overflow: visible; /* 必须为 visible，否则下拉菜单会被截断 */
  position: relative;
  z-index: 1;
}

.breadcrumb {
  display: flex;
  align-items: center;
  min-height: 20px;
  height: 20px;
  margin-top: -6px !important;
  margin-bottom: 2px !important;
}

.folder-filter-tip {
  margin-top: 8px;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1;
}

.file-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  margin-top: 2px !important;
  height: auto !important;
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
}

/* 修复面包屑下拉菜单被模态框遮挡的问题 */
.breadcrumb-ellipsis-dropdown {
  position: relative;
  display: inline-flex;
}

.breadcrumb-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 99999;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  padding: 4px 0;
  min-width: 150px;
  max-width: 250px;
  max-height: 300px;
  overflow-y: auto;
}

.breadcrumb-dropdown-item {
  padding: 8px 16px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background-color 0.2s;
}

.breadcrumb-dropdown-item:hover {
  background-color: #f3f4f6;
}

/* 确保滚动条在各浏览器下表现良好 */
.breadcrumb-dropdown::-webkit-scrollbar {
  width: 6px;
}

.breadcrumb-dropdown::-webkit-scrollbar-track {
  background: transparent;
}

.breadcrumb-dropdown::-webkit-scrollbar-thumb {
  background-color: #D9D9D9;
  border-radius: 3px;
}

.folder-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 10px;
  font-size: 14px;
  line-height: 1.8;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  min-width: 0;
}

.folder-table-header,
.folder-table-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 200px;
  align-items: center;
  column-gap: 16px;
}

.folder-table-header {
  flex-shrink: 0;
  min-height: 46px;
  margin: 12px 0 6px;
  padding: 0 12px;
  background: #f8fafc;
  border-radius: 10px;
}

.folder-table-heading {
  min-width: 0;
  height: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: #8a94a6;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  text-align: left;
}

.folder-table-heading.col-modified_time {
  justify-content: flex-end;
}

.folder-table-heading.active {
  color: #475569;
}

.sort-indicator {
  flex-shrink: 0;
}

.folder-table-body {
  padding-right: 2px;
  overflow-x: hidden;
}

.folder-table-row {
  padding: 12px;
  overflow: visible;
}

.move-folder-input.folder-table-row {
  grid-template-columns: 18px minmax(0, 1fr) 28px 28px;
  column-gap: 8px;
}

.folder-name-cell {
  position: relative;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.folder-name-cell .icon {
  flex-shrink: 0;
}

.folder-name-cell .file-name {
  flex: 1;
  min-width: 0;
  max-width: none !important;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-name-tooltip {
  position: absolute;
  left: 28px;
  bottom: calc(100% + 10px);
  z-index: 20;
  max-width: min(520px, calc(100vw - 80px));
  padding: 7px 10px;
  border-radius: 8px;
  border: 1px solid #e6eaf2;
  background: #fff;
  color: #334155;
  font-size: 13px;
  line-height: 1.45;
  white-space: normal;
  word-break: break-all;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translateY(4px);
  transition:
    opacity 0.12s ease,
    visibility 0s linear 0.12s,
    transform 0.12s ease;
}

.folder-name-tooltip::before {
  content: '';
  position: absolute;
  left: 14px;
  top: 100%;
  border: 5px solid transparent;
  border-top-color: #fff;
  filter: drop-shadow(0 1px 0 #e6eaf2);
}

.folder-name-cell .file-name.truncated:hover + .folder-name-tooltip {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
  transition-delay: 0.8s, 0.8s, 0.8s;
}

.folder-time-cell {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #98a2b3;
  font-size: 13px;
  text-align: right;
}

.move-folder-input {
  background: transparent;
}

.move-folder-inputbox {
  flex: 1;
  min-width: 0;
  border: 1px solid #2196F3;
  background: #fff;
  font-size: 14px;
  padding: 0 12px;
  color: #333;
  transition: border 0.2s;
  border-radius: 8px;
  height: 32px;
  box-sizing: border-box;
}

.folder-inline-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.folder-inline-btn.confirm {
  background: #2196F3;
}

.folder-inline-btn.cancel {
  background: #D1D5DB;
}

.folder-state {
  padding: 20px;
  text-align: center;
  color: #666;
}

.folder-state.error {
  color: #dc2626;
}

.folder-selector-modal-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: auto;
  flex-shrink: 0;
  padding: 0 24px 24px;
}

.folder-selector-footer-spacer {
  flex: 1;
}

.folder-selector-secondary-btn,
.folder-selector-confirm-btn {
  height: 38px;
  border-radius: 10px;
  padding: 0 16px;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
}

.folder-selector-secondary-btn {
  background: #fff;
  color: #475569;
  border: 1px solid #dbe3ee;
}

.folder-selector-confirm-btn {
  min-width: 140px;
  background: linear-gradient(135deg, #4c74df 0%, #02a6f0 100%);
  color: #fff;
}

.folder-selector-secondary-btn:disabled,
.folder-selector-confirm-btn:disabled,
.folder-inline-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .folder-selector-modal-header {
    padding: 18px 18px 0;
    flex-wrap: wrap;
    gap: 10px;
  }

  .folder-selector-search {
    order: 3;
    width: 100%;
    margin-left: 0;
  }

  .folder-selector-content {
    padding: 18px 18px 10px;
  }

  .folder-table-header,
  .folder-table-row {
    grid-template-columns: minmax(0, 1fr) 140px;
    column-gap: 10px;
  }

  .folder-table-header {
    padding: 0 10px;
  }

  .folder-table-heading,
  .folder-time-cell {
    font-size: 12px;
  }

  .folder-table-row {
    padding: 10px;
  }

  .folder-selector-modal-footer {
    padding: 0 18px 20px;
  }
}
</style>
