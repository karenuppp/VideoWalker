import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Alert, AlertStats } from '../types/alert'
import { alertsApi } from '../api/alerts'
import { websocketService } from '../services/websocket'

export const useAlertStore = defineStore('alert', () => {
  const alerts = ref<Alert[]>([])
  const selectedAlert = ref<Alert | null>(null)
  const stats = ref<AlertStats>({
    total: 0,
    unread: 0,
    read: 0,
    resolved: 0,
    by_type: {}
  })
  const loading = ref(false)
  const error = ref<string | null>(null)
  const wsConnected = ref(false)

  const unreadCount = computed(() => stats.value.unread)

  async function fetchAlerts() {
    loading.value = true
    error.value = null
    try {
      alerts.value = await alertsApi.getAlerts({ limit: 100 })
      await fetchStats()
    } catch (e) {
      error.value = 'Failed to fetch alerts'
      console.error(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      stats.value = await alertsApi.getAlertStats()
    } catch (e) {
      console.error('Failed to fetch stats', e)
    }
  }

  async function selectAlert(alert: Alert) {
    selectedAlert.value = alert
    if (alert.status === 'unread') {
      await markAsRead(alert.id)
    }
  }

  async function markAsRead(id: number) {
    try {
      const updated = await alertsApi.updateAlertStatus(id, 'read')
      const index = alerts.value.findIndex(a => a.id === id)
      if (index !== -1) {
        alerts.value[index] = updated
      }
      await fetchStats()
    } catch (e) {
      console.error('Mark as read failed', e)
    }
  }

  async function markAsResolved(id: number) {
    try {
      const updated = await alertsApi.updateAlertStatus(id, 'resolved')
      const index = alerts.value.findIndex(a => a.id === id)
      if (index !== -1) {
        alerts.value[index] = updated
      }
      if (selectedAlert.value?.id === id) {
        selectedAlert.value = updated
      }
      await fetchStats()
    } catch (e) {
      console.error('Mark as resolved failed', e)
    }
  }

  async function deleteAlert(id: number) {
    try {
      await alertsApi.deleteAlert(id)
      alerts.value = alerts.value.filter(a => a.id !== id)
      if (selectedAlert.value?.id === id) {
        selectedAlert.value = null
      }
      await fetchStats()
    } catch (e) {
      console.error('Delete alert failed', e)
    }
  }

  function handleNewAlert(alert: Alert) {
    alerts.value.unshift(alert)
    fetchStats()
  }

  function handleAlertUpdate(update: { id: number; status: string }) {
    const index = alerts.value.findIndex(a => a.id === update.id)
    if (index !== -1) {
      alerts.value[index].status = update.status
    }
    if (selectedAlert.value?.id === update.id) {
      selectedAlert.value.status = update.status
    }
    fetchStats()
  }

  function handleStats(newStats: AlertStats) {
    stats.value = newStats
  }

  function initWebSocket() {
    websocketService.connect()
    wsConnected.value = websocketService.isConnected()

    websocketService.on('alert', handleNewAlert)
    websocketService.on('alert_update', handleAlertUpdate)
    websocketService.on('stats', handleStats)
  }

  function cleanupWebSocket() {
    websocketService.disconnect()
    websocketService.off('alert', handleNewAlert)
    websocketService.off('alert_update', handleAlertUpdate)
    websocketService.off('stats', handleStats)
  }

  return {
    alerts,
    selectedAlert,
    stats,
    loading,
    error,
    wsConnected,
    unreadCount,
    fetchAlerts,
    fetchStats,
    selectAlert,
    markAsRead,
    markAsResolved,
    deleteAlert,
    initWebSocket,
    cleanupWebSocket
  }
})
