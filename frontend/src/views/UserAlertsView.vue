<template>
  <div class="portal user-portal">
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
          <h1>VideoWalker 预警中心</h1>
          <p>用户侧实时预警接收与处置</p>
        </div>
      </div>

      <div class="header-actions">
        <div class="primary-actions">
          <el-button class="btn-ghost" @click="router.push('/admin/dashboard')">进入管理端</el-button>
          <span class="action-divider" aria-hidden="true"></span>
          <el-button class="btn-primary" @click="refreshAlerts" :loading="loading">刷新数据</el-button>
        </div>
      </div>
    </header>

    <main class="portal-main">
      <AlertList class="panel panel-list" />
      <AlertDetail class="panel panel-detail" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import AlertList from '../components/AlertList.vue'
import AlertDetail from '../components/AlertDetail.vue'
import { useAlertStore } from '../stores/alertStore'

const router = useRouter()
const alertStore = useAlertStore()
const { loading } = storeToRefs(alertStore)

function refreshAlerts() {
  alertStore.fetchAlerts()
}

onMounted(() => {
  alertStore.fetchAlerts()
  alertStore.initWebSocket()
})

onUnmounted(() => {
  alertStore.cleanupWebSocket()
})
</script>

<style scoped>
.portal {
  min-height: 100vh;
  background: radial-gradient(circle at top right, #edf4ff 0%, #f3f7fc 52%, #edf3fb 100%);
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
  font-size: 16px;
  margin: 0;
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

.portal-main {
  height: calc(100vh - 60px);
  width: 100%;
  margin: 0;
  display: flex;
  align-items: stretch;
  gap: 20px;
  padding: 24px;
  box-sizing: border-box;
}

.panel-list {
  width: 320px;
  min-width: 320px;
  max-width: 320px;
  flex-shrink: 0;
}

.panel-detail {
  flex: 1;
  min-width: 0;
}

@media (max-width: 1060px) {
  .portal-main {
    display: flex;
    flex-direction: column;
    height: auto;
    min-height: calc(100vh - 60px);
  }

  .panel-list {
    width: 100%;
    min-width: 0;
    max-width: none;
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

  .portal-main {
    gap: 16px;
    padding: 16px;
  }
}
</style>
