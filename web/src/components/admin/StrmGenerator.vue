<template>
  <div class="strm-generator">
    <div class="strm-header">
      <div class="tab-nav strm-tabs" role="tablist" aria-label="媒体管理视图切换">
        <button
          type="button"
          class="tab-btn strm-tab-btn"
          :class="{ active: activeTab === 'tasks' }"
          @click="activeTab = 'tasks'"
        >
          <i class="fas fa-tasks"></i>
          <span>STRM任务</span>
        </button>
        <button
          type="button"
          class="tab-btn strm-tab-btn tab-has-badge"
          :class="{ active: activeTab === 'organize' }"
          @click="activeTab = 'organize'"
        >
          <i class="fas fa-folder-tree"></i>
          <span>目录整理</span>
          <span class="tab-experimental-badge">实验功能</span>
        </button>
        <button
          type="button"
          class="tab-btn strm-tab-btn"
          :class="{ active: activeTab === 'emby' }"
          @click="activeTab = 'emby'"
        >
          <i class="fas fa-server"></i>
          <span>Emby反代</span>
        </button>
        <div class="tab-dropdown"
             @mouseenter="settingsMenuOpen = true"
             @mouseleave="settingsMenuOpen = false">
          <button
            type="button"
            class="tab-btn strm-tab-btn"
            :class="{ active: activeTab === 'settings' || activeTab === 'organizeSettings' }"
            aria-haspopup="true"
            :aria-expanded="settingsMenuOpen"
            @click="settingsMenuOpen = !settingsMenuOpen"
          >
            <i class="fas fa-cog"></i>
            <span>相关设置</span>
            <span class="tab-dropdown-arrow" :class="{ open: settingsMenuOpen }">▾</span>
          </button>
          <div v-if="settingsMenuOpen" class="tab-dropdown-menu">
            <button class="tab-dropdown-item"
                    :class="{ active: activeTab === 'settings' }"
                    @click="activeTab = 'settings'; settingsMenuOpen = false">
              <i class="fas fa-cog"></i>
              <span>STRM设置</span>
            </button>
            <button class="tab-dropdown-item"
                    :class="{ active: activeTab === 'organizeSettings' }"
                    @click="activeTab = 'organizeSettings'; settingsMenuOpen = false">
              <i class="fas fa-sliders-h"></i>
              <span>整理设置</span>
            </button>
          </div>
        </div>
        <button
          type="button"
          class="tab-btn strm-tab-btn"
          :class="{ active: activeTab === 'token' }"
          @click="activeTab = 'token'"
        >
          <i class="fas fa-key"></i>
          <span>令牌管理</span>
        </button>
      </div>

      <div class="strm-action">
        <button
          v-if="activeTab === 'tasks'"
          type="button"
          class="btn btn-primary"
          @click="openAddDialog"
        >
          <i class="fas fa-plus"></i>
          <span>添加任务</span>
        </button>
        <button
          v-if="activeTab === 'emby'"
          type="button"
          class="btn btn-primary"
          @click="openEmbyDialog"
        >
          <i class="fas fa-plus"></i>
          <span>新建反代</span>
        </button>
        <button
          v-if="activeTab === 'settings' || activeTab === 'organizeSettings'"
          type="button"
          class="btn btn-primary"
          :disabled="activeTab === 'organizeSettings' && organizeSaving"
          @click="activeTab === 'settings' ? saveStrmSettings() : saveOrganizeSettings()"
        >
          <i class="fas fa-save"></i>
          <span>保存设置</span>
        </button>
        <button
          v-if="activeTab === 'token'"
          type="button"
          class="btn btn-primary"
          @click="changeStrmToken"
        >
          <i class="fas fa-sync-alt"></i>
          <span>更换令牌</span>
        </button>
        <button
          v-if="activeTab === 'organize'"
          type="button"
          class="btn btn-primary"
          @click="openOrganizeAddDialog"
        >
          <i class="fas fa-plus"></i>
          <span>新建任务</span>
        </button>
      </div>
    </div>

    <div v-if="activeTab === 'tasks'" class="strm-panel">
      <div class="stats-cards">
        <div class="stats-card">
          <div class="stats-icon">
            <i class="fas fa-list"></i>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ tasks.length }}</div>
            <div class="stats-label">任务数量</div>
          </div>
        </div>
        <div class="stats-card">
          <div class="stats-icon running">
            <i class="fas fa-play"></i>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ enabledCount }}</div>
            <div class="stats-label">已启用</div>
          </div>
        </div>
        <div class="stats-card">
          <div class="stats-icon paused">
            <i class="fas fa-pause"></i>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ pausedCount }}</div>
            <div class="stats-label">已禁用</div>
          </div>
        </div>
        <div class="stats-card">
          <div class="stats-icon queued">
            <i class="fas fa-clock"></i>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ queuedCount }}</div>
            <div class="stats-label">排队中</div>
          </div>
        </div>
      </div>

      <div v-if="startupRemaining > 0" class="startup-countdown-banner">
        <i class="fas fa-hourglass-half fa-spin"></i>
        <span>任务启动中，预计 <strong>{{ startupRemaining }}</strong> 秒后开始执行...</span>
      </div>

      <div class="table-container task-table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>任务</th>
              <th>目录</th>
              <th>最后扫描</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.id" class="task-row">
              <td>
                <div class="task-main" :title="getTaskTitle(task)">
                  <div class="task-name">
                    <div class="name">{{ getDisplayTaskName(task.name) }}</div>
                    <span class="task-inline-status" :class="task.status === 'running' ? 'running' : 'paused'">
                      {{ task.status === 'running' ? '已启用' : '已禁用' }}
                    </span>
                  </div>
                </div>
              </td>
              <td class="path" :title="task.path">{{ task.path }}</td>
              <td>
                <div class="last-scan-inline" :title="getLastScanTitle(task)">
                  <span class="scan-status-icon" :class="getScanStatusClass(task)">
                    <svg v-if="task.last_scan_status === 'success' && !isTaskScanning(task)" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="m3.5 8.5 3 3 6-7" />
                    </svg>
                    <svg v-else-if="task.last_scan_status === 'error' && !isTaskScanning(task)" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M8 4.25v4.5" />
                      <circle cx="8" cy="11.75" r=".75" fill="currentColor" stroke="none" />
                      <path d="M8 1.75 14 14.25H2L8 1.75Z" />
                    </svg>
                    <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <circle cx="8" cy="8" r="5.75" />
                      <path d="M8 5.25v3.25l2 1.25" />
                    </svg>
                  </span>
                  <span class="last-scan-switch">
                    <span class="last-scan-text">{{ getLastScanPrimaryText(task) }}</span>
                    <span class="last-scan-summary">{{ getLastScanSummary(task) }}</span>
                  </span>
                </div>
              </td>
              <td>
                <div class="action-buttons">
                  <div class="task-status-switch" role="group" aria-label="任务启用切换">
                    <button
                      type="button"
                      class="task-status-btn"
                      :class="{ active: task.status === 'running' }"
                      title="启用"
                      @click="setTaskEnabled(task, true)"
                    >
                      <span class="task-status-text">启</span>
                    </button>
                    <button
                      type="button"
                      class="task-status-btn"
                      :class="{ active: task.status !== 'running' }"
                      title="禁用"
                      @click="setTaskEnabled(task, false)"
                    >
                      <span class="task-status-text">禁</span>
                    </button>
                  </div>
                  <button v-if="task.is_scanning" type="button" class="task-action-btn force-stop" title="强制停止" @click="forceStopTask(task.id)">
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <rect x="3" y="3" width="10" height="10" rx="1.5" />
                    </svg>
                  </button>
                  <div v-else class="run-menu-wrap">
                    <button type="button" class="task-action-btn" title="立即执行" @click="handleRunButtonClick(task)">
                      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="M8 2v12" />
                        <path d="m4.5 5.5 3.5-3.5 3.5 3.5" />
                      </svg>
                    </button>
                    <div v-if="task.branch_check_enabled" class="run-menu">
                      <button type="button" @click="runTask(task.id, 'full')">全部执行</button>
                      <button type="button" @click="runTask(task.id, 'branch')">分支执行</button>
                    </div>
                  </div>
                  <button type="button" class="task-action-btn" title="修改" @click="editTask(task)">
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M2.5 13.5h3l8-8-3-3-8 8v3z" />
                      <path d="M9.5 3.5l3 3" />
                    </svg>
                  </button>
                  <button type="button" class="task-action-btn danger" title="删除" @click="deleteTask(task.id)">
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

    <div v-if="activeTab === 'settings'" class="strm-panel">
      <div class="settings-group">
        <div class="group-title"><i class="fas fa-play-circle"></i> 播放与调度</div>
        <div class="group-item">
          <div class="group-label with-help">
            STRM播放地址基址
            <span class="help-icon" @mouseover="strmBaseUrlTooltipVisible = true" @mouseleave="strmBaseUrlTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmBaseUrlTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">播放地址基址说明</div>
                  <div class="tooltip-body">
                    <p>生成的 .strm 会写入该地址作为开头。</p>
                    <p>留空时默认使用本机地址：http://127.0.0.1:端口</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <input v-model="strmSettings.strm_base_url" type="text" class="group-input" placeholder="留空默认使用本机地址（http://127.0.0.1:5211）">
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            生成链接携带签名
            <span class="help-icon" @mouseover="strmSignatureTooltipVisible = true" @mouseleave="strmSignatureTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmSignatureTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">签名说明</div>
                  <div class="tooltip-body">
                    <p>开启后新生成的 .strm 链接会携带 sign 参数，播放时同时校验令牌和签名。</p>
                    <p>关闭后只校验 token，适合内网或需要最大兼容性的场景。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <label class="setting-switch">
            <input v-model="strmSettings.strm_signature_enabled" type="checkbox">
            <span></span>
          </label>
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            默认扫描间隔（分钟）
            <span class="help-icon" @mouseover="strmIntervalTooltipVisible = true" @mouseleave="strmIntervalTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmIntervalTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">默认扫描间隔说明</div>
                  <div class="tooltip-body">
                    <p>所有STRM任务统一使用该间隔执行扫描。</p>
                    <p>间隔越短，更新越及时，但会更频繁调用网盘API。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <input v-model.number="strmSettings.strm_default_scan_interval" type="number" class="group-input" min="1" max="1440">
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            任务并发数
            <span class="help-icon" @mouseover="strmTaskConcurrencyTooltipVisible = true" @mouseleave="strmTaskConcurrencyTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmTaskConcurrencyTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">任务并发数说明</div>
                  <div class="tooltip-body">
                    <p>控制同时允许多少条 STRM 任务进行扫描。</p>
                    <p>同一账号默认仍然串行执行，不会并发扫描。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <input v-model.number="strmSettings.strm_task_concurrency" type="number" class="group-input" min="1" max="10">
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            默认同步文件类型
            <span class="help-icon" @mouseover="strmDefaultExtensionsTooltipVisible = true" @mouseleave="strmDefaultExtensionsTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmDefaultExtensionsTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">默认同步文件类型说明</div>
                  <div class="tooltip-body">
                    <p>STRM 任务统一按这里的媒体扩展名扫描。</p>
                    <p>用英文分号分隔；留空时使用程序内置默认值。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <input v-model="strmSettings.strm_default_extensions" type="text" class="group-input">
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            小文件过滤（MB）
            <span class="help-icon" @mouseover="strmMinSizeTooltipVisible = true" @mouseleave="strmMinSizeTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmMinSizeTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">小文件过滤说明</div>
                  <div class="tooltip-body">
                    <p>生成 .strm 时忽略小于该大小的媒体文件。</p>
                    <p>填 0 表示不过滤，可用于跳过预告片、样片等小视频。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <input v-model.number="strmSettings.strm_min_file_size_mb" type="number" class="group-input" min="0" max="10240">
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            同名冲突策略
            <span class="help-icon" @mouseover="strmConflictTooltipVisible = true" @mouseleave="strmConflictTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmConflictTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">同名冲突说明</div>
                  <div class="tooltip-body">
                    <p>同目录存在同名不同后缀文件时，只生成一个 .strm。</p>
                    <p>这里决定保留哪一个媒体文件的播放地址。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <CustomSelect v-model="strmSettings.strm_conflict_policy" :options="conflictPolicyOptions" class="settings-select" placeholder="请选择" />
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            ISO播放规则
            <span class="help-icon" @mouseover="strmIsoModeTooltipVisible = true" @mouseleave="strmIsoModeTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmIsoModeTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">ISO播放规则说明</div>
                  <div class="tooltip-body">
                    <p>仅影响 STRM 播放 ISO 类文件：跟随网盘模式／或强制走 LitePan 代理。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <CustomSelect v-model="strmSettings.strm_iso_play_mode" :options="strmIsoPlayModeOptions" class="settings-select" placeholder="请选择" />
        </div>
      </div>

      <div class="settings-group">
        <div class="group-title"><i class="fas fa-images"></i> 元数据同步</div>
        <div class="group-item">
          <div class="group-label with-help">
            元数据扩展名
            <span class="help-icon" @mouseover="strmMetadataExtTooltipVisible = true" @mouseleave="strmMetadataExtTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmMetadataExtTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">元数据扩展名说明</div>
                  <div class="tooltip-body">
                    <p>任务开启同步元数据后，会按这里的扩展名同步同目录文件。</p>
                    <p>用英文分号分隔；留空时即使任务开启也不会同步元数据。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <input v-model="strmSettings.strm_metadata_extensions" type="text" class="group-input" placeholder="srt;ass;ssa;sub;nfo;jpg;jpeg;png;webp">
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            同步上层元数据
            <span class="help-icon" @mouseover="strmMetadataParentTooltipVisible = true" @mouseleave="strmMetadataParentTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmMetadataParentTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">上层元数据说明</div>
                  <div class="tooltip-body">
                    <p>开启后，如果某个目录的子目录中存在影片，也会同步该目录下的海报、nfo等小文件。</p>
                    <p>适合电视剧的“剧集目录 / Season 1 / 媒体文件”结构。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <label class="setting-switch">
            <input v-model="strmSettings.strm_metadata_parent_enabled" type="checkbox">
            <span></span>
          </label>
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            元数据大小上限（MB）
            <span class="help-icon" @mouseover="strmMetadataSizeTooltipVisible = true" @mouseleave="strmMetadataSizeTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmMetadataSizeTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">元数据大小上限说明</div>
                  <div class="tooltip-body">
                    <p>只同步不超过该大小的元数据文件，避免误下载大文件。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <input v-model.number="strmSettings.strm_metadata_max_size_mb" type="number" class="group-input" min="1" max="1024">
        </div>
      </div>

      <div class="settings-group">
        <div class="group-title"><i class="fas fa-link"></i> 站点替换</div>
        <div class="group-item">
          <div class="group-label with-help">
            新站点URL（含协议）
            <span class="help-icon" @mouseover="strmDomainTooltipVisible = true" @mouseleave="strmDomainTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmDomainTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">域名替换说明</div>
                  <div class="tooltip-body">
                    <p>会批量替换 strm 目录下所有 .strm 文件的域名。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <input v-model="replaceDomain" type="text" class="group-input" placeholder="例如：http://192.168.1.1:5211">
        </div>
        <div class="group-item replace-domain-actions">
          <button type="button" class="btn btn-primary" @click="replaceAllDomains">
            <i class="fas fa-sync"></i> 一键替换
          </button>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'organize'" class="strm-panel">
        <div class="stats-cards">
          <div class="stats-card">
            <div class="stats-icon"><i class="fas fa-list"></i></div>
            <div class="stats-content">
              <div class="stats-number">{{ organizeTasks.length }}</div>
              <div class="stats-label">任务数量</div>
            </div>
          </div>
        </div>

        <div v-if="organizeTasks.length === 0" class="empty-state">
          <i class="fas fa-folder-tree empty-icon"></i>
          <p class="empty-title">暂无整理任务</p>
          <p class="empty-desc">点击右上角「新建任务」创建第一个媒体整理任务</p>
        </div>

        <div v-else class="table-container organize-table-container">
          <table class="data-table organize-table">
            <thead>
              <tr>
                <th>任务</th>
                <th>目标目录</th>
                <th>操作方式</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in organizeTasks" :key="task.id" class="task-row">
                <td>
                  <div class="task-main" :title="`${task.task_name} · ${getAccountName(task.account_id)}`">
                    <div class="task-name">
                      <div class="name">{{ task.task_name }}</div>
                    </div>
                    <div class="organize-account-sub">{{ getAccountName(task.account_id) }}</div>
                  </div>
                </td>
                <td class="path organize-path" :title="task.config?.target_directory">{{ task.config?.target_directory || '-' }}</td>
                <td>
                  <span class="mode-badge compact">{{ task.config?.action_type === 'rename' ? '原地' : '移动' }}</span>
                </td>
                <td>
                  <div class="organize-status-cell" :title="getOrganizeTaskStatusTitle(task)">
                    <span class="scan-status-icon" :class="getOrganizeTaskStatusClass(task)">
                      <svg v-if="!isOrganizeTaskActive(task) && task.last_run_result && (task.last_run_result.failed || 0) === 0" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="m3.5 8.5 3 3 6-7" />
                      </svg>
                      <svg v-else-if="!isOrganizeTaskActive(task) && task.last_run_result && (task.last_run_result.failed || 0) > 0" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="M8 4.25v4.5" />
                        <circle cx="8" cy="11.75" r=".75" fill="currentColor" stroke="none" />
                        <path d="M8 1.75 14 14.25H2L8 1.75Z" />
                      </svg>
                      <svg v-else viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <circle cx="8" cy="8" r="5.75" />
                        <path d="M8 5.25v3.25l2 1.25" />
                      </svg>
                    </span>
                    <span class="organize-status-text">
                      <span class="organize-status-primary">{{ getOrganizeTaskStatusText(task) }}</span>
                      <span v-if="task.last_run_result" class="organize-status-summary">
                        {{ task.last_run_result.total || 0 }} 项 · 改{{ task.last_run_result.renamed || 0 }} · 移{{ task.last_run_result.moved || 0 }} · 失{{ task.last_run_result.failed || 0 }}
                      </span>
                    </span>
                  </div>
                </td>
                <td>
                  <div class="action-buttons">
                    <button v-if="isOrganizeTaskActive(task)" class="task-action-btn force-stop" @click="stopOrganizeTask(task.id)" :disabled="task.status === 'stopping'" :title="task.status === 'stopping' ? '正在停止' : '停止整理'">
                      <i class="fas fa-stop"></i>
                    </button>
                    <button v-else class="task-action-btn play" @click="previewOrganizePlan(task)" title="预览并执行">
                      <i class="fas fa-play"></i>
                    </button>
                    <button class="task-action-btn" @click="openOrganizeLogPanel(task.id)" title="查看日志">
                      <i class="fas fa-terminal"></i>
                    </button>
                    <button class="task-action-btn" @click="editOrganizeTask(task)" title="编辑">
                      <i class="fas fa-edit"></i>
                    </button>
                    <button class="task-action-btn danger" @click="deleteOrganizeTask(task.id)" title="删除">
                      <i class="fas fa-trash-alt"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="organizeLogTaskId" class="organize-log-panel">
          <div class="organize-log-header">
            <div>
              <i class="fas fa-terminal"></i>
              <span>整理日志</span>
              <small v-if="organizeLogTaskName">({{ organizeLogTaskName }})</small>
            </div>
            <button class="task-action-btn" @click="closeOrganizeLogPanel" title="关闭日志">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div ref="organizeLogBodyRef" class="organize-log-body">
            <div v-if="organizeLogs.length === 0" class="organize-log-empty">等待任务输出...</div>
            <div v-for="(line, index) in organizeLogs" :key="index" class="organize-log-line">
              <span class="organize-log-time">[{{ line.time }}]</span>
              <span>{{ line.message }}</span>
            </div>
          </div>
        </div>

      <!-- 新建/编辑弹窗 -->
      <div v-if="organizeShowDialog" class="dialog-overlay">
        <div class="dialog" @click.stop>
          <div class="dialog-header">
            <h3>{{ organizeEditingId ? '修改任务' : '新建整理任务' }}</h3>
            <button @click="organizeShowDialog = false" class="close-btn">&times;</button>
          </div>
          <div class="dialog-content add-config-form">
            <div class="form-row">
              <div class="form-group">
                <label>任务名称</label>
                <input v-model="organizeForm.task_name" class="form-input" maxlength="10" placeholder="例如：电影整理">
              </div>
              <div class="form-group">
                <label>网盘账号</label>
                <CustomSelect v-model="organizeForm.account_id" :options="accountOptions" placeholder="请选择账号" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>目标目录</label>
                <div class="input-group integrated">
                  <input v-model="organizeForm.target_directory" readonly class="form-input" placeholder="需要整理的目录">
                  <button class="btn btn-primary browse-btn" @click="browseOrganizeDir">浏览</button>
                </div>
              </div>
              <div class="form-group">
                <label>操作方式</label>
                <div class="toggle-btn-group">
                  <button type="button" class="toggle-btn" :class="{ active: organizeForm.action_type === 'rename' }" @click="switchOrganizeActionType('rename')">原地重命名</button>
                  <button type="button" class="toggle-btn" :class="{ active: organizeForm.action_type === 'move' }" @click="switchOrganizeActionType('move')">移动到新目录</button>
                </div>
              </div>
            </div>
            <div class="form-row" v-if="organizeForm.action_type === 'move'">
              <div class="form-group">
                <label>目标根目录</label>
                <div class="input-group integrated">
                  <input v-model="organizeForm.target_root" readonly class="form-input" placeholder="整理后的输出目录">
                  <button class="btn btn-primary browse-btn" @click="browseOrganizeTargetRoot">浏览</button>
                </div>
              </div>
              <div class="form-group">
                <label>媒体类型</label>
                <select v-model="organizeForm.media_type" class="form-input">
                  <option value="auto">自动检测</option>
                  <option value="movie">电影</option>
                  <option value="tv">剧集</option>
                </select>
              </div>
            </div>
            <div class="form-row" v-else>
              <div class="form-group">
                <label>
                  整理标识
                  <span class="label-hint">必填，可自定义（如 v2、myrelease）</span>
                </label>
                <input v-model="organizeForm.rename_marker" class="form-input" placeholder="tmdb（推荐，{tmdb-xxx}）或自定义如 v2">
              </div>
              <div class="form-group">
                <label>媒体类型</label>
                <select v-model="organizeForm.media_type" class="form-input">
                  <option value="auto">自动检测</option>
                  <option value="movie">电影</option>
                  <option value="tv">剧集</option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>使用 TMDB 匹配</label>
                <CustomSelect v-model="organizeForm.use_tmdb" :options="boolOptions" placeholder="请选择" />
              </div>
              <div class="form-group">
                <label>启用 ffprobe（暂未实现）</label>
                <CustomSelect v-model="organizeForm.use_ffprobe" :options="boolOptions" placeholder="请选择" />
              </div>
            </div>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn btn-primary" :disabled="organizeSaving" @click="saveOrganizeTask">
              <i class="fas fa-save"></i> {{ organizeEditingId ? '更新任务' : '保存任务' }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="organizePlanDialogVisible" class="dialog-overlay">
        <div class="dialog organize-plan-dialog" @click.stop>
          <div class="dialog-header">
            <h3>整理计划预览 <small v-if="organizePlanTaskName">· {{ organizePlanTaskName }}</small></h3>
            <button @click="closeOrganizePlanDialog" class="close-btn">&times;</button>
          </div>
          <div class="dialog-content">
            <div v-if="organizePlanLoading" class="organize-plan-loading">
              <div class="organize-plan-loading-spinner"><i class="fas fa-circle-notch fa-spin"></i></div>
              <div class="organize-plan-loading-title">正在扫描并生成计划...</div>
              <div class="organize-plan-loading-progress">
                <span class="metric"><i class="fas fa-folder"></i> 扫描目录 {{ organizePlanProgress.scanned_dirs || 0 }}</span>
                <span class="metric"><i class="fas fa-film"></i> 媒体文件 {{ organizePlanProgress.scanned_files || 0 }}</span>
                <span class="metric"><i class="fas fa-layer-group"></i> 已分组 {{ organizePlanProgress.groups || 0 }}</span>
                <span class="metric"><i class="fas fa-list-check"></i> 已生成 {{ organizePlanProgress.actions || 0 }} 个动作</span>
              </div>
              <div v-if="organizePlanProgress.current_dir" class="organize-plan-loading-current">
                当前批次: {{ organizePlanProgress.current_dir }}
              </div>
            </div>
            <template v-else>
              <div
                v-if="organizePlanTmdbStatus && organizePlanTmdbStatus !== 'available' && organizePlanTmdbStatus !== 'disabled_task'"
                class="organize-plan-tmdb-banner"
              >
                <i class="fas fa-triangle-exclamation"></i>
                <span v-if="organizePlanTmdbStatus === 'no_api_key'">未配置 TMDB API Key，本次计划仅使用文件名识别；建议在设置中填入 Key 后重新生成。</span>
                <span v-else-if="organizePlanTmdbStatus === 'unreachable'">TMDB 不可达，本次计划跳过了 TMDB 匹配；请检查网络或代理后再点击「重新生成」。</span>
                <span v-else>TMDB 状态异常: {{ organizePlanTmdbStatus }}</span>
                <button type="button" class="organize-plan-tmdb-test" :disabled="tmdbTesting" @click="testTmdbConnectivity">
                  <i class="fas" :class="tmdbTesting ? 'fa-spinner fa-spin' : 'fa-plug'"></i>
                  {{ tmdbTesting ? '测试中...' : '立即测试' }}
                </button>
              </div>
              <div class="organize-plan-summary">
                <span class="summary-pill"><i class="fas fa-list"></i> 共 {{ organizePlanRelocates.length }} 项整理</span>
                <span v-if="organizePlanSkipped.length" class="summary-pill warning"><i class="fas fa-circle-info"></i> 跳过 {{ organizePlanSkipped.length }} 项</span>
                <span v-if="organizePlanNoTmdbCount > 0" class="summary-pill warning"><i class="fas fa-triangle-exclamation"></i> {{ organizePlanNoTmdbCount }} 项未匹配 TMDB（无 ID）</span>
              </div>
              <div v-if="organizePlanGroups.length === 0" class="empty-state">
                <p class="empty-title">当前没有可执行的计划</p>
                <p class="empty-desc">点击「重新生成」让程序扫描目录并生成新的计划</p>
              </div>
              <div v-else class="organize-plan-list">
                <div v-for="group in organizePlanGroups" :key="group.key" class="organize-plan-group" :class="{ expanded: group.expanded, editing: !!(group.dirAction && organizePlanEditingId === group.dirAction.id) }">
                  <div class="organize-plan-group-header" @click="toggleOrganizePlanGroup(group.key)">
                    <i class="fas organize-plan-group-chevron" :class="group.expanded ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
                    <div v-if="group.dirAction && organizePlanEditingId === group.dirAction.id" class="organize-plan-edit" @click.stop>
                      <div class="organize-plan-edit-source">{{ group.titleOld || group.title }}</div>
                      <i class="fas fa-arrow-right organize-plan-arrow"></i>
                      <input
                        v-model="organizePlanEditingName"
                        class="organize-plan-edit-input"
                        @keydown.enter="commitPlanActionEdit(group.dirAction)"
                        @keydown.esc="cancelPlanActionEdit"
                      />
                      <button class="plan-row-btn ok" @click.stop="commitPlanActionEdit(group.dirAction)" :disabled="organizePlanEditingSaving"><i class="fas fa-check"></i></button>
                      <button class="plan-row-btn cancel" @click.stop="cancelPlanActionEdit"><i class="fas fa-xmark"></i></button>
                    </div>
                    <div v-else class="organize-plan-group-title-wrap">
                      <span v-if="group.hasDirInfo" class="organize-plan-group-title" :title="group.titleOld + ' → ' + group.titleNew">
                        <span class="organize-plan-old">{{ group.titleOld }}</span>
                        <i class="fas fa-arrow-right organize-plan-arrow"></i>
                        <span class="organize-plan-new">{{ group.titleNew }}</span>
                      </span>
                      <span v-else class="organize-plan-group-title" :title="group.title">{{ group.title }}</span>
                    </div>
                    <span class="organize-plan-group-right">
                      <span class="organize-plan-group-badges">
                        <span v-if="group.tmdbId" class="organize-plan-group-tmdb">tmdb-{{ group.tmdbId }}</span>
                        <span v-else class="organize-plan-group-notmdb">无 TMDB</span>
                        <span class="organize-plan-group-count">{{ group.actionCount }} 项</span>
                      </span>
                      <span class="organize-plan-group-controls">
                        <button v-if="group.dirAction" class="plan-row-btn" @click.stop="startPlanActionEdit(group.dirAction)" title="编辑作品目录名"><i class="fas fa-pen"></i></button>
                        <button class="plan-row-btn danger" @click.stop="removePlanGroup(group)" title="从计划中移除整组"><i class="fas fa-trash"></i></button>
                      </span>
                    </span>
                  </div>
                  <div v-if="group.expanded" class="organize-plan-group-body">
                    <div v-if="group.collapsedRanges.length" class="organize-plan-row collapsed-range" v-for="(range, ri) in group.collapsedRanges" :key="'range-'+group.key+'-'+ri">
                      <div class="organize-plan-icon" :class="actionIconClass(range.sample)"><i :class="actionIconName(range.sample)"></i></div>
                      <div class="organize-plan-body">
                        <div class="organize-plan-title">
                          <span class="organize-plan-collapsed-label">
                            S{{ String(range.season).padStart(2,'0') }} ·
                            <template v-if="range.consecutive">E{{ String(range.startEpisode).padStart(2,'0') }}–E{{ String(range.endEpisode).padStart(2,'0') }}</template>
                            <template v-else>E{{ String(range.startEpisode).padStart(2,'0') }}–E{{ String(range.endEpisode).padStart(2,'0') }} 中</template>
                            共 {{ range.actions.length }} 集（命名一致）
                          </span>
                        </div>
                        <div class="organize-plan-sub">
                          <span class="organize-plan-old-mini">{{ range.samplePattern.oldPattern }}</span>
                          <i class="fas fa-arrow-right organize-plan-arrow"></i>
                          <span class="organize-plan-new-mini">{{ range.samplePattern.newPattern }}</span>
                          <button class="plan-row-toggle" @click.stop="expandCollapsedRange(group.key, ri)">展开 {{ range.actions.length }} 条</button>
                        </div>
                      </div>
                    </div>
                    <div v-for="action in group.visibleActions" :key="action.id" class="organize-plan-row" :class="{ editing: organizePlanEditingId === action.id, edited: action.metadata && action.metadata.edited }">
                      <div class="organize-plan-icon" :class="actionIconClass(action)"><i :class="actionIconName(action)"></i></div>
                      <div class="organize-plan-body">
                        <div v-if="organizePlanEditingId === action.id" class="organize-plan-edit">
                          <div class="organize-plan-edit-source">{{ action.source_name }}</div>
                          <i class="fas fa-arrow-right organize-plan-arrow"></i>
                          <input
                            v-model="organizePlanEditingName"
                            class="organize-plan-edit-input"
                            @keydown.enter="commitPlanActionEdit(action)"
                            @keydown.esc="cancelPlanActionEdit"
                          />
                          <button class="plan-row-btn ok" @click="commitPlanActionEdit(action)" :disabled="organizePlanEditingSaving"><i class="fas fa-check"></i></button>
                          <button class="plan-row-btn cancel" @click="cancelPlanActionEdit"><i class="fas fa-xmark"></i></button>
                        </div>
                        <div v-else class="organize-plan-title">
                          <span class="organize-plan-old">{{ action.source_name || '?' }}</span>
                          <i class="fas fa-arrow-right organize-plan-arrow"></i>
                          <span class="organize-plan-new">{{ action.target_name || '?' }}</span>
                          <span class="organize-plan-row-controls">
                            <button class="plan-row-btn" @click="startPlanActionEdit(action)" title="编辑目标名"><i class="fas fa-pen"></i></button>
                            <button class="plan-row-btn danger" @click="removePlanAction(action)" title="从计划中移除"><i class="fas fa-trash"></i></button>
                          </span>
                        </div>
                        <div class="organize-plan-sub" v-if="organizePlanEditingId !== action.id">
                          {{ action.reason }}
                          <span v-if="action.confidence">· 识别可信度 {{ Math.round((action.confidence||0)*100) }}%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="organizePlanSkipped.length" class="organize-plan-skipped">
                  <div class="organize-plan-skipped-title" @click="organizePlanSkipExpanded = !organizePlanSkipExpanded">
                    <i class="fas" :class="organizePlanSkipExpanded ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
                    <span>跳过 {{ organizePlanSkipped.length }} 项</span>
                    <span class="organize-plan-skipped-reasons-inline">
                      <span v-for="group in organizePlanSkipGroups" :key="group.reason" class="organize-plan-skipped-reason-chip">
                        {{ group.reason || '其它' }} · {{ group.items.length }}
                      </span>
                    </span>
                  </div>
                  <div v-if="organizePlanSkipExpanded" class="organize-plan-skipped-body">
                    <div v-for="group in organizePlanSkipGroups" :key="group.reason" class="organize-plan-skipped-reason-group">
                      <div class="organize-plan-skipped-reason-header" @click="toggleOrganizePlanSkipReason(group.reason)">
                        <i class="fas" :class="organizePlanSkipExpandedReasons[group.reason] ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
                        <span class="organize-plan-skipped-reason-label">{{ group.reason || '其它' }}</span>
                        <span class="organize-plan-skipped-reason-count">{{ group.items.length }}</span>
                      </div>
                      <div v-if="organizePlanSkipExpandedReasons[group.reason]" class="organize-plan-skipped-reason-files">
                        <div
                          v-for="(item, idx) in (organizePlanSkipShowAll[group.reason] ? group.items : group.items.slice(0, ORGANIZE_PLAN_SKIP_PREVIEW_LIMIT))"
                          :key="idx"
                          class="organize-plan-skipped-row"
                        >{{ item.file_name }}</div>
                        <div
                          v-if="!organizePlanSkipShowAll[group.reason] && group.items.length > ORGANIZE_PLAN_SKIP_PREVIEW_LIMIT"
                          class="organize-plan-skipped-more"
                          @click="showOrganizePlanSkipAll(group.reason)"
                        >
                          还有 {{ group.items.length - ORGANIZE_PLAN_SKIP_PREVIEW_LIMIT }} 项，点击展开（可能略卡）
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
          <div class="dialog-footer">
            <button type="button" class="btn" :disabled="organizePlanLoading || organizePlanApplying" @click="refreshOrganizePlan(true)">
              <i class="fas fa-sync"></i> 重新生成
            </button>
            <button type="button" class="btn btn-primary" :disabled="organizePlanLoading || organizePlanApplying || organizePlanRelocates.length === 0" @click="applyOrganizePlan">
              <i class="fas fa-check"></i> {{ organizePlanApplying ? '执行中...' : '确认执行' }}
            </button>
          </div>
        </div>
      </div>

    </div>

    <div v-if="activeTab === 'organizeSettings'" class="strm-panel">
      <div class="settings-group">
        <div class="group-title"><i class="fas fa-network-wired"></i> 代理设置</div>
        <div class="group-item">
          <div class="group-label">启用代理</div>
          <label class="setting-switch">
            <input v-model="organizeSettings.proxy_enabled" type="checkbox">
            <span></span>
          </label>
        </div>
        <div class="group-item">
          <div class="group-label">代理地址</div>
          <input v-model="organizeSettings.proxy_url" class="group-input" placeholder="http://127.0.0.1:1080 或 socks5://127.0.0.1:1080">
        </div>
        <div class="group-item">
          <div class="group-label">代理用户名</div>
          <input
            v-model="organizeSettings.proxy_username"
            class="group-input"
            name="litepan-organize-proxy-user"
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            readonly
            placeholder="可选"
            @focus="$event.target.removeAttribute('readonly')"
          >
        </div>
        <div class="group-item">
          <div class="group-label">代理密码</div>
          <input
            v-model="organizeSettings.proxy_password"
            type="password"
            class="group-input"
            name="litepan-organize-proxy-secret"
            autocomplete="new-password"
            autocapitalize="off"
            spellcheck="false"
            readonly
            placeholder="可选"
            @focus="$event.target.removeAttribute('readonly')"
          >
        </div>
      </div>

      <div class="settings-group">
        <div class="group-title">
          <span><i class="fas fa-database"></i> TMDB 设置</span>
          <button type="button" class="tmdb-test-btn" :disabled="tmdbTesting" @click="testTmdbConnectivity">
            <i class="fas" :class="tmdbTesting ? 'fa-spinner fa-spin' : 'fa-plug'"></i>
            {{ tmdbTesting ? '测试中...' : '测试连通性' }}
          </button>
        </div>
        <div class="group-item">
          <div class="group-label">TMDB API Key</div>
          <input v-model="organizeSettings.tmdb_api_key" class="group-input" placeholder="留空使用内置默认 Key">
        </div>
        <div class="group-item">
          <div class="group-label">TMDB 语言（影响搜索和命名）</div>
          <CustomSelect v-model="organizeSettings.tmdb_language" :options="tmdbLanguageOptions" class="settings-select" placeholder="请选择" />
        </div>
      </div>

      <div class="settings-group">
        <div class="group-title"><i class="fas fa-tachometer-alt"></i> API 请求节流</div>
        <div class="group-item">
          <div class="group-label">API额外补偿间隔(毫秒)</div>
          <input v-model.number="organizeSettings.api_request_interval_ms" type="number" class="group-input" min="100" max="10000">
        </div>
        <div class="group-item">
          <div class="group-label">ffprobe 请求间隔（毫秒）</div>
          <input v-model.number="organizeSettings.ffprobe_request_interval_ms" type="number" class="group-input" min="500" max="30000">
        </div>
        <div class="group-item">
          <div class="group-label">TMDB 请求间隔（毫秒）</div>
          <input v-model.number="organizeSettings.tmdb_request_interval_ms" type="number" class="group-input" min="100" max="5000">
        </div>
      </div>

      <div class="settings-group">
        <div class="group-title"><i class="fas fa-file-video"></i> 文件识别与整理规则</div>
        <div class="group-item">
          <div class="group-label">媒体文件后缀（分号分隔）</div>
          <input v-model="organizeSettings.file_extensions" class="group-input" placeholder="mkv;mp4;avi;ts;mov...">
        </div>
        <div class="group-item">
          <div class="group-label">元数据文件后缀（分号分隔）</div>
          <input v-model="organizeSettings.metadata_extensions" class="group-input" placeholder="nfo;ass;srt;sub...">
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            每次最多整理作品数
            <span class="help-icon" @mouseover="organizeMaxWorksTooltipVisible = true" @mouseleave="organizeMaxWorksTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="organizeMaxWorksTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">分批整理说明</div>
                  <div class="tooltip-body">
                    <p>每次生成计划最多包含这么多部作品（一部电影或一部剧集算 1 部），达到上限后停止扫描。</p>
                    <p>已整理过的（带 tmdb 标识）不计入此数。</p>
                    <p>执行完后再次生成计划即可处理剩余作品。0 表示不限制（不推荐用于大库）。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <input v-model.number="organizeSettings.max_works_per_run" type="number" class="group-input" min="0" max="10000" placeholder="50">
        </div>
        <div class="group-item">
          <div class="group-label with-help">
            同名冲突处理
            <span class="help-icon" @mouseover="conflictPolicyTooltipVisible = true" @mouseleave="conflictPolicyTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="conflictPolicyTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">同名冲突处理说明</div>
                  <div class="tooltip-body">
                    <p>执行整理时，若目标目录已存在同名文件：</p>
                    <p><b>跳过</b>：保留目标已有文件，跳过该项（推荐，更安全）</p>
                    <p><b>覆盖</b>：先删除目标已有同名文件，再写入新文件</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <CustomSelect v-model="organizeConflictPolicy" :options="organizeConflictPolicyOptions" class="settings-select" placeholder="请选择" />
        </div>
      </div>

      <div class="settings-group">
        <div class="group-title"><i class="fas fa-tags"></i> 媒体信息标签排序</div>
        <div class="group-item">
          <div class="group-label with-help">
            强迫症模式
            <span class="help-icon" @mouseover="organizeAlignTooltipVisible = true" @mouseleave="organizeAlignTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="organizeAlignTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">强迫症模式说明</div>
                  <div class="tooltip-body">
                    <p>开启后，同一后缀文件将保持媒体信息一致。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <label class="setting-switch">
            <input v-model="organizeSettings.align_media_tags" type="checkbox">
            <span></span>
          </label>
        </div>
        <p style="font-size:13px;color:#718096;margin:0 0 12px 0;">拖拽标签调整顺序，点击 × 移除。文件名按此顺序生成媒体信息。</p>
        <div class="tag-editor-box">
          <span
            v-for="(key, index) in tagOrder"
            :key="key"
            class="tag-chip"
            :class="{ 'drag-over': dragOverIndex === index }"
            draggable="true"
            @dragstart="onTagDragStart($event, index)"
            @dragover.prevent="onTagDragOver($event, index)"
            @dragleave="dragOverIndex = null"
            @drop="onTagDrop($event, index)"
            @dragend="onTagDragEnd"
          >
            <span class="tag-chip-text">{{ TAG_LABELS[key] }}</span>
            <span class="tag-chip-remove" @click.stop="removeTag(key)">&times;</span>
          </span>
          <span v-if="tagOrder.length === 0" class="tag-placeholder">点击下方标签添加到编辑框</span>
        </div>
        <div class="tag-pool" v-if="disabledTags.length > 0">
          <span
            v-for="key in disabledTags"
            :key="key"
            class="tag-chip tag-chip-add"
            @click="addTag(key)"
          >
            + {{ TAG_LABELS[key] }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'emby'" class="strm-panel">
      <div class="stats-cards">
        <div class="stats-card">
          <div class="stats-icon">
            <i class="fas fa-server"></i>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ embyProxies.length }}</div>
            <div class="stats-label">反代数量</div>
          </div>
        </div>
        <div class="stats-card">
          <div class="stats-icon running">
            <i class="fas fa-play"></i>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ embyRunningCount }}</div>
            <div class="stats-label">运行中</div>
          </div>
        </div>
        <div class="stats-card">
          <div class="stats-icon paused">
            <i class="fas fa-pause"></i>
          </div>
          <div class="stats-content">
            <div class="stats-number">{{ embyPausedCount }}</div>
            <div class="stats-label">已暂停</div>
          </div>
        </div>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>反代</th>
              <th>Emby地址</th>
              <th>代理入口</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="proxy in embyProxies" :key="proxy.id" class="task-row">
              <td>
                <div class="task-main" :title="proxy.name">
                  <div class="task-name">
                    <div class="name">{{ proxy.name }}</div>
                    <span class="task-inline-status" :class="proxy.status === 'running' ? 'running' : 'paused'">
                      {{ proxy.status === 'running' ? '运行中' : '已暂停' }}
                    </span>
                  </div>
                </div>
              </td>
              <td class="path" :title="proxy.emby_url">{{ proxy.emby_url }}</td>
              <td class="path" :title="proxy.proxy_url">{{ proxy.proxy_url }}</td>
              <td>
                <div class="action-buttons">
                  <div class="task-status-switch" role="group" aria-label="Emby反代启用切换">
                    <button
                      type="button"
                      class="task-status-btn"
                      :class="{ active: proxy.status === 'running' }"
                      title="启用"
                      @click="setEmbyProxyEnabled(proxy, true)"
                    >
                      <span class="task-status-text">启</span>
                    </button>
                    <button
                      type="button"
                      class="task-status-btn"
                      :class="{ active: proxy.status !== 'running' }"
                      title="暂停"
                      @click="setEmbyProxyEnabled(proxy, false)"
                    >
                      <span class="task-status-text">停</span>
                    </button>
                  </div>
                  <button type="button" class="task-action-btn" title="测试连接" @click="testEmbyProxy(proxy.id)">
                    <i class="fas fa-plug"></i>
                  </button>
                  <button type="button" class="task-action-btn" title="复制入口" @click="copyEmbyProxyUrl(proxy.proxy_url)">
                    <i class="fas fa-copy"></i>
                  </button>
                  <button type="button" class="task-action-btn" title="修改" @click="editEmbyProxy(proxy)">
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M2.5 13.5h3l8-8-3-3-8 8v3z" />
                      <path d="M9.5 3.5l3 3" />
                    </svg>
                  </button>
                  <button type="button" class="task-action-btn danger" title="删除" @click="deleteEmbyProxy(proxy.id)">
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

    <div v-if="activeTab === 'token'" class="strm-panel">
      <div class="settings-group">
        <div class="group-title"><i class="fas fa-key"></i> STRM 令牌</div>
        <div class="group-item">
          <div class="group-label with-help">
            STRM访问令牌
            <span class="help-icon" @mouseover="strmTokenTooltipVisible = true" @mouseleave="strmTokenTooltipVisible = false">
              <i class="fas fa-question-circle"></i>
              <div class="tooltip" v-show="strmTokenTooltipVisible">
                <div class="tooltip-content">
                  <div class="tooltip-title">令牌说明</div>
                  <div class="tooltip-body">
                    <p>用于媒体端访问播放入口，只读。</p>
                  </div>
                </div>
              </div>
            </span>
          </div>
          <input v-model="strmSettings.strm_token" type="text" class="group-input" readonly>
        </div>
      </div>
    </div>

    <div v-if="embyShowDialog" class="dialog-overlay">
      <div class="dialog" @click="handleEmbyModalClick">
        <div class="dialog-header">
          <h3>{{ embyEditingId ? '修改反代' : '新建反代' }}</h3>
          <button @click="closeEmbyDialog" class="close-btn">&times;</button>
        </div>

        <div class="dialog-content add-config-form">
          <div class="form-row">
            <div class="form-group">
              <label>反代名称</label>
              <input v-model="embyForm.name" type="text" class="form-input" placeholder="例如：家庭Emby">
            </div>
            <div class="form-group">
              <label>反代监听端口</label>
              <input v-model.number="embyForm.proxy_port" type="number" class="form-input" min="1" max="65535" placeholder="例如：8097">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Emby地址</label>
              <input v-model="embyForm.emby_url" type="text" class="form-input" placeholder="http://" @focus="() => { if (!embyForm.emby_url) embyForm.emby_url = 'http://' }">
            </div>
            <div class="form-group">
              <label>API Key</label>
              <input v-model="embyForm.api_key" type="password" name="emby_api_key" autocomplete="new-password" class="form-input" placeholder="Emby 控制台 API 密钥">
            </div>
          </div>
        </div>

        <div class="dialog-footer">
          <button @click="saveEmbyProxy" class="btn btn-primary" :disabled="saving">
            <i class="fas fa-save"></i> {{ embyEditingId ? '更新反代' : '保存反代' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showDialog" class="dialog-overlay">
      <div class="dialog" @click="handleModalClick">
        <div class="dialog-header">
          <h3>{{ editingId ? '修改任务' : '添加任务' }}</h3>
          <button @click="closeDialog" class="close-btn">&times;</button>
        </div>

        <div class="dialog-content add-config-form">
          <div class="form-row">
            <div class="form-group">
              <label>任务名称</label>
              <input
                v-model="form.name"
                type="text"
                class="form-input"
                placeholder="例如：百度电视剧（最多10中文/20英文）"
                maxlength="20"
                @input="limitTaskNameInput"
              >
            </div>
            <div class="form-group">
              <label>扫描方式</label>
              <CustomSelect
                v-model="form.scan_mode"
                :options="scanModeOptions"
                placeholder="请选择扫描方式"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>选择账号</label>
              <CustomSelect
                v-model="form.account_id"
                :options="accountOptions"
                placeholder="请选择账号"
                @change="onAccountChange"
              />
            </div>
            <div class="form-group">
              <label>选择目录</label>
              <div class="input-group integrated">
                <input v-model="form.path" type="text" class="form-input" placeholder="请选择目录" readonly>
                <button type="button" class="btn btn-primary browse-btn" @click="browseDirectory">浏览</button>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>API额外补偿间隔(毫秒)</label>
              <input
                v-model.number="form.api_interval"
                type="number"
                class="form-input"
                min="0"
                max="5000"
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

          <div class="advanced-toggle" @click="showAdvanced = !showAdvanced">
            {{ showAdvanced ? '收起选项' : '更多选项' }}
            <svg class="advanced-toggle-icon" :class="{ rotated: showAdvanced }" viewBox="0 0 16 16" fill="none">
              <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>

          <div v-if="showAdvanced">
          <div class="form-row">
            <div class="form-group">
              <label>排除目录关键词</label>
              <input v-model="form.exclude_dir_keywords" type="text" class="form-input" placeholder="例如：sample;预告;花絮">
            </div>
            <div class="form-group">
              <label>排除文件关键词</label>
              <input v-model="form.exclude_file_keywords" type="text" class="form-input" placeholder="例如：sample;trailer;预告">
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>同步元数据</label>
              <CustomSelect
                v-model="form.sync_metadata"
                :options="metadataSyncOptions"
                placeholder="请选择是否同步元数据"
              />
            </div>
            <div class="form-group">
              <label>分支检查</label>
              <div class="branch-check-control" :class="{ enabled: form.branch_check_enabled }">
                <button
                  type="button"
                  class="branch-check-toggle"
                  @click="form.branch_check_enabled = !form.branch_check_enabled"
                >
                  <span class="branch-check-dot"></span>
                  <span class="branch-check-text">{{ form.branch_check_enabled ? '开启' : '关闭' }}</span>
                </button>
                <button
                  type="button"
                  class="branch-check-edit"
                  title="编辑分支"
                  :disabled="!editingId"
                  @click="openBranchDialogForEditing"
                >
                  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M3 4h10" />
                    <path d="M3 8h10" />
                    <path d="M3 12h6" />
                    <path d="M11.5 10.5v3" />
                    <path d="M10 12h3" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          </div>
        </div>

        <div class="dialog-footer">
          <button @click="saveTask" class="btn btn-primary" :disabled="saving">
            <i class="fas fa-save"></i> {{ editingId ? '更新任务' : '保存任务' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="branchDialogVisible" class="dialog-overlay">
      <div class="dialog branch-dialog" @click="handleBranchModalClick">
        <div class="dialog-header">
          <h3>分支编辑</h3>
          <button @click="closeBranchDialog" class="close-btn">&times;</button>
        </div>

        <div class="dialog-content add-config-form branch-dialog-content">
          <div class="branch-add-bar">
            <div class="branch-kind-toggle" role="group" aria-label="分支类型">
              <button type="button" :class="{ active: branchForm.branch_type === 'base' }" @click="setBranchType('base')">入口分支</button>
              <button type="button" :class="{ active: branchForm.branch_type === 'temporary' }" @click="setBranchType('temporary')">监控分支</button>
            </div>
            <div class="branch-path-field input-group integrated">
              <input v-model="branchForm.path" type="text" class="form-input" placeholder="请选择任务目录下的分支" readonly>
              <button type="button" class="btn btn-primary browse-btn" @click="browseBranchDirectory">浏览</button>
            </div>
            <select v-if="branchForm.branch_type === 'temporary'" v-model.number="branchForm.retention_days" class="form-input branch-retention">
              <option v-for="option in temporaryRetentionOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <button type="button" class="btn btn-primary" @click="addBranch">新增</button>
          </div>

          <div v-if="branchLoading" class="empty-state">
            <p class="empty-title">正在加载分支...</p>
          </div>
          <div v-else class="branch-columns">
            <section class="branch-column">
              <div class="branch-column-head">
                <span>入口分支</span>
                <em>{{ baseBranches.length }}</em>
              </div>
              <div v-if="!baseBranches.length" class="branch-empty">暂无入口分支</div>
              <div v-else class="branch-list">
                <div v-for="branch in baseBranches" :key="branch.id" class="branch-row compact">
                  <div class="branch-path" :title="branch.path">{{ branch.path }}</div>
                  <button type="button" class="task-action-btn danger" title="删除分支" @click="deleteBranch(branch)">
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M3 4h10" />
                      <path d="M6 4V3.2c0-.7.5-1.2 1.2-1.2h1.6c.7 0 1.2.5 1.2 1.2V4" />
                      <path d="M5 6v7c0 .6.4 1 1 1h4c.6 0 1-.4 1-1V6" />
                    </svg>
                  </button>
                </div>
              </div>
            </section>

            <section class="branch-column">
              <div class="branch-column-head">
                <span>监控分支</span>
                <span class="branch-expiry-summary" :class="{ preview: hoveredTemporaryBranch }">
                  <template v-if="hoveredTemporaryBranch">
                    自动移除 {{ getTemporaryBranchRemovalLabel(hoveredTemporaryBranch) }}
                  </template>
                  <template v-else>
                    共 {{ temporaryBranches.length }} 条
                  </template>
                </span>
              </div>
              <div v-if="!temporaryBranches.length" class="branch-empty">暂无监控分支</div>
              <div v-else class="branch-list">
                <div v-for="branch in temporaryBranches" :key="branch.id" class="branch-row compact">
                  <div class="branch-path" :title="branch.path">{{ branch.path }}</div>
                  <select
                    v-model.number="branch.retention_days"
                    class="form-input branch-retention"
                    @mouseenter="setHoveredTemporaryBranch(branch)"
                    @mouseleave="clearHoveredTemporaryBranch(branch)"
                    @focus="setHoveredTemporaryBranch(branch)"
                    @blur="onTemporaryBranchRetentionBlur(branch)"
                    @change="updateBranch(branch)"
                  >
                    <option v-for="option in temporaryRetentionOptions" :key="option.value" :value="option.value">
                      {{ option.label }}
                    </option>
                  </select>
                  <button type="button" class="task-action-btn danger" title="删除分支" @click="deleteBranch(branch)">
                    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M3 4h10" />
                      <path d="M6 4V3.2c0-.7.5-1.2 1.2-1.2h1.6c.7 0 1.2.5 1.2 1.2V4" />
                      <path d="M5 6v7c0 .6.4 1 1 1h4c.6 0 1-.4 1-1V6" />
                    </svg>
                  </button>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>

    <!-- 时间滚轮选择器 -->
    <TimeWheelPicker
      :visible="timePickerVisible"
      :startTime="form.time_start"
      :endTime="form.time_end"
      :allDay="form.time_window_mode === 'always'"
      @confirm="onTimeWheelConfirm"
      @cancel="closeTimePicker"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, reactive, watch } from 'vue'
import axios from 'axios'
import { useAdminStore } from '../../stores/admin'
import { storeToRefs } from 'pinia'
import { useModal } from '../../composables/useModal'
import { useFolderSelector } from '../../composables/useFolderSelector'
import CustomSelect from '../CustomSelect.vue'
import TimeWheelPicker from '../TimeWheelPicker.vue'

const activeTab = ref('tasks')
const settingsMenuOpen = ref(false)
const tasks = ref([])
const embyProxies = ref([])
const startupRemaining = ref(0)
const saving = ref(false)
const showDialog = ref(false)
const embyShowDialog = ref(false)
const showAdvanced = ref(false)
const editingId = ref(null)
const embyEditingId = ref(null)
const strmBaseUrlTooltipVisible = ref(false)
const strmIntervalTooltipVisible = ref(false)
const strmTaskConcurrencyTooltipVisible = ref(false)
const strmSignatureTooltipVisible = ref(false)
const strmMinSizeTooltipVisible = ref(false)
const strmDefaultExtensionsTooltipVisible = ref(false)
const strmMetadataExtTooltipVisible = ref(false)
const strmMetadataSizeTooltipVisible = ref(false)
const strmMetadataParentTooltipVisible = ref(false)
const strmConflictTooltipVisible = ref(false)
const strmIsoModeTooltipVisible = ref(false)
const strmTokenTooltipVisible = ref(false)
const strmDomainTooltipVisible = ref(false)
const organizeAlignTooltipVisible = ref(false)
const conflictPolicyTooltipVisible = ref(false)

const organizeConflictPolicyOptions = [
  { value: 'skip', label: '跳过（推荐）' },
  { value: 'overwrite', label: '覆盖' },
]

const organizeConflictPolicy = computed({
  get() {
    return organizeSettings.overwrite_existing ? 'overwrite' : 'skip'
  },
  set(val) {
    organizeSettings.overwrite_existing = val === 'overwrite'
  },
})
const organizeMaxWorksTooltipVisible = ref(false)
const branchDialogVisible = ref(false)
const branchLoading = ref(false)
const branchTask = ref(null)
const branches = ref([])
const hoveredTemporaryBranchId = ref(null)

// ── 目录整理状态 ──

const organizeTasks = ref([])
const organizeShowDialog = ref(false)
const organizeEditingId = ref(null)
const organizeSaving = ref(false)
const organizeLogTaskId = ref(null)
const organizeLogTaskName = ref('')
const organizeLogs = ref([])
const organizeLogBodyRef = ref(null)
let organizeLogPollTimer = null
let organizeTaskListPollTimer = null
const ORGANIZE_LOG_TASK_STORAGE_KEY = 'litepan_organize_log_task_id'

const organizePlanDialogVisible = ref(false)
const organizePlanTaskId = ref(null)
const organizePlanTaskName = ref('')
const organizePlanLoading = ref(false)
const organizePlanApplying = ref(false)
const organizePlanRelocates = ref([])
const organizePlanEnsures = ref([])
const organizePlanSkipped = ref([])
const organizePlanTmdbStatus = ref('')
const tmdbTesting = ref(false)
const organizePlanSkipExpanded = ref(false)

const testTmdbConnectivity = async () => {
  if (tmdbTesting.value) return
  tmdbTesting.value = true
  try {
    const payload = {
      tmdb_api_key: organizeSettings.tmdb_api_key || '',
      tmdb_language: organizeSettings.tmdb_language || 'zh-CN',
      proxy_enabled: !!organizeSettings.proxy_enabled,
      proxy_url: organizeSettings.proxy_url || '',
      proxy_username: organizeSettings.proxy_username || '',
      proxy_password: organizeSettings.proxy_password || '',
    }
    const resp = await axios.post('/api/admin/media-organize/test-tmdb', payload)
    if (resp.data?.success) {
      const lang = resp.data.data?.language || ''
      const proxyUsed = resp.data.data?.proxy_used
      const tail = proxyUsed ? '（已使用代理）' : ''
      window.appNotification?.success?.(`TMDB 连通正常，语言: ${lang}${tail}`)
    } else {
      window.appNotification?.error?.(resp.data?.message || 'TMDB 连通测试失败')
    }
  } catch (e) {
    window.appNotification?.error?.('TMDB 连通测试异常: ' + (e.response?.data?.message || e.message))
  } finally {
    tmdbTesting.value = false
  }
}
const organizePlanSkipExpandedReasons = ref({})
const organizePlanSkipShowAll = ref({})
const ORGANIZE_PLAN_SKIP_PREVIEW_LIMIT = 200

const organizePlanSkipGroups = computed(() => {
  const map = new Map()
  for (const item of organizePlanSkipped.value || []) {
    const reason = (item && item.reason) || '其它'
    if (!map.has(reason)) map.set(reason, { reason, items: [] })
    map.get(reason).items.push(item)
  }
  return Array.from(map.values()).sort((a, b) => b.items.length - a.items.length)
})

const toggleOrganizePlanSkipReason = (reason) => {
  organizePlanSkipExpandedReasons.value = {
    ...organizePlanSkipExpandedReasons.value,
    [reason]: !organizePlanSkipExpandedReasons.value[reason],
  }
}

const showOrganizePlanSkipAll = (reason) => {
  organizePlanSkipShowAll.value = { ...organizePlanSkipShowAll.value, [reason]: true }
}
const organizePlanProgress = ref({})
const organizePlanGroupExpanded = ref({})
const organizePlanExpandedRanges = ref({})
const organizePlanEditingId = ref(null)
const organizePlanEditingName = ref('')
const organizePlanEditingSaving = ref(false)
let organizePlanProgressTimer = null
const boolOptions = [
  { value: 'true', label: '开启' },
  { value: 'false', label: '关闭' },
]
const organizeForm = reactive({
  task_name: '',
  account_id: null,
  target_directory: '',
  target_directory_id: '',
  action_type: 'move',
  target_root: '',
  target_root_id: '',
  media_type: 'auto',
  rename_marker: '',
  use_ffprobe: 'false',
  use_tmdb: 'true',
  recursive: true,
})
const organizeSettings = reactive({
  api_request_interval_ms: 300,
  ffprobe_request_interval_ms: 3000,
  tmdb_request_interval_ms: 250,
  proxy_enabled: false,
  proxy_url: '',
  proxy_username: '',
  proxy_password: '',
  tmdb_api_key: '',
  max_works_per_run: 50,
  tmdb_language: 'zh-CN',
  file_extensions: 'mkv;mp4;avi;ts;mov;wmv;iso;m2ts;rmvb;flv;m4v;webm',
  metadata_extensions: 'nfo;ass;ssa;srt;sub;idx;sup;vtt',
  media_tag_order: '["screen_size","frame_rate","video_codec","audio_codec","audio_channels"]',
  align_media_tags: false,
  overwrite_existing: false,
})

const ALL_TAG_KEYS = ['screen_size', 'frame_rate', 'video_codec', 'audio_codec', 'audio_channels']
const TAG_LABELS = {
  screen_size: '分辨率',
  frame_rate: '帧率',
  video_codec: '视频编码',
  audio_codec: '音频编码',
  audio_channels: '声道数',
}

const tagOrder = reactive([])
const disabledTags = computed(() => ALL_TAG_KEYS.filter(k => !tagOrder.includes(k)))

const syncTagsFromSettings = () => {
  try {
    const order = JSON.parse(organizeSettings.media_tag_order || '[]')
    tagOrder.splice(0, tagOrder.length, ...order.filter(k => ALL_TAG_KEYS.includes(k)))
    for (const k of ALL_TAG_KEYS) {
      if (!tagOrder.includes(k)) tagOrder.push(k)
    }
  } catch {
    tagOrder.splice(0, tagOrder.length, ...ALL_TAG_KEYS)
  }
  organizeSettings.media_tag_order = JSON.stringify([...tagOrder])
}

const onTagOrderChange = () => {
  organizeSettings.media_tag_order = JSON.stringify([...tagOrder])
}

const removeTag = (key) => {
  const idx = tagOrder.indexOf(key)
  if (idx >= 0) tagOrder.splice(idx, 1)
  onTagOrderChange()
}

const addTag = (key) => {
  if (!tagOrder.includes(key)) tagOrder.push(key)
  onTagOrderChange()
}

let dragSrcIndex = null
const dragOverIndex = ref(null)
const onTagDragStart = (e, index) => {
  dragSrcIndex = index
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(index))
}
const onTagDragOver = (e, index) => {
  e.dataTransfer.dropEffect = 'move'
  dragOverIndex.value = index
}
const onTagDrop = (e, index) => {
  if (dragSrcIndex === null || dragSrcIndex === index) return
  const item = tagOrder.splice(dragSrcIndex, 1)[0]
  tagOrder.splice(index, 0, item)
  dragSrcIndex = null
  onTagOrderChange()
}
const onTagDragEnd = () => {
  dragSrcIndex = null
  dragOverIndex.value = null
}

const { confirm } = useModal()
const { selectFolder } = useFolderSelector()

const timePickerVisible = ref(false)

function onTimeWheelConfirm({ startTime, endTime, allDay }) {
  if (allDay) {
    form.time_window_mode = 'always'
  } else {
    form.time_window_mode = 'custom'
    form.time_start = startTime
    form.time_end = endTime
  }
  timePickerVisible.value = false
}

function closeTimePicker() {
  timePickerVisible.value = false
}

let tasksPollTimer = null
let tasksLoading = false

const adminStore = useAdminStore()
const { accounts } = storeToRefs(adminStore)

const replaceDomain = ref('')

const defaultExtensions = 'mp4;mkv;avi;mov;wmv;flv;ts;m2ts;mpg;mpeg;webm;m4v;iso;rmvb;mp3;flac;aac;wav;m4a'
const settingsTabs = ['settings', 'organizeSettings']
const isSettingsTab = computed(() => settingsTabs.includes(activeTab.value))

const strmSettings = reactive({
  strm_base_url: '',
  strm_token: '',
  strm_default_scan_interval: 120,
  strm_task_concurrency: 3,
  strm_signature_enabled: false,
  strm_default_extensions: defaultExtensions,
  strm_min_file_size_mb: 0,
  strm_metadata_extensions: 'srt;ass;ssa;sub;nfo;jpg;jpeg;png;webp',
  strm_metadata_max_size_mb: 10,
  strm_metadata_parent_enabled: true,
  strm_conflict_policy: 'size_desc',
  strm_iso_play_mode: 'follow'
})

const form = reactive({
  name: '',
  account_id: null,
  parent_id: '',
  path: '',
  scan_mode: 'incremental_update',
  api_interval: 200,
  exclude_dir_keywords: '',
  exclude_file_keywords: '',
  sync_metadata: 'false',
  branch_check_enabled: false,
  time_window_mode: 'always',
  time_start: '00:00',
  time_end: '00:00'
})

const taskNameWidthLimit = 20

const textDisplayWidth = (value) => {
  let total = 0
  for (const ch of String(value || '')) {
    total += ch.charCodeAt(0) > 127 ? 2 : 1
  }
  return total
}

const truncateByDisplayWidth = (value, maxWidth) => {
  let total = 0
  let output = ''
  for (const ch of String(value || '')) {
    const width = ch.charCodeAt(0) > 127 ? 2 : 1
    if (total + width > maxWidth) break
    total += width
    output += ch
  }
  return output
}

const limitTaskNameInput = () => {
  if (textDisplayWidth(form.name) > taskNameWidthLimit) {
    form.name = truncateByDisplayWidth(form.name, taskNameWidthLimit)
  }
}

const branchForm = reactive({
  parent_id: '',
  path: '',
  branch_type: 'base',
  recursive: true,
  retention_days: 30
})

const embyForm = reactive({
  name: '',
  emby_url: '',
  api_key: '',
  proxy_port: ''
})

const accountOptions = computed(() => {
  return (accounts.value || []).map(a => ({ value: a.id, label: a.name }))
})

const scanModeOptions = [
  { value: 'incremental_missing', label: '补缺' },
  { value: 'incremental_update', label: '更新' },
  { value: 'full_sync', label: '全量' }
]

const metadataSyncOptions = [
  { value: 'false', label: '关闭' },
  { value: 'true', label: '开启' }
]

const conflictPolicyOptions = [
  { value: 'size_desc', label: '大文件优先' },
  { value: 'size_asc', label: '小文件优先' },
  { value: 'name_asc', label: '文件名靠前优先' }
]

const strmIsoPlayModeOptions = [
  { value: 'follow', label: '跟随网盘模式' },
  { value: 'proxy', label: '强制代理模式' }
]

const tmdbLanguageOptions = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'zh-TW', label: '繁体中文' },
  { value: 'en-US', label: 'English' }
]

