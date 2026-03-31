<template>
  <div class="portal admin-portal">
    <header class="portal-header">
      <div class="brand">
        <span class="brand-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <rect x="3" y="5" width="18" height="14" rx="3" stroke="currentColor" stroke-width="1.8" />
            <circle cx="12" cy="12" r="3.2" stroke="currentColor" stroke-width="1.8" />
            <path d="M3 9h18" stroke="currentColor" stroke-width="1.2" opacity="0.65" />
          </svg>
        </span>
        <div>
          <h1>VideoWalker 管理台</h1>
          <p>摄像头管理与识别场景管理</p>
        </div>
      </div>

      <div class="header-actions">
        <div class="primary-actions">
          <el-button class="btn-ghost" @click="router.push('/user/alerts')">返回用户端</el-button>
          <span class="action-divider" aria-hidden="true"></span>
          <el-button class="btn-primary" @click="refreshAll" :loading="loadingAll">刷新数据</el-button>
        </div>
      </div>
    </header>

    <main class="admin-main">
      <el-tabs v-model="activeTab" class="main-tabs">
        <el-tab-pane label="摄像头管理" name="camera">
          <el-card class="module-card" shadow="never">
            <template #header>
              <div class="module-header">摄像头管理</div>
            </template>

            <el-form :model="cameraForm" label-width="92px" size="small" @submit.prevent class="camera-form-grid">
              <el-form-item label="摄像头编号" class="line-input">
                <el-input v-model="cameraForm.camera_id" placeholder="CAM001" />
              </el-form-item>
              <el-form-item label="摄像头名称" class="line-input">
                <el-input v-model="cameraForm.name" placeholder="东门球机" />
              </el-form-item>
              <el-form-item label="RTSP地址" class="line-input rtsp-field">
                <el-input v-model="cameraForm.rtsp_url" placeholder="rtsp://..." />
              </el-form-item>
              <el-form-item class="camera-submit">
                <el-button class="btn-primary" @click="createCamera">新增摄像头</el-button>
              </el-form-item>
            </el-form>

            <el-table :data="cameras" size="small" height="340" class="data-table">
              <el-table-column prop="camera_id" label="摄像头编号" min-width="130" />
              <el-table-column prop="name" label="摄像头名称" min-width="140" />
              <el-table-column prop="rtsp_url" label="RTSP地址" min-width="220" show-overflow-tooltip />
              <el-table-column label="状态" width="82">
                <template #default="scope">
                  <span :class="['status-pill', scope.row.enabled ? 'status-online' : 'status-offline']">
                    {{ scope.row.enabled ? '在线' : '离线' }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="scope">
                  <el-button class="btn-ghost mini danger" @click="deleteCamera(scope.row.id)">删除</el-button>
                </template>
              </el-table-column>
              <template #empty>
                <div class="table-empty">
                  <svg viewBox="0 0 64 64" fill="none">
                    <rect x="7" y="16" width="50" height="34" rx="6" stroke="currentColor" stroke-width="2" />
                    <circle cx="32" cy="33" r="8" stroke="currentColor" stroke-width="2" />
                    <path d="M12 24h40" stroke="currentColor" stroke-width="1.6" opacity="0.55" />
                  </svg>
                  <p>暂无数据，点击新增开始配置</p>
                </div>
              </template>
            </el-table>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="识别场景管理" name="scene">
          <el-card class="module-card" shadow="never">
            <template #header>
              <div class="module-header">识别场景管理</div>
            </template>

            <el-form :model="sceneForm" label-width="86px" size="small" @submit.prevent class="scene-form">
              <el-form-item label="摄像头" class="line-input">
                <el-select v-model="sceneForm.camera_id" placeholder="选择已新增的摄像头">
                  <el-option
                    v-for="camera in cameras"
                    :key="camera.id"
                    :label="`${camera.name}（${camera.camera_id}）`"
                    :value="camera.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="场景名称" class="line-input">
                <el-input v-model="sceneForm.name" placeholder="如：拉横幅检测" />
              </el-form-item>
              <el-form-item label="场景描述" class="line-input">
                <el-input v-model="sceneForm.description" placeholder="简要说明识别目标" />
              </el-form-item>
              <el-form-item label="抽帧频率" class="line-input">
                <el-input-number v-model="sceneForm.frame_interval_seconds" :min="1" :max="3600" />
              </el-form-item>
              <el-form-item label="模型名称" class="line-input">
                <el-select
                  v-model="sceneForm.model_name"
                  filterable
                  allow-create
                  default-first-option
                  placeholder="选择已启动的模型服务"
                >
                  <el-option v-for="model in availableModels" :key="model" :label="model" :value="model" />
                </el-select>
              </el-form-item>
              <el-form-item label="识别API" class="line-input">
                <el-input v-model="sceneForm.detect_api" placeholder="输入模型API地址" />
              </el-form-item>
              <el-form-item>
                <el-button class="btn-primary" @click="saveScene">新增场景</el-button>
              </el-form-item>
            </el-form>

            <el-table :data="scenes" size="small" height="360" class="data-table">
              <el-table-column prop="camera_name" label="摄像头" min-width="110" />
              <el-table-column prop="name" label="场景名称" min-width="110" />
              <el-table-column prop="description" label="场景描述" min-width="140" show-overflow-tooltip />
              <el-table-column prop="frame_interval_seconds" label="抽帧频率(s)" width="120" />
              <el-table-column prop="model_name" label="模型" width="120" show-overflow-tooltip />
              <el-table-column prop="detect_api" label="识别API" min-width="220" show-overflow-tooltip />
              <el-table-column label="启用目标数量统计" width="150">
                <template #default="scope">
                  <el-switch
                    :model-value="getCountDraft(scope.row).enabled"
                    @change="setCountEnabled(scope.row, $event)"
                  />
                </template>
              </el-table-column>
              <el-table-column label="目标数量预警阈值" width="150">
                <template #default="scope">
                  <el-input
                    class="count-threshold-input"
                    type="number"
                    inputmode="numeric"
                    :model-value="String(getCountDraft(scope.row).threshold)"
                    :disabled="!getCountDraft(scope.row).enabled"
                    placeholder="阈值"
                    @input="setCountThreshold(scope.row, $event)"
                  />
                </template>
              </el-table-column>
              <el-table-column label="启用" width="86">
                <template #default="scope">
                  <span :class="['status-pill', scope.row.enabled ? 'status-online' : 'status-offline']">
                    {{ scope.row.enabled ? '启用' : '停用' }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="180">
                <template #default="scope">
                  <el-button class="btn-ghost mini" @click="applyCountRule(scope.row)">更新</el-button>
                  <el-button class="btn-ghost mini" @click="toggleSceneEnabled(scope.row)">
                    {{ scope.row.enabled ? '停用' : '启用' }}
                  </el-button>
                  <el-button class="btn-ghost mini danger" @click="deleteScene(scope.row.id)">删除</el-button>
                </template>
              </el-table-column>
              <template #empty>
                <div class="table-empty">
                  <svg viewBox="0 0 64 64" fill="none">
                    <rect x="10" y="10" width="44" height="44" rx="6" stroke="currentColor" stroke-width="2" />
                    <path d="M18 24h28M18 33h28M18 42h16" stroke="currentColor" stroke-width="2" />
                  </svg>
                  <p>暂无数据，点击新增开始配置</p>
                </div>
              </template>
            </el-table>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { adminApi } from '../api/admin'
import type { AdminCamera, SceneItem } from '../types/admin'

const router = useRouter()

const activeTab = ref('camera')
const loadingAll = ref(false)
const cameras = ref<AdminCamera[]>([])
const scenes = ref<SceneItem[]>([])
const availableModels = ref<string[]>([])
type CountDraft = { enabled: boolean; threshold: number }
const countDrafts = ref<Record<number, CountDraft>>({})

function loadCountDrafts(): Record<number, CountDraft> {
  try {
    const raw = localStorage.getItem('vw_scene_count_drafts')
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    if (typeof parsed !== 'object' || !parsed) return {}
    // Normalize string keys back to numbers (JSON.stringify converts number keys to strings)
    const normalized: Record<number, CountDraft> = {}
    for (const [k, v] of Object.entries(parsed)) {
      const numKey = Number(k)
      if (!isNaN(numKey)) normalized[numKey] = v as CountDraft
    }
    return normalized
  } catch (error) {
    console.error('Load count drafts failed', error)
    return {}
  }
}

function saveCountDrafts(next: Record<number, CountDraft>) {
  try {
    localStorage.setItem('vw_scene_count_drafts', JSON.stringify(next))
  } catch (error) {
    console.error('Save count drafts failed', error)
  }
}

const cameraForm = reactive({
  camera_id: '',
  name: '',
  rtsp_url: '',
})

const sceneForm = reactive({
  camera_id: undefined as number | undefined,
  name: '',
  description: '',
  frame_interval_seconds: 30,
  model_name: '',
  detect_api: '',
})

function resetSceneForm() {
  sceneForm.camera_id = undefined
  sceneForm.name = ''
  sceneForm.description = ''
  sceneForm.frame_interval_seconds = 30
  sceneForm.model_name = ''
  sceneForm.detect_api = ''
}

async function refreshAll() {
  loadingAll.value = true
  try {
    const [cameraData, sceneData] = await Promise.all([adminApi.listCameras(), adminApi.listScenes()])
    cameras.value = cameraData
    scenes.value = sceneData
    const storedDrafts = loadCountDrafts()
    const nextDrafts: Record<number, CountDraft> = {}
    for (const scene of sceneData) {
      const stored = storedDrafts[scene.id]
      if (stored) {
        // localStorage has user-modified draft — always preserve it
        nextDrafts[scene.id] = stored
        continue
      }
      // No localStorage entry — initialize from backend
      const enabled = scene.rule?.type === 'count'
      const threshold = scene.rule?.threshold && scene.rule.threshold > 0 ? scene.rule.threshold : 1
      nextDrafts[scene.id] = { enabled, threshold }
    }
    countDrafts.value = nextDrafts
    saveCountDrafts(nextDrafts)

    try {
      availableModels.value = await adminApi.listModels(sceneForm.detect_api)
    } catch (modelError) {
      console.error(modelError)
      availableModels.value = []
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('管理台数据加载失败')
  } finally {
    loadingAll.value = false
  }
}

async function createCamera() {
  if (!cameraForm.camera_id || !cameraForm.name || !cameraForm.rtsp_url) {
    ElMessage.warning('请填写完整摄像头信息')
    return
  }

  try {
    await adminApi.createCamera({ ...cameraForm, enabled: true })
    ElMessage.success('摄像头创建成功')
    cameraForm.camera_id = ''
    cameraForm.name = ''
    cameraForm.rtsp_url = ''
    await refreshAll()
  } catch (error) {
    console.error(error)
    ElMessage.error('摄像头创建失败')
  }
}

async function deleteCamera(cameraId: number) {
  try {
    await adminApi.deleteCamera(cameraId)
    ElMessage.success('摄像头已删除')
    await refreshAll()
  } catch (error) {
    console.error(error)
    ElMessage.error('删除摄像头失败')
  }
}

async function saveScene() {
  if (!sceneForm.camera_id || !sceneForm.name || !sceneForm.detect_api || !sceneForm.model_name) {
    ElMessage.warning('请先选择摄像头并填写场景名称、模型名称与识别API')
    return
  }

  try {
    await adminApi.createScene({
      camera_id: sceneForm.camera_id,
      name: sceneForm.name,
      description: sceneForm.description,
      detect_api: sceneForm.detect_api,
      frame_interval_seconds: sceneForm.frame_interval_seconds,
      model_name: sceneForm.model_name,
    })
    ElMessage.success('场景创建成功')
    resetSceneForm()
    await refreshAll()
  } catch (error) {
    console.error(error)
    ElMessage.error('场景保存失败')
  }
}

async function deleteScene(sceneId: number) {
  try {
    await adminApi.deleteScene(sceneId)
    ElMessage.success('场景已删除')
    await refreshAll()
  } catch (error) {
    console.error(error)
    ElMessage.error('删除场景失败')
  }
}

async function toggleSceneEnabled(scene: SceneItem) {
  try {
    await adminApi.updateScene(scene.id, { enabled: !scene.enabled })
    ElMessage.success(`场景已${scene.enabled ? '停用' : '启用'}`)
    await refreshAll()
  } catch (error) {
    console.error(error)
    ElMessage.error('更新场景状态失败')
  }
}

function getCountDraft(scene: SceneItem) {
  const existing = countDrafts.value[scene.id]
  if (existing) return existing
  const enabled = scene.rule?.type === 'count'
  const threshold = scene.rule?.threshold && scene.rule.threshold > 0 ? scene.rule.threshold : 1
  const draft = { enabled, threshold }
  countDrafts.value[scene.id] = draft
  saveCountDrafts(countDrafts.value)
  return draft
}

function setCountEnabled(scene: SceneItem, enabled: boolean) {
  const draft = getCountDraft(scene)
  draft.enabled = enabled
  countDrafts.value[scene.id] = { ...draft }
  saveCountDrafts(countDrafts.value)
}

function setCountThreshold(scene: SceneItem, value: string | number | undefined) {
  const draft = getCountDraft(scene)
  const numeric = typeof value === 'string' ? Number(value) : value
  const threshold = numeric && numeric > 0 ? numeric : 1
  draft.threshold = threshold
  countDrafts.value[scene.id] = { ...draft }
  saveCountDrafts(countDrafts.value)
}

async function applyCountRule(scene: SceneItem) {
  const draft = countDrafts.value[scene.id]
  const enabled = draft?.enabled ?? false
  const threshold = draft?.threshold && draft.threshold > 0 ? draft.threshold : 1
  const rule = enabled
    ? {
        type: 'count',
        target: 'any',
        op: '>=',
        threshold,
      }
    : {
        type: 'presence',
        target: 'any',
        op: '>=',
        threshold: 1,
      }
  try {
    await adminApi.updateScene(scene.id, { rule })
    // API success → update localStorage with current draft values
    countDrafts.value[scene.id] = { enabled, threshold }
    saveCountDrafts(countDrafts.value)
    ElMessage.success('目标数量统计已更新')
  } catch (error) {
    console.error(error)
    ElMessage.error('模型不支持启用目标数量统计')
  }
}

onMounted(async () => {
  await refreshAll()
})
</script>

<style scoped>
.portal {
  width: 100%;
  min-height: 100vh;
  box-sizing: border-box;
  background: linear-gradient(180deg, #f4f8ff 0%, #edf3fb 100%);
}

.portal-header {
  min-height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px 20px;
  padding: 10px 24px;
  border-bottom: 1px solid rgba(183, 204, 235, 0.7);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 12;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-icon {
  width: 20px;
  height: 20px;
  color: #2f5fbc;
  display: inline-flex;
}

.brand h1 {
  margin: 0;
  font-size: 16px;
  line-height: 1;
  color: #1f2a3d;
}

.brand p {
  margin: 2px 0 0;
  font-size: 11px;
  color: #6f7f95;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.primary-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-divider {
  width: 1px;
  height: 18px;
  background: #cfd9e8;
}

.admin-main {
  width: 100%;
  box-sizing: border-box;
  padding: 24px;
}

.main-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.main-tabs :deep(.el-tabs__item) {
  font-weight: 600;
}

.module-card {
  border: 1px solid #d7e3f3;
  border-radius: 16px;
}

.module-card :deep(.el-card__header) {
  padding: 20px 28px 10px;
  border-bottom: none;
}

.module-card :deep(.el-card__body) {
  padding: 16px 28px 28px;
}

.module-header {
  font-weight: 600;
  color: #1f2937;
  letter-spacing: 0.2px;
}

.camera-form-grid {
  display: grid;
  grid-template-columns: 0.9fr 1fr 1.7fr auto;
  gap: 16px 18px;
  align-items: center;
}

.camera-form-grid :deep(.rtsp-field .el-form-item__content) {
  margin-left: 12px;
}

.count-threshold-input :deep(.el-input__wrapper) {
  min-width: 120px;
}

.camera-form-grid :deep(.el-form-item) {
  margin-bottom: 0;
}

.camera-submit {
  margin-bottom: 0;
}

.camera-submit :deep(.el-form-item__content) {
  min-height: 32px;
  align-items: center;
}

.scene-form {
  margin-top: 18px;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 0.9fr 0.9fr 1.2fr auto;
  gap: 14px 18px;
  align-items: center;
}

.scene-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.btn-primary,
.btn-ghost {
  border-radius: 999px;
  padding: 0 16px;
  height: 32px;
}

.btn-primary {
  background: #1677ff;
  border: 1px solid #1677ff;
  color: #fff;
}

.btn-primary:hover {
  background: #0f62d6;
  border-color: #0f62d6;
  color: #fff;
}

.btn-ghost {
  background: transparent;
  border: 1px solid #1677ff;
  color: #1677ff;
}

.btn-ghost:hover {
  background: #eaf3ff;
  border-color: #1677ff;
  color: #0f62d6;
}

.btn-ghost.mini {
  height: 24px;
  padding: 0 10px;
  font-size: 12px;
}

.btn-ghost.mini.danger {
  border-color: #e25d68;
  color: #d84b57;
}

.btn-ghost.mini.danger:hover {
  background: #fff0f1;
}

.line-input :deep(.el-input__wrapper),
.line-select :deep(.el-select__wrapper) {
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  border-bottom: 1px solid #c6d6ee;
  padding-left: 0;
  padding-right: 0;
  background-image: linear-gradient(#1677ff, #1677ff);
  background-repeat: no-repeat;
  background-position: 0 100%;
  background-size: 0 2px;
  transition: background-size 0.5s ease, border-color 0.5s ease;
}

.line-input :deep(.el-input__wrapper.is-focus),
.line-select :deep(.el-select__wrapper.is-focused) {
  border-bottom-color: transparent;
  background-size: 100% 2px;
}

:deep(.el-input-number) {
  width: 148px;
  border-bottom: 1px solid #c6d6ee;
  border-radius: 0;
}

:deep(.el-input-number__decrease),
:deep(.el-input-number__increase) {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid #c7d7ef;
  background: #fff;
  top: 50%;
  transform: translateY(-50%);
  transition: transform 0.2s ease, background-color 0.2s ease;
  box-shadow: none;
}

:deep(.el-input-number__decrease:hover),
:deep(.el-input-number__increase:hover) {
  background: #eaf3ff;
  transform: translateY(-50%) scale(1.08);
}

:deep(.el-input-number__decrease) {
  left: 8px;
}

:deep(.el-input-number__increase) {
  right: 8px;
}

:deep(.el-input-number .el-input__inner) {
  padding-left: 36px;
  padding-right: 36px;
  border: none;
  background: transparent;
  box-shadow: none;
}

:deep(.el-input-number:not(.is-disabled):hover),
:deep(.el-input-number.is-focused) {
  border-color: #1677ff;
}

:deep(.el-input-number.is-focused .el-input__inner) {
  color: #1f2a3d;
}

.data-table {
  margin-top: 12px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.status-online {
  color: #fff;
  background: #2bae66;
}

.status-offline {
  color: #5d6472;
  background: #e5e9f0;
}

.table-empty {
  min-height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #8a99ad;
}

.table-empty svg {
  width: 64px;
  height: 64px;
}

.table-empty p {
  margin: 0;
  font-size: 13px;
  color: #8c98ab;
}

@media (max-width: 1200px) {
  .camera-form-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .camera-submit {
    grid-column: 1 / -1;
  }

  .scene-form {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .scene-form :deep(.el-form-item:last-child) {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .portal-header {
    padding: 10px 16px;
    align-items: flex-start;
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .admin-main {
    padding: 16px;
  }

  .camera-form-grid {
    grid-template-columns: 1fr;
  }

  .scene-form {
    grid-template-columns: 1fr;
  }

  .module-card :deep(.el-card__header) {
    padding: 18px 20px 8px;
  }

  .module-card :deep(.el-card__body) {
    padding: 8px 20px 20px;
  }
}
</style>
