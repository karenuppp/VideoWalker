<template>
  <div class="alert-detail">
    <div v-if="selectedAlert" class="detail-container">
      <div class="detail-header">
        <h3>告警详情</h3>
        <div class="header-actions">
          <el-button
            v-if="selectedAlert.status !== 'resolved'"
            @click="handleMarkResolved"
            class="btn-primary"
          >
            标记为已解决
          </el-button>
          <el-button @click="handleDelete" class="btn-ghost danger">
            删除
          </el-button>
        </div>
      </div>

      <div class="detail-content">
        <div class="image-section">
          <div class="image-container">
            <img
              :src="getImageUrl(selectedAlert.image_path)"
              :alt="selectedAlert.alert_type"
              @error="handleImageError"
            />
            <div class="image-status" :class="selectedAlert.status">
              {{ getStatusLabel(selectedAlert.status) }}
            </div>
          </div>
        </div>

        <div class="info-section">
          <div class="info-card">
            <h4>告警信息</h4>
            <div class="info-row">
              <span class="label">类型:</span>
              <span class="value">{{ getAlertTypeLabel(selectedAlert) }}</span>
            </div>
            <div class="info-row">
              <span class="label">检测时间:</span>
              <span class="value">{{ formatDateTime(selectedAlert.detected_at) }}</span>
            </div>
            <div class="info-row" v-if="selectedAlert.confidence">
              <span class="label">置信度:</span>
              <span class="value">{{ (selectedAlert.confidence * 100).toFixed(1) }}%</span>
            </div>
            <div class="info-row" v-if="selectedAlert.description">
              <span class="label">描述:</span>
              <span class="value">{{ selectedAlert.description }}</span>
            </div>
          </div>

          <div class="info-card">
            <h4>摄像头信息</h4>
            <div class="info-row">
              <span class="label">名称:</span>
              <span class="value">{{ selectedAlert.camera?.name || `摄像头${selectedAlert.camera_id}` }}</span>
            </div>
            <div class="info-row" v-if="selectedAlert.camera?.location">
              <span class="label">位置:</span>
              <span class="value">{{ selectedAlert.camera.location }}</span>
            </div>
            <div class="info-row">
              <span class="label">状态:</span>
              <span class="value" :class="selectedAlert.camera?.status">
                {{ getCameraStatusLabel(selectedAlert.camera?.status) }}
              </span>
            </div>
            <div class="info-row" v-if="selectedAlert.camera?.last_frame_time">
              <span class="label">最近抽帧:</span>
              <span class="value">{{ formatDateTime(selectedAlert.camera.last_frame_time) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <svg viewBox="0 0 72 72" fill="none">
        <rect x="10" y="14" width="52" height="36" rx="6" stroke="currentColor" stroke-width="2" />
        <path d="M10 23h52" stroke="currentColor" stroke-width="1.6" opacity="0.58" />
        <circle cx="36" cy="35" r="8" stroke="currentColor" stroke-width="2" />
      </svg>
      <p>请选择一条告警查看详情</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useAlertStore } from '../stores/alertStore'

const alertStore = useAlertStore()
const { selectedAlert } = storeToRefs(alertStore)

function handleMarkResolved() {
  if (selectedAlert.value) {
    alertStore.markAsResolved(selectedAlert.value.id)
  }
}

function handleDelete() {
  if (selectedAlert.value && confirm('确定删除该告警吗？')) {
    alertStore.deleteAlert(selectedAlert.value.id)
  }
}

function getImageUrl(path: string): string {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  const normalized = path.replace(/\\/g, '/')

  if (normalized.startsWith('storage/frames/')) {
    return `/storage/${normalized.slice('storage/frames/'.length)}`
  }
  if (normalized.startsWith('/storage/frames/')) {
    return `/storage/${normalized.slice('/storage/frames/'.length)}`
  }

  if (normalized.startsWith('/storage/')) return normalized
  if (normalized.startsWith('storage/')) return `/${normalized}`
  if (normalized.startsWith('./storage/')) return normalized.replace('./', '/')

  const storageIndex = normalized.toLowerCase().indexOf('/storage/')
  if (storageIndex >= 0) {
    return normalized.slice(storageIndex)
  }

  if (normalized.startsWith('/')) return `/storage${normalized}`
  return `/storage/${normalized}`
}

function handleImageError(event: Event) {
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml,' + encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
      <rect width="400" height="300" fill="#f5f5f5"/>
      <text x="200" y="150" text-anchor="middle" fill="#999" font-size="16">图片加载失败</text>
    </svg>
  `)
}

function getAlertTypeLabel(alert: any): string {
  if (alert?.scene_name) return alert.scene_name
  const labels: Record<string, string> = {
    banner: '拉横幅',
    lying_down: '躺地',
    other: '其他'
  }
  return labels[alert?.alert_type] || alert?.alert_type || ''
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    unread: '未读',
    read: '已读',
    resolved: '已解决'
  }
  return labels[status] || status
}

function getCameraStatusLabel(status?: string): string {
  const labels: Record<string, string> = {
    active: '在线',
    inactive: '离线',
    error: '异常'
  }
  return labels[status || ''] || status || 'Unknown'
}

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<style scoped>
.alert-detail {
  display: flex;
  width: 100%;
  min-width: 0;
  height: 100%;
  background: transparent;
  overflow: hidden;
  min-height: 0;
}

.detail-container {
  display: flex;
  flex-direction: column;
  padding: 20px;
  width: 100%;
  height: 100%;
  margin: 0;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #d7e3f3;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 0 0 14px;
  border-bottom: 1px solid #e6edf7;
}

.detail-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
  letter-spacing: 0.2px;
}

.header-actions {
  display: flex;
  gap: 10px;
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

.btn-ghost.danger {
  border-color: #e25d68;
  color: #d84b57;
}

.btn-ghost.danger:hover {
  background: #fff0f1;
  border-color: #e25d68;
  color: #d84b57;
}

.detail-content {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 320px);
  gap: 18px;
}

.image-section {
  background: #f8fbff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid #e1eaf7;
}

.image-container {
  position: relative;
  width: 100%;
  min-height: 420px;
  background: #f1f5fb;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dde7f5;
}

.image-container img {
  max-width: 100%;
  max-height: 640px;
  object-fit: contain;
}

.image-status {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.image-status.unread {
  background: rgba(22, 119, 255, 0.9);
}

.image-status.read {
  background: rgba(77, 140, 252, 0.9);
}

.image-status.resolved {
  background: rgba(45, 174, 98, 0.9);
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.info-card {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid #dce7f6;
}

.info-card h4 {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e8eff8;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 8px 0;
  border-bottom: 1px solid #f1f5fa;
  gap: 12px;
}

.info-row:last-child {
  border-bottom: none;
}

.info-row .label {
  color: #64748b;
  font-size: 13px;
}

.info-row .value {
  color: #0f172a;
  font-size: 13px;
  font-weight: 600;
  text-align: right;
  max-width: 65%;
  word-break: break-word;
}

.info-row .value.active {
  color: #2dae62;
}

.info-row .value.inactive {
  color: #7c8798;
}

.info-row .value.error {
  color: #e34d59;
}

.empty-state {
  flex: 1;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #8ea0b7;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #d7e3f3;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
  gap: 12px;
}

.empty-state svg {
  width: 72px;
  height: 72px;
}

.empty-state p {
  margin: 0;
  font-size: 13px;
  color: #8c98ab;
}

@media (max-width: 1024px) {
  .detail-content {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .info-section {
    order: -1;
  }

  .detail-container {
    padding: 16px;
  }
}
</style>