const normalizeConflictPolicy = (value) => {
  if (value === 'quality_then_size') return 'size_desc'
  return ['size_desc', 'size_asc', 'name_asc'].includes(value) ? value : 'size_desc'
}

const temporaryRetentionOptions = [
  { value: 10, label: '10天' },
  { value: 30, label: '30天' },
  { value: 90, label: '90天' },
  { value: 365, label: '1年' },
  { value: 0, label: '永久' },
]

const baseBranches = computed(() => branches.value.filter(branch => (branch.branch_type || 'temporary') === 'base'))
const temporaryBranches = computed(() => branches.value.filter(branch => (branch.branch_type || 'temporary') !== 'base'))
/** 悬停在某个监控分支的时长控件上时，表头右侧显示该分支预计移除时间 */
const hoveredTemporaryBranch = computed(() => {
  if (!hoveredTemporaryBranchId.value) return null
  return temporaryBranches.value.find(branch => Number(branch.id) === Number(hoveredTemporaryBranchId.value)) || null
})

/** 与后端一致：自创建时间起 retention_days 天后移除 */
const getTemporaryBranchRemovalLabel = (branch) => {
  if (!branch) return ''
  const days = Number(branch.retention_days ?? 30)
  if (days <= 0) return '永久保留'
  const createdRaw = branch.created_at
  if (createdRaw) {
    const base = new Date(createdRaw)
    if (Number.isFinite(base.getTime())) {
      const dt = new Date(base.getTime() + days * 86400000)
      return formatLast(dt.toISOString())
    }
  }
  if (branch.expires_at) {
    const d = new Date(branch.expires_at)
    if (Number.isFinite(d.getTime())) {
      return formatLast(d.toISOString())
    }
  }
  return '—'
}

