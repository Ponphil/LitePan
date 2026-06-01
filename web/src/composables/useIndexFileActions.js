import axios from 'axios'
import FolderSelectorModal from '../components/common/FolderSelectorModal.vue'
import FileActionDialog from '../components/index/FileActionDialog.vue'

const escapeHtml = text => String(text ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const createFieldError = (field, message) => {
  const error = new Error(message)
  error.field = field
  return error
}

const invalidFileNamePattern = /[<>:"/\\|?*\x00-\x1F]/

const validateFileNameBasics = (name, field = 'name') => {
  const trimmedName = name.trim()
  if (!trimmedName) {
    throw createFieldError(field, '请输入名称')
  }
  if (trimmedName.length > 100) {
    throw createFieldError(field, '名称不能超过100个字符')
  }
  if (trimmedName === '.' || trimmedName === '..') {
    throw createFieldError(field, '名称不能为 . 或 ..')
  }
  if (invalidFileNamePattern.test(trimmedName)) {
    throw createFieldError(field, '名称不能包含 < > : " / \\ | ? * 等特殊字符')
  }
  if (/[.\s]$/.test(trimmedName)) {
    throw createFieldError(field, '名称不能以空格或点结尾')
  }

  return trimmedName
}

const buildSmartBreadcrumb = (pathItems, maxItems = 4) => {
  if (pathItems.length <= maxItems) {
    return pathItems.map((item, index) =>
      `<span class="breadcrumb-item${index === pathItems.length - 1 ? ' active' : ''}" data-idx="${index}" title="${escapeHtml(item.name)}"><span class="breadcrumb-item-label">${escapeHtml(item.name)}</span></span>`
    ).join('')
  }

  const result = []
  result.push(`<span class="breadcrumb-item" data-idx="0" title="${escapeHtml(pathItems[0].name)}"><span class="breadcrumb-item-label">${escapeHtml(pathItems[0].name)}</span></span>`)

  const hiddenItems = pathItems.slice(1, pathItems.length - 2)
  const dropdownItems = hiddenItems.map(item =>
    `<div class="breadcrumb-dropdown-item" data-idx="${pathItems.indexOf(item)}" title="${escapeHtml(item.name)}"><span class="breadcrumb-dropdown-item-label">${escapeHtml(item.name)}</span></div>`
  ).join('')

  result.push(`
    <span class="breadcrumb-ellipsis-dropdown">
      <span class="breadcrumb-ellipsis">...</span>
      <div class="breadcrumb-dropdown">${dropdownItems}</div>
    </span>
  `)

  for (let i = pathItems.length - 2; i < pathItems.length; i += 1) {
    const active = i === pathItems.length - 1 ? ' active' : ''
    result.push(`<span class="breadcrumb-item${active}" data-idx="${i}" title="${escapeHtml(pathItems[i].name)}"><span class="breadcrumb-item-label">${escapeHtml(pathItems[i].name)}</span></span>`)
  }

  return result.join('')
}

export function useIndexFileActions({
  accounts,
  files,
  selectedAccountId,
  selectedFilesList,
  currentPath,
  operationLoading,
  setOperationLoading,
  loadFiles,
  refreshFiles,
  refreshAfterCreateFolder,
  naturalSort,
  confirm,
  form,
  custom,
  closeModal
}) {
  const getCurrentAccount = () => accounts.value.find(account => account.id === selectedAccountId.value)
  const getRootId = () => getCurrentAccount()?.config?.root_folder_id || '0'

  const getDeleteMode = () => {
    const account = getCurrentAccount()
    if (!account?.config) return 'recycle'
    return account.config.delete_mode === 'delete' ? 'permanent' : 'recycle'
  }

  const validateFolderName = name => {
    const trimmedName = validateFileNameBasics(name, 'folderName')

    const existingFile = files.value.find(file => file.name.toLowerCase() === trimmedName.toLowerCase())
    if (existingFile) {
      if (existingFile.is_dir) {
        window.appNotification.warning('当前目录已存在同名文件夹，请重新输入')
      } else {
        window.appNotification.warning('当前目录已存在同名文件，请重新输入')
      }
      throw new Error('')
    }

    return trimmedName
  }

  const validateRename = (file, name) => {
    const trimmedName = validateFileNameBasics(name, 'newName')
    if (trimmedName === file.name) {
      throw createFieldError('newName', '新名称不能与原名称相同')
    }

    const existingFile = files.value.find(item =>
      item.id !== file.id && item.name.toLowerCase() === trimmedName.toLowerCase()
    )
    if (existingFile) {
      if (existingFile.is_dir) {
        window.appNotification.warning('当前目录已存在同名文件夹，请重新输入')
      } else {
        window.appNotification.warning('当前目录已存在同名文件，请重新输入')
      }
      throw new Error('')
    }

    return trimmedName
  }

  const notifyValidationError = error => {
    if (error?.field && error.message) {
      window.appNotification.warning(error.message)
      return true
    }
    return false
  }

  const createFolder = async (inlineName = null, options = {}) => {
    const isInlineCreate = typeof inlineName === 'string'
    const showGlobalLoading = options.showGlobalLoading !== false
    const showSuccess = options.showSuccess !== false
    const refresh = options.refresh || refreshAfterCreateFolder

    if (!selectedAccountId.value) {
      window.appNotification.warning('请先选择一个账号')
      return false
    }
    if (operationLoading.value && showGlobalLoading) return false

    try {
      let folderName
      if (isInlineCreate) {
        folderName = inlineName
      } else {
        const result = await form({
          title: '新建文件夹',
          confirmText: '创建',
          className: 'minimal',
          hideCancelButton: true,
          fields: [
            {
              name: 'folderName',
              label: '文件夹名称',
              type: 'text',
              required: true,
              placeholder: '请输入文件夹名称',
              autofocus: true
            }
          ],
          validate: values => {
            validateFolderName(values.folderName)
          }
        })
        folderName = result.folderName
      }

      folderName = validateFolderName(folderName)
      if (showGlobalLoading) {
        setOperationLoading(true, 'create_folder', null, folderName)
      }

      try {
        const formData = new FormData()
        formData.append('account_id', selectedAccountId.value)
        formData.append('path', currentPath.value)
        formData.append('name', folderName)

        const response = await axios.post('/api/files/create-folder', formData)
        if (response.data.success) {
          if (showSuccess) {
            window.appNotification.success(response.data.message)
          }
          await refresh(folderName)
          return true
        } else {
          window.appNotification.error(response.data.message)
          return false
        }
      } catch (apiError) {
        window.appNotification.error(`创建文件夹失败: ${apiError.response?.data?.message || apiError.message}`)
        return false
      } finally {
        if (showGlobalLoading) {
          setOperationLoading(false)
        }
      }
    } catch (error) {
      if (isInlineCreate && notifyValidationError(error)) {
        return false
      }
      if (error.message !== 'Modal closed' && error.message) {
        console.error('创建文件夹错误:', error)
      }
      return false
    }
  }

  const renameFile = async (file, inlineName = null, options = {}) => {
    const isInlineRename = typeof inlineName === 'string'
    const showGlobalLoading = options.showGlobalLoading !== false
    const showSuccess = options.showSuccess !== false
    const refresh = options.refresh || loadFiles

    if (operationLoading.value && showGlobalLoading) return false

    try {
      let newName
      if (isInlineRename) {
        newName = inlineName
      } else {
        const result = await form({
          title: '重命名',
          confirmText: '重命名',
          className: 'minimal',
          hideCancelButton: true,
          fields: [
            {
              name: 'newName',
              label: '新名称',
              type: 'text',
              required: true,
              placeholder: '请输入新名称',
              defaultValue: file.name,
              autofocus: true,
              selectText: true
            }
          ],
          validate: values => {
            validateRename(file, values.newName)
          }
        })
        newName = result.newName
      }

      newName = validateRename(file, newName)

      if (showGlobalLoading) {
        setOperationLoading(true, file.is_dir ? 'rename_folder' : 'rename_file', null, file.name)
      }

      try {
        const response = await axios.put('/api/files/rename', {
          account_id: selectedAccountId.value,
          old_path: file.id,
          new_name: newName
        }, {
          headers: {
            'Content-Type': 'application/json'
          }
        })

        if (response.data.success) {
          if (showSuccess) {
            window.appNotification.success(response.data.message)
          }
          await refresh()
          return true
        } else {
          window.appNotification.error(response.data.message)
          return false
        }
      } catch (apiError) {
        window.appNotification.error(`重命名失败: ${apiError.response?.data?.message || apiError.message}`)
        return false
      } finally {
        if (showGlobalLoading) {
          setOperationLoading(false)
        }
      }
    } catch (error) {
      if (isInlineRename && notifyValidationError(error)) {
        return false
      }
      if (error.message !== 'Modal closed' && error.message) {
        console.error('重命名错误:', error)
      }
      return false
    }
  }

  window.downloadFileAction = null

  const handleFileDownload = async file => {
    if (operationLoading.value) return

    try {
      setOperationLoading(true, 'download_file', null, file.name)
      const encodedFileId = encodeURIComponent(file.id)
      const downloadUrl = `/api/files/download/${selectedAccountId.value}/${encodedFileId}?user_agent=${encodeURIComponent(navigator.userAgent)}&file_name=${encodeURIComponent(file.name || '')}`
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = file.name
      link.style.display = 'none'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.appNotification.success(`开始下载文件：${file.name}`)
    } catch (error) {
      window.appNotification.error(`下载文件失败: ${error.message}`)
    } finally {
      setOperationLoading(false)
    }
  }

  const showFileActionModal = async file => {
    const result = await custom({
      title: '',
      size: 'medium',
      hideFooter: true,
      component: FileActionDialog,
      componentProps: {
        fileName: file.name,
        file: { name: file.name, is_dir: !!file.is_dir }
      }
    }).catch(() => null)

    if (result?.action === 'download') {
      await handleFileDownload(file)
    }
  }

  const deleteFile = async (file, options = {}) => {
    const showGlobalLoading = options.showGlobalLoading !== false
    const refresh = options.refresh || loadFiles
    const onRequestStart = options.onRequestStart || null
    const onRequestEnd = options.onRequestEnd || null

    if (operationLoading.value && showGlobalLoading) return false

    try {
      const deleteMode = getDeleteMode()
      const modalConfig = deleteMode === 'permanent'
        ? {
            title: '确认彻底删除',
            content: `确定要彻底删除${file.is_dir ? '文件夹' : '文件'} "${file.name}" 吗？删除后无法恢复！`,
            confirmText: '彻底删除',
            confirmClass: 'btn-danger',
            icon: 'trash'
          }
        : {
            title: '确认删除',
            content: `确定要将${file.is_dir ? '文件夹' : '文件'} "${file.name}" 移入回收站吗？`,
            confirmText: '删除',
            confirmClass: 'btn-primary',
            icon: 'warning'
          }

      await confirm(modalConfig)

      try {
        if (showGlobalLoading) {
          setOperationLoading(true, file.is_dir ? 'delete_folder' : 'delete_file', null, file.name)
        }
        onRequestStart?.()
        const response = await axios.delete('/api/files/delete', {
          data: {
            account_id: selectedAccountId.value,
            file_ids: [file.id],
            parent_id: currentPath.value
          },
          headers: {
            'Content-Type': 'application/json'
          }
        })

        if (response.data.success) {
          window.appNotification.success(response.data.message)
          await refresh()
          return true
        } else {
          window.appNotification.error(response.data.message)
          return false
        }
      } catch (apiError) {
        window.appNotification.error(`删除失败: ${apiError.response?.data?.message || apiError.message}`)
        return false
      } finally {
        onRequestEnd?.()
        if (showGlobalLoading) {
          setOperationLoading(false)
        }
      }
    } catch (error) {
      if (error.message !== 'Modal closed') {
        console.error('删除文件错误:', error)
      }
      return false
    }
  }

  const buildSelectedCountText = selectedCount => {
    const hasFiles = files.value.some(file => selectedFilesList.value.includes(file.id) && !file.is_dir)
    const hasFolders = files.value.some(file => selectedFilesList.value.includes(file.id) && file.is_dir)

    if (hasFiles && hasFolders) return `${selectedCount} 个文件和文件夹`
    if (hasFolders) return `${selectedCount} 个文件夹`
    if (hasFiles) return `${selectedCount} 个文件`
    return `${selectedCount} 个项目`
  }

  const showMoveDialog = async (targetFiles = null) => {
    const movingFiles = targetFiles || files.value.filter(file => selectedFilesList.value.includes(file.id))
    const selectedFolderIds = movingFiles
      .filter(file => file.is_dir)
      .map(file => String(file.id))

    const result = await custom({
      title: '',
      size: null,
      closable: false,
      hideFooter: true,
      modalClass: 'modal-folder-selector',
      bodyClass: 'modal-body-flush',
      component: FolderSelectorModal,
      componentProps: {
        accountId: selectedAccountId.value,
        title: '移动到',
        confirmText: '选择当前目录',
        rootId: getRootId(),
        excludedFolderIds: selectedFolderIds,
        allowCreateFolder: true,
        showRefreshButton: false
      }
    }).catch(() => null)

    return result?.id || null
  }

  const moveFiles = async (targetFiles, successRefresh = () => refreshFiles(true), options = {}) => {
    const showGlobalLoading = options.showGlobalLoading !== false
    const onRequestStart = options.onRequestStart || null
    const onRequestEnd = options.onRequestEnd || null

    const movingFiles = targetFiles.filter(Boolean)
    if (movingFiles.length === 0) {
      window.appNotification.warning('请先选择要移动的文件')
      return false
    }

    const targetFolderId = await showMoveDialog(movingFiles)
    if (!targetFolderId) return false

    if (targetFolderId === currentPath.value) {
      window.appNotification.warning('不能移动到原目录')
      return false
    }

    try {
      const selectedCount = movingFiles.length
      const loadingName = selectedCount === 1 ? movingFiles[0].name : `${selectedCount} 个项目`
      if (showGlobalLoading) {
        setOperationLoading(true, 'move', null, loadingName)
      }
      onRequestStart?.()
      const moveData = {
        account_id: parseInt(selectedAccountId.value, 10),
        file_ids: movingFiles.map(file => String(file.id)),
        target_parent_id: String(targetFolderId),
        source_parent_id: String(currentPath.value)
      }

      const response = await axios.post('/api/files/move', moveData, {
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.data.success) {
        window.appNotification.success(response.data.message)
        await successRefresh()
        return true
      } else {
        window.appNotification.error(response.data.message)
        return false
      }
    } catch (apiError) {
      window.appNotification.error(`移动失败: ${apiError.response?.data?.message || apiError.message}`)
      return false
    } finally {
      onRequestEnd?.()
      if (showGlobalLoading) {
        setOperationLoading(false)
      }
    }
  }

  const moveFile = async (file, options = {}) => {
    const showGlobalLoading = options.showGlobalLoading !== false
    if (operationLoading.value && showGlobalLoading) return false

    try {
      const successRefresh = options.refresh || (() => loadFiles())
      return await moveFiles([file], successRefresh, options)
    } catch (error) {
      if (error.message !== 'Modal closed') {
        console.error('移动文件错误:', error)
      }
      return false
    }
  }

  const batchMove = async () => {
    if (operationLoading.value) return

    try {
      const selectedCount = selectedFilesList.value.length
      if (selectedCount === 0) {
        window.appNotification.warning('请先选择要移动的文件')
        return
      }

      const selectedIdSet = new Set(selectedFilesList.value.map(id => String(id)))
      const targetFiles = files.value.filter(file => selectedIdSet.has(String(file.id)))
      await moveFiles(targetFiles, async () => {
        selectedFilesList.value = []
        await refreshFiles(true)
      })
    } catch (error) {
      if (error.message !== 'Modal closed') {
        console.error('批量移动错误:', error)
      }
    }
  }

  const showCopyDialog = async (targetFiles = null) => {
    const copyingFiles = targetFiles || files.value.filter(file => selectedFilesList.value.includes(file.id))
    const selectedFolderIds = copyingFiles
      .filter(file => file.is_dir)
      .map(file => String(file.id))

    const result = await custom({
      title: '',
      size: null,
      closable: false,
      hideFooter: true,
      modalClass: 'modal-folder-selector',
      bodyClass: 'modal-body-flush',
      component: FolderSelectorModal,
      componentProps: {
        accountId: selectedAccountId.value,
        title: '复制到',
        confirmText: '复制到当前目录',
        rootId: getRootId(),
        excludedFolderIds: selectedFolderIds,
        allowCreateFolder: true,
        showRefreshButton: false
      }
    }).catch(() => null)

    return result?.id || null
  }

  const copyFiles = async (targetFiles, successRefresh = () => refreshFiles(true), options = {}) => {
    const showGlobalLoading = options.showGlobalLoading !== false
    const onRequestStart = options.onRequestStart || null
    const onRequestEnd = options.onRequestEnd || null

    const copyingFiles = targetFiles.filter(Boolean)
    if (copyingFiles.length === 0) {
      window.appNotification.warning('请先选择要复制的文件')
      return false
    }

    const targetFolderId = await showCopyDialog(copyingFiles)
    if (!targetFolderId) return false

    try {
      const selectedCount = copyingFiles.length
      const loadingName = selectedCount === 1 ? copyingFiles[0].name : `${selectedCount} 个项目`
      if (showGlobalLoading) {
        setOperationLoading(true, 'copy_file', null, loadingName)
      }
      onRequestStart?.()
      const copyData = {
        account_id: parseInt(selectedAccountId.value, 10),
        file_ids: copyingFiles.map(file => String(file.id)),
        target_parent_id: String(targetFolderId),
        source_parent_id: String(currentPath.value)
      }

      const response = await axios.post('/api/files/copy', copyData, {
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.data.success) {
        window.appNotification.success(response.data.message)
        await successRefresh()
        return true
      } else {
        if (response.data.data?.warning) {
          window.appNotification.warning(response.data.message)
        } else {
          window.appNotification.error(response.data.message)
        }
        return false
      }
    } catch (apiError) {
      window.appNotification.error(`复制失败: ${apiError.response?.data?.message || apiError.message}`)
      return false
    } finally {
      onRequestEnd?.()
      if (showGlobalLoading) {
        setOperationLoading(false)
      }
    }
  }

  const copyFile = async (file, options = {}) => {
    const showGlobalLoading = options.showGlobalLoading !== false
    if (operationLoading.value && showGlobalLoading) return false

    try {
      const successRefresh = options.refresh || (() => loadFiles())
      return await copyFiles([file], successRefresh, options)
    } catch (error) {
      if (error.message !== 'Modal closed') {
        console.error('复制文件错误:', error)
      }
      return false
    }
  }

  const batchCopy = async () => {
    if (operationLoading.value) return

    try {
      const targetFiles = files.value.filter(file => selectedFilesList.value.includes(file.id))
      if (targetFiles.length === 0) {
        window.appNotification.warning('请先选择要复制的文件')
        return
      }
      await copyFiles(targetFiles, async () => {
        selectedFilesList.value = []
        await refreshFiles(true)
      })
    } catch (error) {
      if (error.message !== 'Modal closed') {
        console.error('批量复制错误:', error)
      }
    }
  }

  const batchDelete = async () => {
    if (operationLoading.value) return

    try {
      const selectedCount = selectedFilesList.value.length
      if (selectedCount === 0) {
        window.appNotification.warning('请先选择要删除的文件')
        return
      }

      const deleteMode = getDeleteMode()
      const fileCountText = buildSelectedCountText(selectedCount)

      const modalConfig = deleteMode === 'permanent'
        ? {
            title: '确认批量彻底删除',
            content: `确定要彻底删除选中的${fileCountText}吗？删除后无法恢复！`,
            confirmText: '彻底删除',
            confirmClass: 'btn-danger',
            icon: 'trash'
          }
        : {
            title: '确认批量删除',
            content: `确定要将选中的${fileCountText}移入回收站吗？`,
            confirmText: '删除',
            confirmClass: 'btn-primary',
            icon: 'warning'
          }

      await confirm(modalConfig)

      try {
        setOperationLoading(true, 'batch_delete', null, `${selectedCount} 个项目`)
        const response = await axios.delete('/api/files/delete', {
          data: {
            account_id: selectedAccountId.value,
            file_ids: selectedFilesList.value,
            parent_id: currentPath.value
          },
          headers: {
            'Content-Type': 'application/json'
          }
        })

        if (response.data.success) {
          window.appNotification.success(response.data.message)
          selectedFilesList.value = []
          await loadFiles()
        } else {
          window.appNotification.error(response.data.message)
        }
      } catch (apiError) {
        window.appNotification.error(`批量删除失败: ${apiError.response?.data?.message || apiError.message}`)
      } finally {
        setOperationLoading(false)
      }
    } catch (error) {
      if (error.message !== 'Modal closed') {
        console.error('批量删除错误:', error)
      }
    }
  }

  return {
    createFolder,
    showFileActionModal,
    handleFileDownload,
    renameFile,
    deleteFile,
    moveFile,
    batchMove,
    batchDelete,
    copyFile,
    batchCopy
  }
}
