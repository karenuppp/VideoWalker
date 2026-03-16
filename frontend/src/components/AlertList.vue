<template>
  <div class="alert-list">
    <div class="alert-list-header">
      <h2>告警列表</h2>
      <div class="stats">
        <span class="stat-item unread">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="12" r="10" />
          </svg>
          未读: {{ unreadCount }}
        </span>
        <span class="stat-item total">总计: {{ stats.total }}</span>
      </div>
    </div>

    <div class="alert-list-content" v-if="!loading">
      <div
        v-for="alert in alerts"
        :key="alert.id"
        :class="['alert-item', { active: selectedAlert?.id === alert.id, unread: alert.status === 'unread' }]"
        @click="handleSelectAlert(alert)"
      >
        <div class="alert-item-right">
          <div class="alert-item-header">
            <span class="alert-type-tag">
              {{ getAlertTypeLabel(alert) }}
            </span>
            <span class="alert-time">{{ formatTime(alert.detected_at) }}</span>
          </div>
          <div class="alert-item-body">
            <div class="alert-camera">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                <circle cx="12" cy="13" r="4"></circle>
              </svg>
              <span>{{ alert.camera?.name || `摄像头${alert.camera_id}` }}</span>
            </div>
            <div class="alert-description" v-if="alert.description">
              {{ alert.description }}
            </div>
            <div class="alert-confidence" v-if="alert.confidence">
              置信度: {{ (alert.confidence * 100).toFixed(1) }}%
            </div>
          </div>
        </div>
        <div class="alert-item-status" :class="alert.status">
          {{ getStatusLabel(alert.status) }}
        </div>
      </div>

      <div v-if="alerts.length === 0" class="empty-state">
        <svg viewBox="0 0 72 72" fill="none">
          <rect x="9" y="16" width="54" height="40" rx="7" stroke="currentColor" stroke-width="2" />
          <circle cx="36" cy="36" r="9" stroke="currentColor" stroke-width="2" />
          <path d="M9 25h54" stroke="currentColor" stroke-width="1.6" opacity="0.6" />
        </svg>
        <p>暂无告警数据</p>
      </div>
    </div>

    <div class="loading-state" v-else>
      <div class="spinner"></div>
      <p>加载告警列表...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia'
import { useAlertStore } from '../stores/alertStore'

const alertStore = useAlertStore()
const { alerts, selectedAlert, stats, loading, unreadCount } = storeToRefs(alertStore)

function handleSelectAlert(alert: any) {
  alertStore.selectAlert(alert)
}

function getAlertTypeLabel(alert: any): string {
  if (alert?.scene_name) return alert.scene_name
  return getSceneName(alert?.alert_type || '')
}

function getSceneName(type: string): string {
  const labels: Record<string, string> = {
    banner: '拉横幅',
    lying_down: '躺地',
    other: '其他'
  }
  return labels[type] || type
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    unread: '未读',
    read: '已读',
    resolved: '已解决'
  }
  return labels[status] || status
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`

  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.alert-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-radius: 16px;
  border: 1px solid #d7e3f3;
  min-height: 0;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.alert-list-header {
  padding: 20px 28px 14px;
  border-bottom: 1px solid #e6edf7;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.alert-list-header h2 {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin: 0 0 10px;
  letter-spacing: 0.2px;
}

.stats {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.stat-item {
  font-size: 12px;
  color: #627089;
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-item.unread {
  color: #1677ff;
  font-weight: 600;
}

.stat-item.unread svg {
  width: 10px;
  height: 10px;
}

.alert-list-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 10px 12px 14px;
}

.alert-item {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: start;
  gap: 10px;
  padding: 14px 14px;
  border-radius: 12px;
  margin: 8px 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.alert-item:hover {
  background: #f8fbff;
  border-color: #d8e6fa;
}

.alert-item.active {
  background: #eef5ff;
  border-color: #c4dbff;
}

.alert-item.unread {
  background: #f5f9ff;
}

.alert-item-right {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.alert-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 7px;
  gap: 8px;
}

.alert-type-tag {
  font-size: 11px;
  font-weight: 600;
  color: #111111;
  background: #ff4d4f;
  padding: 3px 8px;
  border-radius: 999px;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.alert-time {
  font-size: 11px;
  color: #8c95a3;
  flex-shrink: 0;
}

.alert-item-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.alert-camera {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #5c6676;
}

.alert-camera svg {
  flex-shrink: 0;
  color: #93a0b2;
}

.alert-camera span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alert-description {
  font-size: 12px;
  color: #445066;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.alert-confidence {
  font-size: 11px;
  color: #748196;
}

.alert-item-status {
  justify-self: end;
  align-self: start;
  font-size: 10px;
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.alert-item-status.unread {
  background: #eaf3ff;
  color: #1677ff;
  border: 1px solid #bdd7ff;
}

.alert-item-status.read {
  background: #eff7ff;
  color: #1f7bf7;
  border: 1px solid #c9defe;
}

.alert-item-status.resolved {
  background: #f1fbf3;
  color: #2dae62;
  border: 1px solid #bbe9c5;
}

.empty-state {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #8ea0b7;
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

.loading-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #999;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #1677ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