const onTemporaryBranchRetentionBlur = (branch) => {
  if (Number(hoveredTemporaryBranchId.value) === Number(branch?.id)) {
    hoveredTemporaryBranchId.value = null
  }
}

const setHoveredTemporaryBranch = (branch) => {
  hoveredTemporaryBranchId.value = branch?.id || null
}

const clearHoveredTemporaryBranch = (branch) => {
  if (Number(hoveredTemporaryBranchId.value) === Number(branch?.id)) {
    hoveredTemporaryBranchId.value = null
  }
}

const timeWindowDisplay = computed(() => {
  if (form.time_window_mode === 'always') return '全天'
  const [sh, sm] = form.time_start.split(':').map(Number)
  const [eh, em] = form.time_end.split(':').map(Number)
  const sMin = sh * 60 + sm
  const eMin = eh * 60 + em
  if (sMin < eMin) return `${form.time_start}-${form.time_end}`
  if (sMin === eMin) return '全天'
  return `${form.time_start}-次日${form.time_end}`
})

const enabledCount = computed(() => tasks.value.filter(t => t.status === 'running').length)
const pausedCount = computed(() => tasks.value.filter(t => t.status !== 'running').length)
const queuedCount = computed(() => tasks.value.filter(t => Boolean(t?.is_queued)).length)
const embyRunningCount = computed(() => embyProxies.value.filter(p => p.status === 'running').length)
const embyPausedCount = computed(() => embyProxies.value.filter(p => p.status !== 'running').length)

