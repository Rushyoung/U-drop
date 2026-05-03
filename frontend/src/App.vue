<script setup lang="ts">
import { onMounted, watchEffect, watch } from 'vue';
import { useRoute } from 'vue-router';
import ToastContainer from './components/atomic/ToastContainer.vue';
import ContextMenu from './components/atomic/ContextMenu.vue';
import GlobalConfirm from './components/atomic/GlobalConfirm.vue';
import { warmupWorker } from './utils/hash';
import { useSettings } from './utils/settings';
import { useWebSocket } from './hooks/useWebSocket';
import { getToken } from './utils/auth';

const { settings } = useSettings();
const route = useRoute();
const { connect, disconnect, onMessage } = useWebSocket();

onMounted(() => {
  warmupWorker();
  
  // 处理全局上传进度推送
  onMessage((msg) => {
    if (msg.type === 'UPLOAD_PROGRESS') {
      const { upload_id, received_size, total_size } = msg.data;
      // 注意：目前 UploadManager 使用 message_id 作为 Key。
      // 我们需要一种方法将 upload_id 映射回任务，或者让后端推送也包含 message_id。
      // 临时方案：如果是当前正在进行的上传，后端推送进度可以作为全局参考。
      console.log(`[WS] Upload Progress: ${upload_id} -> ${Math.round(received_size/total_size*100)}%`);
    }
  });
});

// 根据登录状态管理 WebSocket 连接
watch(() => route.name, (name) => {
  const isAuthPage = name === 'login' || name === 'register';
  if (!isAuthPage && getToken()) {
    connect();
  } else {
    disconnect();
  }
}, { immediate: true });

watchEffect(() => {
  const root = document.documentElement;
  const isAuthPage = route.name === 'login' || route.name === 'register';

  if (isAuthPage) {
    // Reset to hardcoded defaults for Login/Register pages
    root.style.setProperty('--accent-color', '#00A3FF');
    root.style.setProperty('--pit-bg', '#4a9ecc');
    root.style.setProperty('--card-start', '#7fb2d5');
    root.style.setProperty('--card-end', '#a4d8f0');
    root.style.setProperty('--surround-color', '#aed9f4');
    root.style.setProperty('--card-border', 'rgba(255, 255, 255, 0.3)');
  } else {
    // Apply user settings for Home and other authenticated views
    root.style.setProperty('--accent-color', settings.accentColor);
    root.style.setProperty('--pit-bg', settings.pitColor);
    root.style.setProperty('--card-start', settings.cardColorStart);
    root.style.setProperty('--card-end', settings.cardColorEnd);
    root.style.setProperty('--surround-color', settings.surroundColor);
    root.style.setProperty('--card-border', 'rgba(255, 255, 255, 0.3)');
  }
});
</script>

<template>
  <router-view />
  <ToastContainer />
  <ContextMenu />
  <GlobalConfirm />
</template>

<style>
/* Global styles if needed */
</style>