const getModeText = (mode) => {
  if (mode === 'incremental_missing') return '补缺'
  if (mode === 'incremental_update') return '更新'
  if (mode === 'full_sync') return '全量'
  return '未知'
}

const formatLast = (value) => {
  if (!value) return '未执行'
  return value.replace('T', ' ').replace('Z', '').slice(0, 19)
}

const formatDuration = (durationMs) => {
  const value = Number(durationMs || 0)
  if (!value) return ''
  if (value < 1000) return `${value}毫秒`
  const seconds = value / 1000
  if (seconds < 60) return `${seconds.toFixed(seconds >= 10 ? 0 : 1)}秒`
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = Math.round(seconds % 60)
  return `${minutes}分${remainSeconds}秒`
}

const getDisplayTaskName = (name) => {
  const chars = Array.from(String(name || ''))
  if (chars.length <= 7) return String(name || '')
  return `${chars.slice(0, 7).join('')}...`
}

const isTaskScanning = (task) => Boolean(task?.is_scanning)
const isTaskQueued = (task) => Boolean(task?.is_queued) && !isTaskScanning(task)

const getScanStatusClass = (task) => {
  if (isTaskScanning(task)) return 'scanning'
  if (isTaskQueued(task)) return 'queued'
  return task?.last_scan_status || 'pending'
}

const getLastScanPrimaryText = (task) => {
  if (isTaskScanning(task)) {
    const elapsedText = getElapsedText(task)
    let text = '正在扫描'
    if (task.scanned_dirs > 0 || task.scanned_files > 0) {
      text += ` — 已扫 ${task.scanned_dirs} 目录 / ${task.scanned_files} 文件`
    }
    if (elapsedText) text += `，${elapsedText}`
    return text
  }
  if (isTaskQueued(task)) return '排队中'
  return formatLast(task?.last_scan)
}

const getLastScanSummary = (task) => {
  if (isTaskScanning(task)) return '扫描中...'
  if (isTaskQueued(task)) return '等待执行...'
  if (!task?.last_scan) return ''
  const created = Number(task.last_created_count || 0)
  const updated = Number(task.last_updated_count || 0)
  const deleted = Number(task.last_deleted_count || 0)
  const durationText = formatDuration(task.last_duration_ms)
  const parts = []
  if (created > 0) parts.push(`新增 ${created}`)
  if (updated > 0) parts.push(`改写 ${updated}`)
  if (deleted > 0) parts.push(`删除 ${deleted}`)
  if (parts.length === 0) parts.push('无变更')
  if (durationText) parts.push(durationText)
  return parts.join(' · ')
}

const getElapsedText = (task) => {
  const currentDurationMs = Number(task?.current_duration_ms || 0)
  if (currentDurationMs > 0) {
    const elapsed = Math.max(1, Math.floor(currentDurationMs / 1000))
    if (elapsed < 60) return `耗时 ${elapsed}s`
    const min = Math.floor(elapsed / 60)
    const sec = elapsed % 60
    return `耗时 ${min}m${sec}s`
  }
  if (!task?.started_at) return ''
  const started = new Date(task.started_at)
  const now = new Date()
  const elapsedRaw = Math.floor((now - started) / 1000)
  const elapsed = Math.max(1, Number.isFinite(elapsedRaw) ? elapsedRaw : 0)
  if (elapsed < 60) return `耗时 ${elapsed}s`
  const min = Math.floor(elapsed / 60)
  const sec = elapsed % 60
  return `耗时 ${min}m${sec}s`
}

const getTaskTitle = (task) => {
  const parts = [task?.name || '']
  if (task?.account_name) parts.push(`账号：${task.account_name}`)
  if (task?.scan_mode) parts.push(`扫描方式：${getModeText(task.scan_mode)}`)
  return parts.filter(Boolean).join('\n')
}

const getLastScanTitle = (task) => {
  const parts = [getLastScanPrimaryText(task)]
  const summary = getLastScanSummary(task)
  if (summary) parts.push(summary)
  const scanned = Number(task?.file_count || 0)
  if (task?.last_scan) {
    parts.push(`扫描 ${scanned} 个文件`)
  }
  if (task?.error_message) {
    parts.push(task.error_message)
  }
  return parts.filter(Boolean).join('\n')
}

const loadTasks = async () => {
  if (tasksLoading) return
  tasksLoading = true
  try {
    const response = await axios.get('/api/admin/strm/tasks')
    if (response.data.success) {
      tasks.value = response.data.data || []
      startupRemaining.value = response.data.startup_remaining || 0
    }
  } finally {
    tasksLoading = false
  }
}

const loadEmbyProxies = async () => {
  const response = await axios.get('/api/admin/strm/emby-proxies')
  if (response.data.success) {
    embyProxies.value = response.data.data || []
  }
}

const startTasksPolling = () => {
  if (tasksPollTimer) return
  tasksPollTimer = window.setInterval(() => {
    if (activeTab.value === 'tasks') {
      loadTasks()
    }
  }, 3000)
}

const stopTasksPolling = () => {
  if (tasksPollTimer) {
    window.clearInterval(tasksPollTimer)
    tasksPollTimer = null
  }
}

const loadStrmSettings = async () => {
  const response = await axios.get('/api/admin/strm/settings')
  if (response.data.success) {
    strmSettings.strm_base_url = response.data.data.strm_base_url || ''
    strmSettings.strm_token = response.data.data.strm_token || ''
    strmSettings.strm_default_scan_interval = Number(response.data.data.strm_default_scan_interval) || 120
    strmSettings.strm_task_concurrency = Number(response.data.data.strm_task_concurrency) || 3
    strmSettings.strm_signature_enabled = Boolean(response.data.data.strm_signature_enabled)
    strmSettings.strm_default_extensions = response.data.data.strm_default_extensions || defaultExtensions
    strmSettings.strm_min_file_size_mb = Number(response.data.data.strm_min_file_size_mb) || 0
    strmSettings.strm_metadata_extensions = response.data.data.strm_metadata_extensions || ''
    strmSettings.strm_metadata_max_size_mb = Number(response.data.data.strm_metadata_max_size_mb) || 10
    strmSettings.strm_metadata_parent_enabled = response.data.data.strm_metadata_parent_enabled !== false
    strmSettings.strm_conflict_policy = normalizeConflictPolicy(response.data.data.strm_conflict_policy)
    strmSettings.strm_iso_play_mode = response.data.data.strm_iso_play_mode || 'follow'
    if (!replaceDomain.value) {
      replaceDomain.value = strmSettings.strm_base_url || ''
    }
  }
}

const saveStrmSettings = async () => {
  const response = await axios.post('/api/admin/strm/settings', {
    strm_base_url: strmSettings.strm_base_url,
    strm_default_scan_interval: strmSettings.strm_default_scan_interval,
    strm_task_concurrency: strmSettings.strm_task_concurrency,
    strm_signature_enabled: strmSettings.strm_signature_enabled,
    strm_default_extensions: strmSettings.strm_default_extensions,
    strm_min_file_size_mb: strmSettings.strm_min_file_size_mb,
    strm_metadata_extensions: strmSettings.strm_metadata_extensions,
    strm_metadata_max_size_mb: strmSettings.strm_metadata_max_size_mb,
    strm_metadata_parent_enabled: strmSettings.strm_metadata_parent_enabled,
    strm_conflict_policy: strmSettings.strm_conflict_policy,
    strm_iso_play_mode: strmSettings.strm_iso_play_mode
  })
  if (response.data.success) {
    strmSettings.strm_base_url = response.data.data.strm_base_url || ''
    strmSettings.strm_token = response.data.data.strm_token || ''
    strmSettings.strm_default_scan_interval = Number(response.data.data.strm_default_scan_interval) || 120
    strmSettings.strm_task_concurrency = Number(response.data.data.strm_task_concurrency) || 3
    strmSettings.strm_signature_enabled = Boolean(response.data.data.strm_signature_enabled)
    strmSettings.strm_default_extensions = response.data.data.strm_default_extensions || defaultExtensions
    strmSettings.strm_min_file_size_mb = Number(response.data.data.strm_min_file_size_mb) || 0
    strmSettings.strm_metadata_extensions = response.data.data.strm_metadata_extensions || ''
    strmSettings.strm_metadata_max_size_mb = Number(response.data.data.strm_metadata_max_size_mb) || 10
    strmSettings.strm_metadata_parent_enabled = response.data.data.strm_metadata_parent_enabled !== false
    strmSettings.strm_conflict_policy = normalizeConflictPolicy(response.data.data.strm_conflict_policy)
    strmSettings.strm_iso_play_mode = response.data.data.strm_iso_play_mode || 'follow'
    if (replaceDomain.value) {
      replaceDomain.value = strmSettings.strm_base_url || replaceDomain.value
    }
    window.appNotification.success('STRM设置保存成功')
  } else {
    window.appNotification.error(response.data.message || '保存失败')
  }
}

const regenerateStrmToken = async (applyTokenToExistingStrm = false) => {
  const response = await axios.post('/api/admin/strm/settings', {
    regenerate_token: true,
    apply_token_to_existing_strm: applyTokenToExistingStrm
  })
  if (response.data.success) {
    strmSettings.strm_base_url = response.data.data.strm_base_url || ''
    strmSettings.strm_token = response.data.data.strm_token || ''
    strmSettings.strm_default_scan_interval = Number(response.data.data.strm_default_scan_interval) || 120
    strmSettings.strm_task_concurrency = Number(response.data.data.strm_task_concurrency) || 3
    strmSettings.strm_signature_enabled = Boolean(response.data.data.strm_signature_enabled)
    strmSettings.strm_default_extensions = response.data.data.strm_default_extensions || defaultExtensions
    strmSettings.strm_min_file_size_mb = Number(response.data.data.strm_min_file_size_mb) || 0
    strmSettings.strm_metadata_extensions = response.data.data.strm_metadata_extensions || ''
    strmSettings.strm_metadata_max_size_mb = Number(response.data.data.strm_metadata_max_size_mb) || 10
    strmSettings.strm_metadata_parent_enabled = response.data.data.strm_metadata_parent_enabled !== false
    strmSettings.strm_conflict_policy = normalizeConflictPolicy(response.data.data.strm_conflict_policy)
    strmSettings.strm_iso_play_mode = response.data.data.strm_iso_play_mode || 'follow'
    const replaceResult = response.data.data.strm_token_replace_result
    if (replaceResult) {
      window.appNotification.success(`STRM令牌已重新生成，已替换 ${replaceResult.updated}/${replaceResult.total} 个文件`)
    } else {
      window.appNotification.success('STRM令牌已重新生成')
    }
  } else {
    window.appNotification.error(response.data.message || '重新生成失败')
  }
}

const changeStrmToken = async () => {
  try {
    const result = await confirm({
      title: '确认更换令牌',
      content: '重新生成后旧 .strm 中的令牌会失效，可同时将已生成文件中的旧令牌替换为新令牌。',
      confirmText: '更换令牌',
      confirmClass: 'btn-danger',
      icon: 'key',
      checkboxLabel: '将新令牌应用到已有strm中',
      checkboxChecked: true
    })
    await regenerateStrmToken(result?.checked !== false)
  } catch (error) {
    if (error.message !== 'Modal closed') {
      window.appNotification.error('更换令牌失败: ' + error.message)
    }
  }
}

const openAddDialog = () => {
  editingId.value = null
  showAdvanced.value = false
  Object.assign(form, {
    name: '',
    account_id: null,
    parent_id: '',
    path: '',
    scan_mode: 'incremental_update',
    api_interval: 200,
    exclude_dir_keywords: '',
    exclude_file_keywords: '',
    sync_metadata: 'false',
    branch_check_enabled: false,
    time_window_mode: 'always',
    time_start: '00:00',
    time_end: '00:00'
  })
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const openEmbyDialog = () => {
  embyEditingId.value = null
  Object.assign(embyForm, {
    name: '',
    emby_url: '',
    api_key: '',
    proxy_port: ''
  })
  embyShowDialog.value = true
}

const closeEmbyDialog = () => {
  embyShowDialog.value = false
}

const handleDialogKeydown = (event) => {
  if (event.key !== 'Escape' || (!showDialog.value && !embyShowDialog.value && !branchDialogVisible.value)) return
  const activeModal = document.querySelector('.modern-modal-overlay')
  if (!activeModal) {
    event.preventDefault()
    event.stopPropagation()
    event.stopImmediatePropagation?.()
    if (branchDialogVisible.value) {
      closeBranchDialog()
    } else if (embyShowDialog.value) {
      closeEmbyDialog()
    } else if (showDialog.value) {
      closeDialog()
    }
    if (document.activeElement) {
      document.activeElement.blur()
    }
  }
}

const handleModalClick = (event) => {
  if (event.target.classList.contains('dialog-overlay')) {
    closeDialog()
  }
}

const handleEmbyModalClick = (event) => {
  if (event.target.classList.contains('dialog-overlay')) {
    closeEmbyDialog()
  }
}

const handleBranchModalClick = (event) => {
  if (event.target.classList.contains('dialog-overlay')) {
    closeBranchDialog()
  }
}

const onAccountChange = () => {
  form.parent_id = ''
  form.path = ''
}

const browseDirectory = async () => {
  if (!form.account_id) {
    window.appNotification.warning('请先选择账号')
    return
  }
  const result = await selectFolder(form.account_id, {
    initialPath: form.path
  })
  if (result) {
    form.path = result.path
    form.parent_id = result.id
  }
}

const resetBranchForm = () => {
  Object.assign(branchForm, {
    parent_id: '',
    path: '',
    branch_type: 'base',
    recursive: true,
    retention_days: 30
  })
}

const setBranchType = (type) => {
  branchForm.branch_type = type
  if (type === 'base') {
    branchForm.recursive = false
    branchForm.retention_days = 30
  } else {
    branchForm.recursive = true
    branchForm.retention_days = branchForm.retention_days ?? 30
  }
}

const loadBranches = async () => {
  if (!branchTask.value?.id) return
  branchLoading.value = true
  try {
    const resp = await axios.get(`/api/admin/strm/tasks/${branchTask.value.id}/branches`)
    if (resp.data.success) {
      branches.value = resp.data.data || []
    } else {
      window.appNotification.error(resp.data.message || '加载分支失败')
    }
  } finally {
    branchLoading.value = false
  }
}

const openBranchDialog = async (task) => {
  branchTask.value = task
  resetBranchForm()
  branchDialogVisible.value = true
  await loadBranches()
}

const openBranchDialogForEditing = async () => {
  if (!editingId.value) {
    window.appNotification.info('保存任务后再编辑分支')
    return
  }
  const task = tasks.value.find(t => Number(t.id) === Number(editingId.value)) || {
    id: editingId.value,
    account_id: form.account_id,
    path: form.path
  }
  await openBranchDialog(task)
}

const closeBranchDialog = () => {
  branchDialogVisible.value = false
  branchTask.value = null
  branches.value = []
  hoveredTemporaryBranchId.value = null
  resetBranchForm()
  loadTasks()
}

const browseBranchDirectory = async () => {
  if (!branchTask.value?.account_id) {
    window.appNotification.warning('任务账号不存在')
    return
  }
  const result = await selectFolder(branchTask.value.account_id, {
    rootId: branchTask.value.parent_id,
    title: '选择分支目录',
    confirmText: '选择该分支'
  })
  if (result) {
    const basePath = String(branchTask.value.path || '').replace(/\/+$/, '') || '/'
    const pickedPath = String(result.path || '/').replace(/^\/+/, '')
    branchForm.path = pickedPath ? `${basePath}/${pickedPath}` : basePath
    branchForm.parent_id = result.id
  }
}

const addBranch = async () => {
  if (!branchTask.value?.id) return
  if (!branchForm.parent_id || !branchForm.path) {
    window.appNotification.warning('请选择分支目录')
    return
  }
  const resp = await axios.post(`/api/admin/strm/tasks/${branchTask.value.id}/branches`, {
    parent_id: branchForm.parent_id,
    path: branchForm.path,
    branch_type: branchForm.branch_type,
    recursive: branchForm.branch_type === 'temporary' ? Boolean(branchForm.recursive) : false,
    retention_days: branchForm.branch_type === 'temporary' ? Number(branchForm.retention_days ?? 30) : 0
  })
  if (resp.data.success) {
    window.appNotification.success('分支添加成功')
    resetBranchForm()
    await loadBranches()
    await loadTasks()
  } else {
    window.appNotification.error(resp.data.message || '分支添加失败')
  }
}

const updateBranch = async (branch) => {
  if (!branchTask.value?.id) return
  const resp = await axios.put(`/api/admin/strm/tasks/${branchTask.value.id}/branches/${branch.id}`, {
    branch_type: branch.branch_type || 'temporary',
    recursive: (branch.branch_type || 'temporary') === 'temporary' ? Boolean(branch.recursive) : false,
    retention_days: (branch.branch_type || 'temporary') === 'temporary' ? Number(branch.retention_days ?? 30) : 0
  })
  if (!resp.data.success) {
    window.appNotification.error(resp.data.message || '分支更新失败')
    await loadBranches()
  } else {
    await loadBranches()
  }
}

const deleteBranch = async (branch) => {
  if (!branchTask.value?.id) return
  const resp = await axios.delete(`/api/admin/strm/tasks/${branchTask.value.id}/branches/${branch.id}`)
  if (resp.data.success) {
    window.appNotification.success('分支已删除')
    await loadBranches()
    await loadTasks()
  } else {
    window.appNotification.error(resp.data.message || '分支删除失败')
  }
}

const saveTask = async () => {
  if (!form.name.trim()) {
    window.appNotification.error('任务名称不能为空')
    return
  }
  if (Array.from(form.name.trim()).length > 10) {
    window.appNotification.error('任务名称最多10个字符')
    return
  }
  if (!form.account_id || !form.parent_id) {
    window.appNotification.error('请选择账号和目录')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...form,
      sync_metadata: form.sync_metadata === 'true',
      branch_check_enabled: Boolean(form.branch_check_enabled),
      time_window_enabled: form.time_window_mode === 'custom',
      time_start: form.time_start,
      time_end: form.time_end
    }
    if (!editingId.value) {
      const resp = await axios.post('/api/admin/strm/tasks', payload)
      if (resp.data.success) {
        window.appNotification.success('任务添加成功')
        closeDialog()
        await loadTasks()
      } else {
        window.appNotification.error(resp.data.message || '添加失败')
      }
    } else {
      const resp = await axios.put(`/api/admin/strm/tasks/${editingId.value}`, payload)
      if (resp.data.success) {
        window.appNotification.success('任务更新成功')
        closeDialog()
        await loadTasks()
      } else {
        window.appNotification.error(resp.data.message || '更新失败')
      }
    }
  } catch (error) {
    window.appNotification.error('保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

const editTask = (task) => {
  editingId.value = task.id
  Object.assign(form, {
    name: task.name,
    account_id: task.account_id,
    parent_id: task.parent_id,
    path: task.path,
    scan_mode: task.scan_mode || 'incremental_update',
    api_interval: task.api_interval || 200,
    exclude_dir_keywords: task.exclude_dir_keywords || '',
    exclude_file_keywords: task.exclude_file_keywords || '',
    sync_metadata: task.sync_metadata ? 'true' : 'false',
    branch_check_enabled: Boolean(task.branch_check_enabled),
    time_window_mode: task.time_window_enabled ? 'custom' : 'always',
    time_start: task.time_start || '00:00',
    time_end: task.time_end || '00:00'
  })
  showDialog.value = true
}

const toggleTask = async (taskId) => {
  const resp = await axios.post(`/api/admin/strm/tasks/${taskId}/toggle`)
  if (resp.data.success) {
    await loadTasks()
  } else {
    window.appNotification.error(resp.data.message || '切换失败')
  }
}

const setTaskEnabled = async (task, enabled) => {
  const isRunning = task.status === 'running'
  if ((enabled && isRunning) || (!enabled && !isRunning)) {
    return
  }
  await toggleTask(task.id)
}

const handleRunButtonClick = (task) => {
  if (task.branch_check_enabled) return
  runTask(task.id, 'full')
}

const runTask = async (taskId, mode = 'auto') => {
  const resp = await axios.post(`/api/admin/strm/tasks/${taskId}/run`, null, {
    params: { mode }
  })
  if (resp.data.success) {
    const runtimeState = resp.data.data?.runtime_state
    tasks.value = tasks.value.map(task => (
      task.id === taskId
        ? { ...task, is_scanning: runtimeState !== 'queued' && runtimeState !== 'already_queued', is_queued: runtimeState === 'queued' || runtimeState === 'already_queued' }
        : task
    ))
    window.appNotification.success(resp.data.message || '已触发执行')
    await loadTasks()
  } else {
    window.appNotification.error(resp.data.message || '触发失败')
  }
}

const forceStopTask = async (taskId) => {
  stopTasksPolling()
  try {
    const resp = await axios.post(`/api/admin/strm/tasks/${taskId}/force-stop`)
    if (resp.data.success) {
      window.appNotification.success(resp.data.message || '已强制停止')
      await loadTasks()
      if (tasks.value.some(t => t.is_scanning)) {
        startTasksPolling()
      }
    } else {
      window.appNotification.info(resp.data.message || '任务未在执行中')
    }
  } catch (error) {
    console.error('强制停止失败:', error)
    startTasksPolling()
  }
}

const deleteTask = async (taskId) => {
  try {
    const result = await confirm({
      title: '确认删除',
      content: '确定要删除该STRM同步任务吗？',
      confirmText: '删除',
      confirmClass: 'btn-danger',
      icon: 'trash',
      checkboxLabel: '同时删除 strm 文件'
    })

    const deleteStrmFiles = !!result?.checked
    const resp = await axios.delete(`/api/admin/strm/tasks/${taskId}`, {
      params: {
        delete_strm_files: deleteStrmFiles
      }
    })
    if (resp.data.success) {
      window.appNotification.success(deleteStrmFiles ? '任务和 strm 文件已删除' : '删除成功')
      await loadTasks()
    } else {
      window.appNotification.error(resp.data.message || '删除失败')
    }
  } catch (error) {
    if (error.message !== 'Modal closed') {
      window.appNotification.error('删除失败: ' + error.message)
    }
  }
}

const replaceAllDomains = async () => {
  if (!replaceDomain.value.trim()) {
    window.appNotification.error('请输入新域名')
    return
  }
  const resp = await axios.post('/api/admin/strm/replace-domain', { new_base_url: replaceDomain.value.trim() })
  if (resp.data.success) {
    window.appNotification.success(`替换完成：${resp.data.data.updated}/${resp.data.data.total}`)
    await loadStrmSettings()
  } else {
    window.appNotification.error(resp.data.message || '替换失败')
  }
}

const saveEmbyProxy = async () => {
  if (!embyForm.name.trim()) {
    window.appNotification.error('反代名称不能为空')
    return
  }
  if (!embyForm.emby_url.trim()) {
    window.appNotification.error('请输入Emby地址')
    return
  }
  if (!embyForm.api_key.trim()) {
    window.appNotification.error('请输入Emby API Key')
    return
  }
  const proxyPort = Number(embyForm.proxy_port)
  if (!Number.isInteger(proxyPort) || proxyPort < 1 || proxyPort > 65535) {
    window.appNotification.error('请输入有效的反代监听端口')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: embyForm.name.trim(),
      emby_url: embyForm.emby_url.trim(),
      api_key: embyForm.api_key.trim(),
      proxy_port: proxyPort
    }
    const response = embyEditingId.value
      ? await axios.put(`/api/admin/strm/emby-proxies/${embyEditingId.value}`, payload)
      : await axios.post('/api/admin/strm/emby-proxies', payload)
    if (response.data.success) {
      window.appNotification.success(embyEditingId.value ? '反代更新成功' : '反代创建成功')
      closeEmbyDialog()
      await loadEmbyProxies()
    } else {
      window.appNotification.error(response.data.message || '保存失败')
    }
  } catch (error) {
    window.appNotification.error('保存失败: ' + (error.response?.data?.message || error.message))
  } finally {
    saving.value = false
  }
}

const editEmbyProxy = (proxy) => {
  embyEditingId.value = proxy.id
  Object.assign(embyForm, {
    name: proxy.name || '',
    emby_url: proxy.emby_url || '',
    api_key: proxy.api_key || '',
    proxy_port: Number(proxy.proxy_port) || ''
  })
  embyShowDialog.value = true
}

const toggleEmbyProxy = async (proxyId) => {
  const response = await axios.post(`/api/admin/strm/emby-proxies/${proxyId}/toggle`)
  if (response.data.success) {
    await loadEmbyProxies()
  } else {
    window.appNotification.error(response.data.message || '切换失败')
  }
}

const setEmbyProxyEnabled = async (proxy, enabled) => {
  const isRunning = proxy.status === 'running'
  if ((enabled && isRunning) || (!enabled && !isRunning)) return
  await toggleEmbyProxy(proxy.id)
}

const testEmbyProxy = async (proxyId) => {
  const response = await axios.post(`/api/admin/strm/emby-proxies/${proxyId}/test`)
  if (response.data.success) {
    window.appNotification.success(response.data.message || 'Emby连接测试通过')
  } else {
    window.appNotification.error(response.data.message || 'Emby连接测试失败')
  }
}

const copyTextFallback = (text) => {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '0'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()
  textarea.setSelectionRange(0, textarea.value.length)
  let copied = false
  try {
    copied = document.execCommand('copy')
  } finally {
    document.body.removeChild(textarea)
  }
  return copied
}

const copyEmbyProxyUrl = async (url) => {
  if (!url) return
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(url)
    } else if (!copyTextFallback(url)) {
      throw new Error('fallback copy failed')
    }
    window.appNotification.success('反代入口已复制')
  } catch (error) {
    if (copyTextFallback(url)) {
      window.appNotification.success('反代入口已复制')
      return
    }
    window.appNotification.error('复制失败，请手动复制入口地址')
  }
}

const deleteEmbyProxy = async (proxyId) => {
  try {
    await confirm({
      title: '确认删除',
      content: '确定要删除该Emby反代吗？',
      confirmText: '删除',
      confirmClass: 'btn-danger',
      icon: 'trash'
    })
    const response = await axios.delete(`/api/admin/strm/emby-proxies/${proxyId}`)
    if (response.data.success) {
      window.appNotification.success('反代删除成功')
      await loadEmbyProxies()
    } else {
      window.appNotification.error(response.data.message || '删除失败')
    }
  } catch (error) {
    if (error.message !== 'Modal closed') {
      window.appNotification.error('删除失败: ' + (error.response?.data?.message || error.message))
    }
  }
}

onMounted(async () => {
  await adminStore.fetchAccounts()
  await loadStrmSettings()
  await loadTasks()
  await loadEmbyProxies()
  startTasksPolling()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

const handleVisibilityChange = () => {
  if (!document.hidden && activeTab.value === 'tasks') {
    startTasksPolling()
  }
}

// ── 目录整理方法 ──

const loadOrganizeTasks = async () => {
  try {
    const resp = await axios.get('/api/admin/media-organize/tasks')
    if (resp.data.success) {
      organizeTasks.value = resp.data.data || []
    }
  } catch (e) {
    // 静默失败，轮询不需要报错
  }
}

const loadOrganizeSettings = async () => {
  try {
    const resp = await axios.get('/api/admin/media-organize/settings')
    if (resp.data.success && resp.data.data) {
      Object.assign(organizeSettings, resp.data.data)
      organizeSettings.align_media_tags = normalizeBooleanSetting(organizeSettings.align_media_tags)
      organizeSettings.overwrite_existing = normalizeBooleanSetting(organizeSettings.overwrite_existing)
      if (organizeSettings.max_works_per_run == null || organizeSettings.max_works_per_run === '') {
        organizeSettings.max_works_per_run = 50
      } else {
        organizeSettings.max_works_per_run = Number(organizeSettings.max_works_per_run) || 0
      }
      syncTagsFromSettings()
    }
  } catch (e) {
    // 使用默认值
  }
}

const normalizeBooleanSetting = value => {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') return ['1', 'true', 'yes', 'on', '开启'].includes(value.trim().toLowerCase())
  return false
}

const getAccountName = (accountId) => {
  const acc = (accounts.value || []).find(a => String(a.id) === String(accountId))
  return acc ? acc.name : accountId
}

const isOrganizeTaskActive = (task) => ['running', 'stopping'].includes(task?.status)

const getOrganizeTaskStatusClass = (task) => {
  if (isOrganizeTaskActive(task)) return 'scanning'
  if (task.last_run_result && (task.last_run_result.failed || 0) > 0) return 'error'
  if (task.last_run_result) return 'success'
  return 'pending'
}

const getOrganizeTaskStatusText = (task) => {
  if (task.status === 'stopping') return '停止中'
  if (task.status === 'running') return '执行中'
  if (task.last_run_result?.stopped) return '已停止'
  if (task.last_run_result && (task.last_run_result.failed || 0) > 0) return '有失败'
  if (task.last_run_result) return '已完成'
  return '未执行'
}

const getOrganizeTaskStatusTitle = (task) => {
  const result = task.last_run_result
  if (!result) {
    if (task.status === 'stopping') return '任务正在停止，当前操作完成后退出'
    return task.status === 'running' ? '任务正在执行' : '任务尚未执行'
  }
  if (result.stopped) return `已停止：总数 ${result.total || 0}，改名 ${result.renamed || 0}，移动 ${result.moved || 0}，跳过 ${result.skipped || 0}，失败 ${result.failed || 0}`
  return `总数 ${result.total || 0}，改名 ${result.renamed || 0}，移动 ${result.moved || 0}，跳过 ${result.skipped || 0}，失败 ${result.failed || 0}`
}

const switchOrganizeActionType = (type) => {
  organizeForm.action_type = type
  if (type === 'rename' && !organizeForm.rename_marker.trim()) {
    organizeForm.rename_marker = 'tmdb'
  }
}

const openOrganizeAddDialog = () => {
  organizeEditingId.value = null
  Object.assign(organizeForm, {
    task_name: '',
    account_id: null,
    target_directory: '',
    target_directory_id: '',
    action_type: 'move',
    target_root: '',
    target_root_id: '',
    media_type: 'auto',
    rename_marker: '',
    use_ffprobe: 'false',
    use_tmdb: 'true',
    recursive: true,
  })
  organizeShowDialog.value = true
}

const editOrganizeTask = (task) => {
  organizeEditingId.value = task.id
  const cfg = task.config || {}
  Object.assign(organizeForm, {
    task_name: task.task_name,
    account_id: task.account_id ? Number(task.account_id) : null,
    target_directory: cfg.target_directory || '',
    target_directory_id: cfg.target_directory_id || '',
    action_type: cfg.action_type || 'move',
    target_root: cfg.target_root || '',
    target_root_id: cfg.target_root_id || '',
    media_type: cfg.media_type || 'auto',
    rename_marker: cfg.rename_marker || '',
    use_ffprobe: cfg.use_ffprobe ? 'true' : 'false',
    use_tmdb: cfg.use_tmdb !== false ? 'true' : 'false',
    recursive: cfg.recursive !== false,
  })
  organizeShowDialog.value = true
}

const saveOrganizeTask = async () => {
  if (!organizeForm.task_name.trim()) {
    window.appNotification.warning('请输入任务名称')
    return
  }
  if (!organizeForm.account_id) {
    window.appNotification.warning('请选择网盘账号')
    return
  }
  if (organizeForm.action_type === 'move' && !organizeForm.target_root.trim()) {
    window.appNotification.warning('move 模式下目标根目录不能为空')
    return
  }
  if (organizeForm.action_type === 'rename' && !organizeForm.rename_marker.trim()) {
    window.appNotification.warning('原地重命名必须设置标识（tmdb 或自定义），已整理文件靠标识判断跳过')
    return
  }

  const payload = {
    task_name: organizeForm.task_name.trim(),
    account_id: String(organizeForm.account_id),
    target_directory: organizeForm.target_directory,
    target_directory_id: organizeForm.target_directory_id,
    action_type: organizeForm.action_type,
    target_root: organizeForm.target_root,
    target_root_id: organizeForm.target_root_id,
    media_type: organizeForm.media_type,
    rename_marker: organizeForm.rename_marker,
    use_ffprobe: organizeForm.use_ffprobe === 'true',
    use_tmdb: organizeForm.use_tmdb === 'true',
    recursive: organizeForm.recursive,
  }

  organizeSaving.value = true
  try {
    if (organizeEditingId.value) {
      const resp = await axios.put(`/api/admin/media-organize/tasks/${organizeEditingId.value}`, payload)
      if (resp.data.success) {
        window.appNotification.success('任务更新成功')
        organizeShowDialog.value = false
        await loadOrganizeTasks()
      } else {
        window.appNotification.error(resp.data.message || '更新失败')
      }
    } else {
      const resp = await axios.post('/api/admin/media-organize/tasks', payload)
      if (resp.data.success) {
        window.appNotification.success('任务创建成功')
        organizeShowDialog.value = false
        await loadOrganizeTasks()
      } else {
        window.appNotification.error(resp.data.message || '创建失败')
      }
    }
  } catch (e) {
    window.appNotification.error('操作失败: ' + (e.response?.data?.message || e.message))
  } finally {
    organizeSaving.value = false
  }
}

const runOrganizeTask = async (taskId) => {
  const idx = organizeTasks.value.findIndex(t => t.id === taskId)
  if (idx >= 0) organizeTasks.value[idx].status = 'running'
  if (organizeLogTaskId.value === taskId) {
    loadOrganizeLogs(taskId)
    startOrganizeLogPolling(taskId)
  }
  try {
    const resp = await axios.post(`/api/admin/media-organize/tasks/${taskId}/run`)
    if (!resp.data.success) {
      window.appNotification.error(resp.data.message || '启动失败')
      if (idx >= 0) organizeTasks.value[idx].status = 'idle'
      if (organizeLogTaskId.value === taskId) stopOrganizeLogPolling()
      return
    }
  } catch (e) {
    window.appNotification.error('启动失败: ' + (e.response?.data?.message || e.message))
    if (idx >= 0) organizeTasks.value[idx].status = 'idle'
    if (organizeLogTaskId.value === taskId) stopOrganizeLogPolling()
    return
  }

  let retries = 0
  while (retries < 360) {
    if (organizeLogTaskId.value === taskId) await loadOrganizeLogs(taskId)
    await loadOrganizeTasks()
    const task = organizeTasks.value.find(t => t.id === taskId)
    if (!task || !isOrganizeTaskActive(task)) {
      if (organizeLogTaskId.value === taskId) {
        await loadOrganizeLogs(taskId)
        stopOrganizeLogPolling()
      }
      if (task && task.last_run_result) {
        if (task.last_run_result.stopped) {
          window.appNotification.info('整理任务已停止')
        } else {
          window.appNotification.success(`完成：改名${task.last_run_result.renamed||0} 移动${task.last_run_result.moved||0} 跳过${task.last_run_result.skipped||0}`)
        }
      }
      return
    }
    await new Promise(r => setTimeout(r, 2000))
    retries++
  }
  window.appNotification.warning('执行超时，请刷新查看状态')
}

const stopOrganizeTask = async (taskId) => {
  const idx = organizeTasks.value.findIndex(t => t.id === taskId)
  if (idx >= 0) organizeTasks.value[idx].status = 'stopping'
  if (organizeLogTaskId.value === taskId) {
    loadOrganizeLogs(taskId)
    startOrganizeLogPolling(taskId)
  }
  try {
    const resp = await axios.post(`/api/admin/media-organize/tasks/${taskId}/stop`)
    if (resp.data.success) {
      window.appNotification.info(resp.data.message || '已请求停止')
      await loadOrganizeTasks()
    } else {
      window.appNotification.error(resp.data.message || '停止失败')
      await loadOrganizeTasks()
    }
  } catch (e) {
    window.appNotification.error('停止失败: ' + (e.response?.data?.message || e.message))
    await loadOrganizeTasks()
  }
}

const openOrganizeLogPanel = (taskId) => {
  const task = organizeTasks.value.find(t => t.id === taskId)
  organizeLogTaskId.value = taskId
  organizeLogTaskName.value = task?.task_name || ''
  organizeLogs.value = []
  loadOrganizeLogs(taskId)
  startOrganizeLogPolling(taskId)
}

const closeOrganizeLogPanel = () => {
  stopOrganizeLogPolling()
  organizeLogTaskId.value = null
  organizeLogTaskName.value = ''
  organizeLogs.value = []
}

const startOrganizeLogPolling = (taskId) => {
  stopOrganizeLogPolling()
  organizeLogPollTimer = window.setInterval(() => {
    loadOrganizeLogs(taskId)
  }, 1000)
}

const stopOrganizeLogPolling = () => {
  if (organizeLogPollTimer) {
    window.clearInterval(organizeLogPollTimer)
    organizeLogPollTimer = null
  }
}

const _organizeHasActiveTasks = () => {
  return organizeTasks.value.some(t => ['running', 'planning', 'stopping'].includes(t?.status))
}

const _startOrganizeTaskListPolling = () => {
  if (organizeTaskListPollTimer) return
  organizeTaskListPollTimer = window.setInterval(async () => {
    if (activeTab.value !== 'organize') {
      _stopOrganizeTaskListPolling()
      return
    }
    await loadOrganizeTasks()
    if (!_organizeHasActiveTasks()) {
      _stopOrganizeTaskListPolling()
    }
  }, 4000)
}

const _stopOrganizeTaskListPolling = () => {
  if (organizeTaskListPollTimer) {
    window.clearInterval(organizeTaskListPollTimer)
    organizeTaskListPollTimer = null
  }
}

watch(activeTab, (next) => {
  if (next === 'organize') {
    if (_organizeHasActiveTasks()) _startOrganizeTaskListPolling()
  } else {
    _stopOrganizeTaskListPolling()
  }
})

watch(organizeTasks, () => {
  if (activeTab.value !== 'organize') return
  if (_organizeHasActiveTasks()) {
    _startOrganizeTaskListPolling()
  } else {
    _stopOrganizeTaskListPolling()
  }
})

const _patchOrganizeTaskFromLogs = (taskId, status, lastRunResult) => {
  const idx = organizeTasks.value.findIndex(t => String(t.id) === String(taskId))
  if (idx < 0) return
  const next = { ...organizeTasks.value[idx] }
  let dirty = false
  if (status && next.status !== status) {
    next.status = status
    dirty = true
  }
  if (lastRunResult !== undefined && JSON.stringify(next.last_run_result || null) !== JSON.stringify(lastRunResult || null)) {
    next.last_run_result = lastRunResult || null
    dirty = true
  }
  if (dirty) {
    const arr = [...organizeTasks.value]
    arr.splice(idx, 1, next)
    organizeTasks.value = arr
  }
}

const loadOrganizeLogs = async (taskId) => {
  if (!taskId) return
  try {
    const resp = await axios.get(`/api/admin/media-organize/tasks/${taskId}/logs`)
    if (resp.data.success) {
      organizeLogs.value = resp.data.data?.logs || []
      const status = resp.data.data?.status
      const lastRunResult = resp.data.data?.last_run_result
      _patchOrganizeTaskFromLogs(taskId, status, lastRunResult)
      requestAnimationFrame(() => {
        if (organizeLogBodyRef.value) {
          organizeLogBodyRef.value.scrollTop = organizeLogBodyRef.value.scrollHeight
        }
      })
      if (!['running', 'planning', 'stopping'].includes(status)) {
        stopOrganizeLogPolling()
      }
    }
  } catch (error) {
    console.error('加载整理日志失败:', error)
  }
}

const restoreOrganizeLogPanel = async () => {
  if (organizeLogTaskId.value) return
  const taskId = localStorage.getItem(ORGANIZE_LOG_TASK_STORAGE_KEY)
  if (!taskId) return
  if (organizeTasks.value.length === 0) {
    await loadOrganizeTasks()
  }
  const task = organizeTasks.value.find(t => t.id === taskId)
  if (!task) {
    localStorage.removeItem(ORGANIZE_LOG_TASK_STORAGE_KEY)
    return
  }
  organizeLogTaskId.value = taskId
  organizeLogTaskName.value = task.task_name || ''
  await loadOrganizeLogs(taskId)
  if (isOrganizeTaskActive(task)) {
    startOrganizeLogPolling(taskId)
  }
}

const deleteOrganizeTask = async (taskId) => {
  try {
    await confirm({
      title: '确认删除',
      content: '确定要删除该整理任务吗？',
      confirmText: '删除',
      confirmClass: 'btn-danger',
      icon: 'trash',
    })
  } catch (e) {
    return
  }
  try {
    const resp = await axios.delete(`/api/admin/media-organize/tasks/${taskId}`)
    if (resp.data.success) {
      if (resp.data.data?.stopping) {
        const idx = organizeTasks.value.findIndex(t => t.id === taskId)
        if (idx >= 0) organizeTasks.value[idx].status = 'stopping'
        window.appNotification.info(resp.data.message || '已请求停止')
        if (organizeLogTaskId.value === taskId) {
          startOrganizeLogPolling(taskId)
        }
        await loadOrganizeTasks()
        return
      }
      window.appNotification.success('任务删除成功')
      if (organizeLogTaskId.value === taskId) {
        closeOrganizeLogPanel()
      } else if (localStorage.getItem(ORGANIZE_LOG_TASK_STORAGE_KEY) === taskId) {
        localStorage.removeItem(ORGANIZE_LOG_TASK_STORAGE_KEY)
      }
      await loadOrganizeTasks()
    } else {
      window.appNotification.error(resp.data.message || '删除失败')
    }
  } catch (e) {
    if (e.message !== 'Modal closed') {
      window.appNotification.error('删除失败: ' + (e.response?.data?.message || e.message))
    }
  }
}

const actionIconClass = (action) => {
  if (!action) return ''
  if (action.source_parent_id === action.target_parent_id) return 'rename'
  return 'move'
}

const actionIconName = (action) => {
  if (!action) return 'fas fa-pen-to-square'
  if (action.source_parent_id === action.target_parent_id) return 'fas fa-pen-to-square'
  return 'fas fa-arrow-right-arrow-left'
}

const _splitOrganizePlan = (plan) => {
  const actions = (plan && plan.actions) || []
  organizePlanRelocates.value = actions.filter(a => a.kind === 'relocate')
  organizePlanEnsures.value = actions.filter(a => a.kind === 'ensure_dir')
  organizePlanSkipped.value = (plan && plan.skipped) || []
  organizePlanTmdbStatus.value = (plan && plan.diagnostics && plan.diagnostics.tmdb_status) || ''
  organizePlanGroupExpanded.value = {}
  organizePlanSkipExpanded.value = false
  organizePlanSkipExpandedReasons.value = {}
  organizePlanSkipShowAll.value = {}
  organizePlanExpandedRanges.value = {}
}

const organizePlanNoTmdbCount = computed(() => {
  return organizePlanRelocates.value.filter(a => !(a.metadata && a.metadata.tmdb_id)).length
})

const _episodeNumberFromName = (name) => {
  if (!name) return null
  const m = name.match(/S(\d{1,3})E(\d{1,4})/i)
  if (m) return { season: parseInt(m[1], 10), episode: parseInt(m[2], 10) }
  return null
}

const _isNumericEpisodeSource = (name) => {
  if (!name) return false
  const stem = name.replace(/\.[^.]+$/, '').trim()
  return /^\d{1,4}(?:\s*(?:4k|2160p|1080p|720p))?$/i.test(stem)
}

const _formatCollapsedOldPattern = (oldP, items, seasonKey) => {
  if (oldP.startsWith('NUM{ee}')) {
    const ext = oldP.slice('NUM{ee}'.length) || '.mp4'
    const eps = items.map(a => a._ep).filter(v => v != null).sort((a, b) => a - b)
    if (!eps.length) return `*${ext}`
    const pad = (n) => String(n).padStart(2, '0')
    if (eps.length === 1) return `${pad(eps[0])}${ext}`
    const consecutive = eps.every((ep, i) => i === 0 || ep === eps[i - 1] + 1)
    if (consecutive) {
      return `${pad(eps[0])}–${pad(eps[eps.length - 1])}${ext}`
    }
    return `${pad(eps[0])}…${pad(eps[eps.length - 1])}${ext}`
  }
  return oldP.replace('S{ss}E{ee}', `S${String(seasonKey).padStart(2, '0')}E**`)
}

const _formatCollapsedNewPattern = (newP, seasonKey) => {
  return newP.replace('S{ss}E{ee}', `S${String(seasonKey).padStart(2, '0')}E**`)
}

const _patternOf = (name, season, episode) => {
  if (!name) return ''
  if (season != null && episode != null) {
    const tag = `S${String(season).padStart(2,'0')}E${String(episode).padStart(2,'0')}`
    if (name.includes(tag)) {
      return name.split(tag).join('S{ss}E{ee}')
    }
    if (_isNumericEpisodeSource(name)) {
      const ext = name.match(/(\.[^.]+)$/)?.[1] || ''
      return `NUM{ee}${ext}`
    }
  }
  return name
}

const organizePlanGroups = computed(() => {
  const map = new Map()
  for (const action of organizePlanRelocates.value) {
    const md = action.metadata || {}
    const tmdbId = md.tmdb_id || ''
    let key
    if (tmdbId) {
      key = 'tmdb:' + tmdbId
    } else {
      const fallback = String(action.reason || '').split('|')[1]?.trim() || action.target_name
      key = 'title:' + fallback
    }
    if (!map.has(key)) {
      map.set(key, { key, tmdbId, dirAction: null, actions: [] })
    }
    const bucket = map.get(key)
    if ((md.kind_label || '') === 'dir_rename') {
      bucket.dirAction = action
    } else {
      bucket.actions.push(action)
    }
  }

  const groups = []
  for (const g of map.values()) {
    let title
    let titleOld = ''
    let titleNew = ''
    let virtualDir = false
    if (g.dirAction) {
      titleOld = g.dirAction.source_name
      titleNew = g.dirAction.target_name
      title = titleNew
    } else {
      const sample = g.actions[0]
      const md = (sample && sample.metadata) || {}
      if (md.group_old_dir_name && md.group_new_dir_name) {
        titleOld = md.group_old_dir_name
        titleNew = md.group_new_dir_name
        title = titleNew
        virtualDir = true
      } else if (sample) {
        title = String(sample.reason || '').split('|')[1]?.trim() || sample.target_name
      } else {
        title = `tmdb-${g.tmdbId}`
      }
    }

    const seasonBuckets = new Map()
    for (const action of g.actions) {
      const ep = _episodeNumberFromName(action.target_name)
      const seasonKey = ep ? ep.season : 0
      if (!seasonBuckets.has(seasonKey)) seasonBuckets.set(seasonKey, [])
      seasonBuckets.get(seasonKey).push({ ...action, _ep: ep ? ep.episode : null })
    }

    const collapsedRanges = []
    const visibleActions = []
    let groupIndex = 0
    for (const [seasonKey, list] of seasonBuckets.entries()) {
      list.sort((a, b) => (a._ep || 0) - (b._ep || 0))
      if (seasonKey === 0) {
        for (const a of list) visibleActions.push(a)
        continue
      }
      const subBuckets = new Map()
      for (const a of list) {
        const oldP = _patternOf(a.source_name, seasonKey, a._ep)
        const newP = _patternOf(a.target_name, seasonKey, a._ep)
        const subKey = `${oldP}\u0001${newP}`
        if (!subBuckets.has(subKey)) subBuckets.set(subKey, { oldP, newP, items: [] })
        subBuckets.get(subKey).items.push(a)
      }
      for (const { oldP, newP, items } of subBuckets.values()) {
        if (items.length < 3) {
          for (const a of items) visibleActions.push(a)
          continue
        }
        groupIndex += 1
        const rangeKey = `${g.key}::S${seasonKey}::p${groupIndex}`
        if (!organizePlanExpandedRanges.value[rangeKey]) {
          const eps = items.map(a => a._ep).filter(v => v != null)
          const minEp = eps.length ? Math.min(...eps) : null
          const maxEp = eps.length ? Math.max(...eps) : null
          const consecutive = items.every((a, i) => i === 0 || a._ep === items[i - 1]._ep + 1)
          collapsedRanges.push({
            key: rangeKey,
            season: seasonKey,
            startEpisode: minEp,
            endEpisode: maxEp,
            consecutive,
            actions: items,
            sample: items[0],
            samplePattern: {
              oldPattern: _formatCollapsedOldPattern(oldP, items, seasonKey),
              newPattern: _formatCollapsedNewPattern(newP, seasonKey),
            },
          })
        } else {
          for (const a of items) visibleActions.push(a)
        }
      }
    }

    const expandKey = g.key
    const expanded = organizePlanGroupExpanded.value[expandKey] === true
    const actionCount = g.actions.length + (g.dirAction ? 1 : 0)
    groups.push({
      key: g.key,
      tmdbId: g.tmdbId,
      dirAction: g.dirAction,
      virtualDir,
      hasDirInfo: Boolean(g.dirAction || (titleOld && titleNew)),
      title,
      titleOld,
      titleNew,
      actions: g.actions,
      actionCount,
      expanded,
      collapsedRanges,
      visibleActions,
    })
  }
  return groups
})

const toggleOrganizePlanGroup = (key) => {
  organizePlanGroupExpanded.value = {
    ...organizePlanGroupExpanded.value,
    [key]: !organizePlanGroupExpanded.value[key],
  }
}

const expandCollapsedRange = (groupKey, rangeIdx) => {
  const group = organizePlanGroups.value.find(g => g.key === groupKey)
  if (!group) return
  const range = group.collapsedRanges[rangeIdx]
  if (!range) return
  organizePlanExpandedRanges.value = {
    ...organizePlanExpandedRanges.value,
    [range.key]: true,
  }
}

const startPlanActionEdit = (action) => {
  organizePlanEditingId.value = action.id
  organizePlanEditingName.value = action.target_name || ''
}

const cancelPlanActionEdit = () => {
  organizePlanEditingId.value = null
  organizePlanEditingName.value = ''
}

const commitPlanActionEdit = async (action) => {
  const taskId = organizePlanTaskId.value
  const newName = (organizePlanEditingName.value || '').trim()
  if (!taskId || !action || !newName) {
    window.appNotification.warning('目标名不能为空')
    return
  }
  if (newName === action.target_name) {
    cancelPlanActionEdit()
    return
  }
  try {
    organizePlanEditingSaving.value = true
    const resp = await axios.put(
      `/api/admin/media-organize/tasks/${taskId}/plan/actions/${action.id}`,
      { target_name: newName }
    )
    if (resp.data.success) {
      action.target_name = resp.data.data?.action?.target_name || newName
      if (!action.metadata) action.metadata = {}
      action.metadata.edited = true
      cancelPlanActionEdit()
    } else {
      window.appNotification.error(resp.data.message || '保存失败')
    }
  } catch (e) {
    window.appNotification.error('保存失败: ' + (e.response?.data?.message || e.message))
  } finally {
    organizePlanEditingSaving.value = false
  }
}

const removePlanAction = async (action) => {
  const taskId = organizePlanTaskId.value
  if (!taskId || !action) return
  try {
    await confirm({
      title: '从计划中移除',
      content: `确定从计划中移除 “${action.source_name}” 吗？该文件不会被整理。`,
      confirmText: '移除',
      confirmClass: 'btn-danger',
      icon: 'trash',
      hideCancelButton: false,
    })
  } catch (e) {
    return
  }
  try {
    const resp = await axios.delete(`/api/admin/media-organize/tasks/${taskId}/plan/actions/${action.id}`)
    if (resp.data.success) {
      organizePlanRelocates.value = organizePlanRelocates.value.filter(a => a.id !== action.id)
    } else {
      window.appNotification.error(resp.data.message || '删除失败')
    }
  } catch (e) {
    window.appNotification.error('删除失败: ' + (e.response?.data?.message || e.message))
  }
}

const removePlanGroup = async (group) => {
  const taskId = organizePlanTaskId.value
  if (!taskId || !group) return
  const total = (group.actions ? group.actions.length : 0) + (group.dirAction ? 1 : 0)
  try {
    await confirm({
      title: '移除整个作品',
      content: `确定从计划中移除整个作品 “${group.title}”（共 ${total} 项）吗？这些条目不会被整理。`,
      confirmText: '移除整组',
      confirmClass: 'btn-danger',
      icon: 'trash',
      hideCancelButton: false,
    })
  } catch (e) {
    return
  }
  const toRemove = [...group.actions]
  if (group.dirAction) toRemove.push(group.dirAction)
  const removedIds = []
  for (const action of toRemove) {
    try {
      const resp = await axios.delete(`/api/admin/media-organize/tasks/${taskId}/plan/actions/${action.id}`)
      if (resp.data.success) removedIds.push(action.id)
    } catch (e) {}
  }
  if (removedIds.length) {
    const removedSet = new Set(removedIds)
    organizePlanRelocates.value = organizePlanRelocates.value.filter(a => !removedSet.has(a.id))
    window.appNotification.success(`已移除 ${removedIds.length} 项`)
  } else {
    window.appNotification.error('移除失败')
  }
}

const _startOrganizePlanProgressPolling = (taskId) => {
  _stopOrganizePlanProgressPolling()
  organizePlanProgress.value = {}
  const tick = async () => {
    try {
      const resp = await axios.get(`/api/admin/media-organize/tasks/${taskId}/progress`)
      if (resp.data.success) {
        organizePlanProgress.value = resp.data.data || {}
      }
    } catch (e) {}
  }
  tick()
  organizePlanProgressTimer = setInterval(tick, 1200)
}

const _stopOrganizePlanProgressPolling = () => {
  if (organizePlanProgressTimer) {
    clearInterval(organizePlanProgressTimer)
    organizePlanProgressTimer = null
  }
}

const previewOrganizePlan = async (task) => {
  if (!task || !task.id) return
  organizePlanTaskId.value = task.id
  organizePlanTaskName.value = task.task_name || ''
  organizePlanRelocates.value = []
  organizePlanEnsures.value = []
  organizePlanSkipped.value = []
  organizePlanTmdbStatus.value = ''
  organizePlanGroupExpanded.value = {}
  organizePlanExpandedRanges.value = {}
  organizePlanDialogVisible.value = true
  try {
    const existing = await axios.get(`/api/admin/media-organize/tasks/${task.id}/plan`)
    if (existing.data.success && existing.data.data) {
      _splitOrganizePlan(existing.data.data)
      if (organizePlanRelocates.value.length || organizePlanEnsures.value.length) {
        return
      }
    }
    organizePlanLoading.value = true
    _startOrganizePlanProgressPolling(task.id)
    const resp = await axios.post(`/api/admin/media-organize/tasks/${task.id}/plan`)
    if (resp.data.success && resp.data.data?.plan) {
      _splitOrganizePlan(resp.data.data.plan)
    } else {
      window.appNotification.error(resp.data.message || '计划生成失败')
    }
  } catch (e) {
    window.appNotification.error('计划生成失败: ' + (e.response?.data?.message || e.message))
  } finally {
    _stopOrganizePlanProgressPolling()
    organizePlanLoading.value = false
  }
}

const refreshOrganizePlan = async (force = false) => {
  const taskId = organizePlanTaskId.value
  if (!taskId) return
  try {
    organizePlanLoading.value = true
    _startOrganizePlanProgressPolling(taskId)
    const resp = await axios.post(`/api/admin/media-organize/tasks/${taskId}/plan`)
    if (resp.data.success && resp.data.data?.plan) {
      _splitOrganizePlan(resp.data.data.plan)
      window.appNotification.success('计划已重新生成')
    } else {
      window.appNotification.error(resp.data.message || '生成失败')
    }
  } catch (e) {
    window.appNotification.error('生成失败: ' + (e.response?.data?.message || e.message))
  } finally {
    _stopOrganizePlanProgressPolling()
    organizePlanLoading.value = false
  }
}

const closeOrganizePlanDialog = () => {
  organizePlanDialogVisible.value = false
  organizePlanTaskId.value = null
  organizePlanTaskName.value = ''
  organizePlanRelocates.value = []
  organizePlanEnsures.value = []
  organizePlanSkipped.value = []
  organizePlanTmdbStatus.value = ''
  organizePlanGroupExpanded.value = {}
  organizePlanExpandedRanges.value = {}
  organizePlanEditingId.value = null
  organizePlanEditingName.value = ''
  _stopOrganizePlanProgressPolling()
}

const applyOrganizePlan = async () => {
  const taskId = organizePlanTaskId.value
  if (!taskId) return
  try {
    organizePlanApplying.value = true
    const resp = await axios.post(`/api/admin/media-organize/tasks/${taskId}/apply`)
    if (resp.data.success) {
      window.appNotification.success('计划已开始执行，可在日志中查看进度')
      closeOrganizePlanDialog()
      openOrganizeLogPanel(taskId)
      await loadOrganizeTasks()
    } else {
      window.appNotification.error(resp.data.message || '执行失败')
    }
  } catch (e) {
    window.appNotification.error('执行失败: ' + (e.response?.data?.message || e.message))
  } finally {
    organizePlanApplying.value = false
  }
}

const saveOrganizeSettings = async () => {
  organizeSaving.value = true
  try {
    const payload = {
      ...organizeSettings,
      align_media_tags: normalizeBooleanSetting(organizeSettings.align_media_tags),
      overwrite_existing: normalizeBooleanSetting(organizeSettings.overwrite_existing),
    }
    const resp = await axios.put('/api/admin/media-organize/settings', payload)
    if (resp.data.success) {
      window.appNotification.success('设置保存成功')
    } else {
      window.appNotification.error(resp.data.message || '保存失败')
    }
  } catch (e) {
    window.appNotification.error('保存失败: ' + (e.response?.data?.message || e.message))
  } finally {
    organizeSaving.value = false
  }
}

const browseOrganizeDir = async () => {
  if (!organizeForm.account_id) {
    window.appNotification.warning('请先选择账号')
    return
  }
  const result = await selectFolder(organizeForm.account_id, {
    initialPath: organizeForm.target_directory
  })
  if (result) {
    organizeForm.target_directory = result.path
    organizeForm.target_directory_id = result.id
  }
}

const browseOrganizeTargetRoot = async () => {
  if (!organizeForm.account_id) {
    window.appNotification.warning('请先选择账号')
    return
  }
  const result = await selectFolder(organizeForm.account_id, {
    initialPath: organizeForm.target_root
  })
  if (result) {
    organizeForm.target_root = result.path
    organizeForm.target_root_id = result.id
  }
}

const handleOrganizeDialogKeydown = (event) => {
  if (event.key !== 'Escape' || !organizeShowDialog.value) return
  const activeModal = document.querySelector('.modern-modal-overlay')
  if (activeModal) return
  event.preventDefault()
  event.stopPropagation()
  event.stopImmediatePropagation?.()
  organizeShowDialog.value = false
}

// 切换 Tab 时加载数据
watch(() => activeTab.value, (tab) => {
  if (tab === 'organize') {
    loadOrganizeTasks()
    loadOrganizeSettings()
  }
  if (tab === 'organizeSettings') {
    loadOrganizeSettings()
  }
})

watch(organizeShowDialog, (visible) => {
  if (visible) {
    document.addEventListener('keydown', handleOrganizeDialogKeydown)
  } else {
    document.removeEventListener('keydown', handleOrganizeDialogKeydown)
  }
})

watch([showDialog, embyShowDialog, branchDialogVisible], ([taskVisible, embyVisible, branchVisible]) => {
  if (taskVisible || embyVisible || branchVisible) {
    document.addEventListener('keydown', handleDialogKeydown)
  } else {
    document.removeEventListener('keydown', handleDialogKeydown)
  }
})

onBeforeUnmount(() => {
  stopTasksPolling()
  stopOrganizeLogPolling()
  document.removeEventListener('keydown', handleDialogKeydown)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.strm-generator {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.strm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
}

.strm-header .tab-nav {
  flex: 1;
  min-width: 0;
}

.strm-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  background: #f8fafc;
  padding: 4px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.strm-tabs .tab-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.2;
  white-space: nowrap;
  transition: all 0.2s ease;
  position: relative;
}

.strm-tabs .tab-btn:hover {
  background: linear-gradient(135deg, #3b5bdb, #1e88e5);
  color: #fff;
}

.strm-tabs .tab-btn.active {
  background: linear-gradient(135deg, #4c74df, #02a6f0);
  color: #fff;
  box-shadow: 0 2px 4px rgba(76, 116, 223, 0.3);
}

.tab-dropdown {
  position: relative;
}

.tab-dropdown::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 100%;
  height: 8px;
}

.tab-dropdown-arrow {
  font-size: 12px;
  transition: transform 0.2s ease;
}

.tab-dropdown-arrow.open {
  transform: rotate(180deg);
}

.tab-dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 160px;
  padding: 6px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  z-index: 20;
}

.tab-dropdown-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border: none;
  background: transparent;
  border-radius: 8px;
  color: #334155;
  cursor: pointer;
  font-size: 14px;
  white-space: nowrap;
}

.tab-dropdown-item:hover {
  background: #f1f5f9;
}

.tab-dropdown-item.active {
  background: #eff6ff;
  color: #1e88e5;
}

.tab-has-badge {
  overflow: visible;
}

.tab-experimental-badge {
  position: absolute;
  top: -6px;
  right: -4px;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #fef3c7;
  color: #d97706;
  font-weight: 600;
  line-height: 1.4;
  white-space: nowrap;
}

.strm-action {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.strm-panel {
  min-width: 0;
}

@media (max-width: 900px) {
  .strm-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .strm-action {
    justify-content: center;
  }

  .strm-action .btn {
    width: 100%;
    justify-content: center;
  }

  .path {
    max-width: none;
  }
}

@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .strm-tabs {
    flex-direction: column;
    gap: 2px;
  }

  .strm-tabs .tab-btn {
    justify-content: center;
    padding: 10px 16px;
  }
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stats-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.stats-content {
  min-width: 0;
}

.stats-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eef2ff;
  color: #4c74df;
}

.stats-icon.running {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

.stats-icon.paused {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}

.stats-icon.queued {
  background: rgba(249, 115, 22, 0.12);
  color: #f97316;
}

.stats-number {
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
}

.stats-label {
  font-size: 14px;
  color: #64748b;
}

.table-container {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  overflow-x: auto;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  -webkit-overflow-scrolling: touch;
}

.task-table-container {
  overflow: visible;
}

.data-table {
  width: 100%;
  min-width: 760px;
  border-collapse: collapse;
  table-layout: fixed;
}

.data-table th,
.data-table td {
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
  vertical-align: middle;
}

.data-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
}

.data-table th:nth-child(1),
.data-table td:nth-child(1) {
  width: 15%;
}

.data-table th:nth-child(2),
.data-table td:nth-child(2) {
  width: 28%;
}

.organize-table {
  min-width: 880px;
}

.organize-table th:nth-child(1),
.organize-table td:nth-child(1) {
  width: 18%;
}

.organize-table th:nth-child(2),
.organize-table td:nth-child(2) {
  width: 38%;
}

.organize-table th:nth-child(3),
.organize-table td:nth-child(3) {
  width: 9%;
}

.organize-table th:nth-child(4),
.organize-table td:nth-child(4) {
  width: 18%;
}

.organize-table th:nth-child(5),
.organize-table td:nth-child(5) {
  width: 17%;
}

.data-table th:last-child,
.data-table td:last-child {
  text-align: center;
}

.task-row {
  position: relative;
  transition: background-color 0.18s ease;
}

.task-row:hover {
  background: #fafcff;
  z-index: 30;
}

.action-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}

.interval-badge,
.mode-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 12px;
  background: #f1f5f9;
  color: #64748b;
}

.account-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 9999px;
  background: rgba(76, 116, 223, 0.12);
  color: #4c74df;
  font-weight: 600;
  font-size: 12px;
}

.path {
  max-width: 392px;
  color: #475569;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.organize-path {
  max-width: none;
}

.organize-account {
  max-width: 128px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #475569;
}

.organize-account-sub {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.2;
}

.mode-badge.compact {
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11px;
}

.organize-status-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.organize-status-text {
  min-width: 0;
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
}

.organize-status-primary {
  color: #334155;
  font-weight: 650;
  font-size: 13px;
  line-height: 1.2;
}

.organize-status-summary {
  max-width: 148px;
  color: #94a3b8;
  font-size: 11px;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.task-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.task-name .name {
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-inline-status {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 11px;
  flex-shrink: 0;
}

.task-inline-status.running {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

.task-inline-status.paused {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}

.last-scan-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #475569;
  white-space: nowrap;
  min-width: 0;
}

.last-scan-switch {
  display: grid;
  min-width: 0;
}

.scan-status-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.scan-status-icon svg {
  width: 16px;
  height: 16px;
}

.scan-status-icon.success {
  color: #10b981;
}

.scan-status-icon.error {
  color: #ef4444;
}

.scan-status-icon.pending {
  color: #94a3b8;
}

.scan-status-icon.queued {
  color: #f59e0b;
}

.scan-status-icon.scanning {
  color: #4c74df;
}

.scan-status-icon.scanning svg {
  animation: spin 1s linear infinite;
}

.last-scan-text,
.last-scan-summary {
  grid-area: 1 / 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity 0.18s ease;
  font-size: 13px;
}

.last-scan-text {
  color: #475569;
}

.last-scan-summary {
  color: #94a3b8;
  opacity: 0;
}

.last-scan-switch:hover .last-scan-summary {
  opacity: 1;
}

.last-scan-switch:hover .last-scan-text {
  opacity: 0;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.settings-group {
  background: white;
  border-radius: 12px;
  padding: 20px;
  border-left: 4px solid #4C74DF;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.group-title {
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.tmdb-test-btn {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  cursor: pointer;
  transition: all .15s;
}

.tmdb-test-btn:hover:not(:disabled) {
  background: #dbeafe;
  border-color: #93c5fd;
}

.tmdb-test-btn:disabled {
  opacity: .6;
  cursor: not-allowed;
}

.group-title i {
  margin-right: 12px;
  color: #4C74DF;
}

.group-item {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 20px;
  align-items: center;
  padding: 12px 0;
  position: relative;
}

.group-item:not(:last-child)::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 33.33%;
  height: 1px;
  background: linear-gradient(to right,
    #e2e8f0 0%,
    rgba(226, 232, 240, 0.8) 25%,
    rgba(226, 232, 240, 0.6) 50%,
    rgba(226, 232, 240, 0.4) 75%,
    transparent 100%
  );
}

.group-label {
  font-weight: 500;
  color: #4a5568;
}

.group-label.with-help {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.group-input {
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.group-input:focus {
  outline: none;
  border-color: #4C74DF;
  box-shadow: 0 0 0 2px rgba(76, 116, 223, 0.1);
}

.settings-select {
  width: 100%;
}

.setting-switch {
  display: inline-flex;
  align-items: center;
  width: 54px;
  height: 30px;
  cursor: pointer;
}

.setting-switch input {
  display: none;
}

.setting-switch span {
  position: relative;
  width: 54px;
  height: 30px;
  border-radius: 999px;
  background: #cbd5e1;
  transition: all 0.2s ease;
}

.setting-switch span::after {
  content: '';
  position: absolute;
  top: 4px;
  left: 4px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.18);
  transition: all 0.2s ease;
}

.setting-switch input:checked + span {
  background: linear-gradient(135deg, #4c74df, #02a6f0);
}

.setting-switch input:checked + span::after {
  transform: translateX(24px);
}

.replace-domain-actions {
  grid-template-columns: 1fr;
  justify-items: center;
}

.replace-domain-actions > button {
  justify-self: center;
}

.help-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: help;
}

.help-icon i {
  color: #94a3b8;
  font-size: 14px;
  transition: color 0.2s ease;
}

.help-icon:hover i {
  color: #4C74DF;
}

.tooltip {
  position: absolute;
  top: 50%;
  left: 25px;
  transform: translateY(-50%);
  z-index: 1000;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
  padding: 0;
  min-width: 380px;
  max-width: 480px;
  color: #2d3748;
  overflow: hidden;
}

.tooltip::before {
  content: '';
  position: absolute;
  top: 50%;
  left: -7px;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-top: 7px solid transparent;
  border-bottom: 7px solid transparent;
  border-right: 7px solid #e1e8ed;
}

.tooltip::after {
  content: '';
  position: absolute;
  top: 50%;
  left: -6px;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  border-right: 6px solid #ffffff;
}

.tooltip-content {
  padding: 0;
}

.tooltip-title {
  background: #f8fafc;
  color: #4C74DF;
  padding: 16px 20px;
  font-weight: 600;
  font-size: 15px;
  border-bottom: 1px solid #e2e8f0;
}

.tooltip-body {
  padding: 20px;
}

.tooltip-body p {
  margin: 0 0 16px 0;
  color: #475569;
  font-size: 14px;
  line-height: 1.6;
}

.tooltip-body p:last-child {
  margin-bottom: 0;
}

.task-action-btn {
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

.task-action-btn svg {
  width: 16px;
  height: 16px;
}

.task-action-btn i {
  font-size: 14px;
  line-height: 1;
}

.task-action-btn:hover {
  color: #334155;
  background: #f8fafc;
  border-color: #d8e0ea;
}

.task-action-btn.danger:hover {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.18);
  color: #ef4444;
}

.task-action-btn.force-stop {
  color: #ef4444;
}

.task-action-btn.force-stop:hover {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.18);
  color: #dc2626;
}

.task-action-btn.play:hover {
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(34, 197, 94, 0.18);
  color: #22c55e;
}

.task-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.run-menu-wrap {
  position: relative;
  display: inline-flex;
}

/* 填补按钮与下拉之间的空隙，避免移入子菜单时 hover 断开 */
.run-menu-wrap::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 100%;
  height: 14px;
  z-index: 24;
}

.run-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 12px);
  min-width: 104px;
  padding: 6px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
  opacity: 0;
  pointer-events: none;
  transform: translateY(-4px);
  transition: all 0.16s ease;
  z-index: 30;
}

.run-menu-wrap:hover .run-menu {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.run-menu button {
  width: 100%;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #475569;
  cursor: pointer;
  font-size: 13px;
  padding: 8px 10px;
  text-align: left;
}

.run-menu button:hover {
  background: #f1f5f9;
  color: #2563eb;
}

.task-status-switch {
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

.task-status-btn {
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

.task-status-btn:hover {
  color: #334155;
  background: #f8fafc;
}

.task-status-btn.active {
  background: #eef4ff;
  color: #2563eb;
}

.task-status-text {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
}

/* 对话框基础样式（与缓存保持一致） */
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

.branch-dialog {
  max-width: 900px;
  height: 560px;
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
  overflow: hidden;
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

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #374151;
  font-size: 14px;
}

.form-group label .label-hint {
  margin-left: 8px;
  font-weight: 400;
  color: #9ca3af;
  font-size: 12px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 0;
}

.advanced-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #94a3b8;
  cursor: pointer;
  user-select: none;
  transition: color 0.2s;
}

.advanced-toggle:hover {
  color: #3b82f6;
}

.advanced-toggle-icon {
  width: 16px;
  height: 16px;
  transition: transform 0.2s;
}

.advanced-toggle-icon.rotated {
  transform: rotate(180deg);
}

.form-switch-row {
  height: 40px;
  padding: 0 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  display: flex !important;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #475569;
  background: #fff;
  box-sizing: border-box;
}

.form-switch-row > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.form-help-text {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.4;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-group .btn {
  height: 40px;
  min-width: 72px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.input-group.integrated {
  gap: 0;
}

.input-group.integrated .form-input {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.browse-btn {
  min-width: 84px;
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  box-shadow: none;
}

.full-width {
  width: 100%;
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

/* ── 目录整理 ── */

.sub-tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 18px;
}

.sub-tab-btn {
  padding: 10px 20px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.sub-tab-btn:hover {
  color: #334155;
}

.sub-tab-btn.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}

.toggle-btn-group {
  display: flex;
  gap: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}
.toggle-btn {
  flex: 1;
  padding: 8px 16px;
  border: none;
  background: #f8fafc;
  color: #64748b;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.toggle-btn:hover {
  background: #e2e8f0;
}
.toggle-btn.active {
  background: linear-gradient(135deg, #4c74df, #02a6f0);
  color: #fff;
}

.organize-log-panel {
  margin-top: 14px;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #0f172a;
  overflow: hidden;
}

.organize-log-header {
  height: 42px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #111827;
  color: #e5e7eb;
  font-size: 14px;
}

.organize-log-header i {
  margin-right: 8px;
  color: #60a5fa;
}

.organize-log-header small {
  margin-left: 8px;
  color: #94a3b8;
}

.organize-log-body {
  height: 260px;
  padding: 10px 12px;
  overflow-y: auto;
  font-family: Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.65;
  color: #d1d5db;
}

.organize-log-line {
  white-space: pre-wrap;
  word-break: break-word;
}

.organize-log-time {
  color: #93c5fd;
  margin-right: 8px;
}

.organize-log-empty {
  color: #94a3b8;
  padding: 18px 0;
  text-align: center;
}

.organize-plan-dialog {
  width: 720px;
  max-width: 92vw;
  max-height: 86vh;
  display: flex;
  flex-direction: column;
}

.organize-plan-dialog .dialog-content {
  overflow-y: auto;
}

.organize-plan-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 48px 16px;
}

.organize-plan-loading-spinner i {
  font-size: 38px;
  color: #4f46e5;
}

.organize-plan-loading-title {
  font-size: 15px;
  color: #1e293b;
}

.organize-plan-loading-progress {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.organize-plan-loading-progress .metric {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: #f1f5f9;
  border-radius: 999px;
  color: #475569;
  font-size: 12px;
}

.organize-plan-loading-current {
  font-size: 12px;
  color: #64748b;
  max-width: 600px;
  text-align: center;
  word-break: break-all;
}

.organize-plan-tmdb-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  font-size: 13px;
  color: #9a3412;
}

.organize-plan-tmdb-banner > i {
  color: #ea580c;
}

.organize-plan-tmdb-banner > span {
  flex: 1;
}

.organize-plan-tmdb-test {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  color: #c2410c;
  background: #fff;
  border: 1px solid #fdba74;
  border-radius: 6px;
  cursor: pointer;
}

.organize-plan-tmdb-test:hover:not(:disabled) {
  background: #ffedd5;
}

.organize-plan-tmdb-test:disabled {
  opacity: .6;
  cursor: not-allowed;
}

.organize-plan-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 12px;
}

.summary-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  color: #475569;
  font-size: 12px;
}

.summary-pill.warning {
  border-color: #fed7aa;
  color: #c2410c;
  background: #fff7ed;
}

.organize-plan-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.organize-plan-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

.organize-plan-row.mkdir {
  background: #fefce8;
  border-color: #fde68a;
}

.organize-plan-icon {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eef2ff;
  color: #4f46e5;
  border-radius: 8px;
  font-size: 13px;
}

.organize-plan-icon.rename {
  background: #ecfeff;
  color: #0e7490;
}

.organize-plan-icon.move {
  background: #f0fdf4;
  color: #15803d;
}

.organize-plan-body {
  flex: 1;
  min-width: 0;
}

.organize-plan-title {
  font-size: 13px;
  color: #0f172a;
  word-break: break-all;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.organize-plan-arrow {
  color: #94a3b8;
  font-size: 11px;
}

.organize-plan-old {
  color: #475569;
}

.organize-plan-new {
  color: #0f172a;
  font-weight: 500;
}

.organize-plan-sub {
  margin-top: 3px;
  font-size: 12px;
  color: #64748b;
}

.organize-plan-skipped {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #e5e7eb;
}

.organize-plan-skipped-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #6b7280;
  cursor: pointer;
  user-select: none;
}

.organize-plan-skipped-title:hover {
  color: #c2410c;
}

.organize-plan-skipped-title > i {
  width: 10px;
  font-size: 10px;
}

.organize-plan-skipped-reasons-inline {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-left: 4px;
}

.organize-plan-skipped-reason-chip {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  font-size: 11px;
  color: #c2410c;
  background: #fff7ed;
  border-radius: 999px;
  line-height: 18px;
}

.organize-plan-skipped-body {
  margin-top: 6px;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
}

.organize-plan-skipped-reason-group {
  border-bottom: 1px dashed #f3f4f6;
}

.organize-plan-skipped-reason-group:last-child {
  border-bottom: 0;
}

.organize-plan-skipped-reason-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  cursor: pointer;
  user-select: none;
}

.organize-plan-skipped-reason-header:hover .organize-plan-skipped-reason-label {
  color: #c2410c;
}

.organize-plan-skipped-reason-header > i {
  width: 10px;
  font-size: 10px;
  color: #9ca3af;
}

.organize-plan-skipped-reason-label {
  font-size: 12px;
  color: #6b7280;
}

.organize-plan-skipped-reason-count {
  font-size: 11px;
  color: #9ca3af;
}

.organize-plan-skipped-reason-files {
  max-height: 280px;
  overflow-y: auto;
  padding: 2px 0 6px 18px;
}

.organize-plan-skipped-row {
  padding: 1px 0;
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.organize-plan-skipped-more {
  margin-top: 4px;
  font-size: 11px;
  color: #c2410c;
  cursor: pointer;
}

.organize-plan-skipped-more:hover {
  text-decoration: underline;
}

.organize-plan-group {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}

.organize-plan-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #f8fafc;
  cursor: pointer;
  font-size: 13px;
  color: #0f172a;
  position: relative;
}

.organize-plan-group-chevron {
  color: #64748b;
  width: 12px;
  flex-shrink: 0;
}

.organize-plan-group-title-wrap {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
}

.organize-plan-group-title {
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  max-width: 100%;
  white-space: nowrap;
}

.organize-plan-group-title .organize-plan-old {
  flex: 0 100 auto;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.organize-plan-group-title .organize-plan-new {
  flex: 0 1 auto;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.organize-plan-group-title .organize-plan-arrow {
  flex: 0 0 auto;
}

.organize-plan-group-title .organize-plan-old {
  color: #64748b;
  font-weight: 400;
}

.organize-plan-group-title .organize-plan-new {
  color: #0f172a;
}

.organize-plan-group-right {
  position: relative;
  flex-shrink: 0;
  min-width: 80px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
}

.organize-plan-group-badges {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: opacity 0.15s ease;
}

.organize-plan-group-controls {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  display: inline-flex;
  gap: 4px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}

.organize-plan-group-header:hover .organize-plan-group-badges,
.organize-plan-group.editing .organize-plan-group-badges {
  opacity: 0;
  pointer-events: none;
}

.organize-plan-group-header:hover .organize-plan-group-controls,
.organize-plan-group.editing .organize-plan-group-controls {
  opacity: 1;
  pointer-events: auto;
}

.organize-plan-group-tmdb {
  font-size: 12px;
  color: #4f46e5;
  background: #eef2ff;
  padding: 2px 8px;
  border-radius: 999px;
}

.organize-plan-group-notmdb {
  font-size: 12px;
  color: #c2410c;
  background: #fff7ed;
  padding: 2px 8px;
  border-radius: 999px;
}

.organize-plan-group-count {
  font-size: 12px;
  color: #64748b;
}

.organize-plan-group-body {
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.organize-plan-row {
  position: relative;
  transition: none;
}

.organize-plan-row-controls {
  margin-left: auto;
  display: inline-flex;
  gap: 4px;
  visibility: hidden;
}

.organize-plan-row:hover .organize-plan-row-controls,
.organize-plan-row.editing .organize-plan-row-controls {
  visibility: visible;
}

.organize-plan-row.edited .organize-plan-new {
  color: #1d4ed8;
  font-weight: 600;
}

.organize-plan-row.collapsed-range {
  background: #f8fafc;
  border-style: dashed;
}

.organize-plan-collapsed-label {
  font-size: 13px;
  color: #0f172a;
  font-weight: 500;
}

.organize-plan-old-mini,
.organize-plan-new-mini {
  font-size: 12px;
  color: #475569;
}

.plan-row-toggle {
  margin-left: 8px;
  font-size: 12px;
  color: #4f46e5;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

.plan-row-btn {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  color: #475569;
  cursor: pointer;
  font-size: 11px;
}

.plan-row-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.plan-row-btn.ok {
  color: #0f766e;
  border-color: #99f6e4;
  background: #ccfbf1;
}

.plan-row-btn.cancel {
  color: #b91c1c;
}

.plan-row-btn.danger {
  color: #b91c1c;
}

.organize-plan-edit {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.organize-plan-edit-source {
  font-size: 12px;
  color: #64748b;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.organize-plan-edit-input {
  flex: 1;
  min-width: 200px;
  padding: 5px 8px;
  border: 1px solid #94a3b8;
  border-radius: 6px;
  font-size: 13px;
}

.organize-plan-edit-input:focus {
  outline: none;
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79,70,229,0.15);
}

.branch-check-control {
  height: 40px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 42px;
  align-items: stretch;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.branch-check-control.enabled {
  border-color: #b8c8f3;
  box-shadow: 0 0 0 2px rgba(76, 116, 223, 0.08);
}

.branch-check-toggle,
.branch-check-edit {
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
}

.branch-check-toggle {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  text-align: left;
}

.branch-check-toggle:hover {
  background: #f8fafc;
}

.branch-check-dot {
  width: 28px;
  height: 16px;
  border-radius: 999px;
  background: #cbd5e1;
  position: relative;
  flex-shrink: 0;
  transition: background 0.2s ease;
}

.branch-check-dot::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.18);
  transition: transform 0.2s ease;
}

.branch-check-control.enabled .branch-check-dot {
  background: linear-gradient(135deg, #4c74df, #02a6f0);
}

.branch-check-control.enabled .branch-check-dot::after {
  transform: translateX(12px);
}

.branch-check-text {
  font-size: 14px;
  color: #334155;
  line-height: 1;
}

.branch-check-edit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-left: 1px solid #e5e7eb;
}

.branch-check-edit svg {
  width: 16px;
  height: 16px;
}

.branch-check-edit:hover:not(:disabled) {
  color: #2563eb;
  background: #f8fafc;
}

.branch-check-edit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.branch-dialog-content {
  gap: 14px;
  min-height: 0;
  height: 100%;
}

.branch-add-bar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) 112px auto;
  gap: 8px;
  align-items: center;
  padding: 8px 0 14px;
  border-bottom: 1px solid #edf2f7;
}

.branch-kind-toggle {
  display: inline-flex;
  height: 34px;
  padding: 2px;
  border: 1px solid #dbe4ef;
  border-radius: 7px;
  background: #fff;
}

.branch-kind-toggle button {
  border: none;
  border-radius: 5px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 13px;
  padding: 0 10px;
}

.branch-kind-toggle button.active {
  background: #edf4ff;
  color: #2563eb;
  font-weight: 600;
}

.branch-path-field {
  display: flex;
  gap: 0;
  min-width: 0;
}

.branch-path-field .form-input {
  min-width: 0;
}

.branch-path-field .browse-btn {
  flex-shrink: 0;
}

.branch-inline-check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  color: #475569;
  font-size: 13px;
}

.branch-retention {
  min-width: 104px;
}

.branch-columns {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
  flex: 1;
}

.branch-column {
  min-width: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 320px;
}

.branch-column-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 12px;
  border-bottom: 1px solid #e2e8f0;
  background: #fbfcfe;
  color: #334155;
  font-size: 14px;
  font-weight: 600;
}

.branch-column-head em,
.branch-expiry-summary {
  min-height: 22px;
  border-radius: 999px;
  background: #eef4ff;
  color: #2563eb;
  font-size: 12px;
  font-style: normal;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  max-width: 220px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.branch-expiry-summary.preview {
  max-width: min(100%, 360px);
  background: #ecfdf5;
  color: #047857;
}

.branch-list {
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow: auto;
  min-height: 0;
}

.branch-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 112px auto;
  gap: 8px;
  align-items: center;
  min-height: 38px;
  padding: 6px 9px;
  border-bottom: 1px solid #edf2f7;
  background: #fff;
}

.branch-row:last-child {
  border-bottom: none;
}

.branch-row.compact {
  grid-template-columns: minmax(0, 1fr) auto;
}

.branch-column:last-child .branch-row.compact {
  grid-template-columns: minmax(0, 1fr) 112px auto;
}

.branch-path {
  color: #334155;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.branch-empty {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 12px;
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
}

@media (max-width: 760px) {
  .branch-add-bar,
  .branch-columns,
  .branch-row {
    grid-template-columns: 1fr;
  }
}

.tag-editor-box {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 12px;
  min-height: 44px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  align-items: center;
  transition: border-color 0.2s;
}
.tag-editor-box:focus-within {
  border-color: #4C74DF;
  box-shadow: 0 0 0 2px rgba(76, 116, 223, 0.1);
}
.tag-placeholder {
  font-size: 13px;
  color: #94a3b8;
  pointer-events: none;
}
.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 6px;
  font-size: 13px;
  color: #3730a3;
  cursor: grab;
  user-select: none;
  transition: all 0.15s ease;
}
.tag-chip:active {
  cursor: grabbing;
}
.tag-chip.drag-over {
  border-color: #4C74DF;
  background: #ddd6fe;
  box-shadow: 0 0 0 2px rgba(76, 116, 223, 0.2);
}
.tag-chip-text {
  font-weight: 500;
}
.tag-chip-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  font-size: 12px;
  line-height: 1;
  color: #6366f1;
  cursor: pointer;
  transition: all 0.15s;
}
.tag-chip-remove:hover {
  background: #c7d2fe;
  color: #312e81;
}
.tag-pool {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.tag-chip-add {
  cursor: pointer;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  color: #64748b;
}
.tag-chip-add:hover {
  background: #eef2ff;
  border-color: #818cf8;
  color: #4f46e5;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  color: #cbd5e1;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: #94a3b8;
  margin-bottom: 4px;
}

</style>
