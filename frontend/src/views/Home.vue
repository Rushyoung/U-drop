<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import Timeline from '../components/Timeline.vue';
import InputBar from '../components/InputBar.vue';
import MyShares from './MyShares.vue';
import TrashBin from './TrashBin.vue';
import StorageAssistant from './StorageAssistant.vue';
import AdminPanel from './AdminPanel.vue';
import Devices from './Devices.vue';
import client from '../api/client';
import { AuthService } from '../api/services';
import { useToast } from '../utils/toast';
import { 
  History, 
  Settings, 
  RotateCw,
  LogOut,
  UploadCloud,
  Share2,
  Menu,
  Search as SearchIcon,
  X as XIcon,
  Trash2,
  PieChart,
  ListChecks,
  MonitorSmartphone,
  ShieldCheck
} from 'lucide-vue-next';

import { useSettings } from '../utils/settings';
import { useUser } from '../utils/user';
import { useWebSocket } from '../hooks/useWebSocket';
import { useDropZone } from '@vueuse/core';
import { getToken, clearToken } from '../utils/auth';

const router = useRouter();
const { showToast } = useToast();
const { settings } = useSettings();
const { user, fetchUser } = useUser();
const { status: wsStatus, onMessage } = useWebSocket();
const timelineRef = ref<any>(null);
const inputBarRef = ref<any>(null);
const currentTab = ref('timeline');
const isMobileSidebarOpen = ref(false);

watch(currentTab, () => {
  isMobileSidebarOpen.value = false;
});
const latency = ref<number | null>(null);
const isRefreshing = ref(false);
const rotation = ref(0);
const searchQuery = ref('');
const isSearchOpen = ref(false);
const tempTrashDays = ref(30);
let latencyTimer: any = null;

watch(() => user.value?.trash_expire_days, (newVal) => {
  if (newVal !== undefined) tempTrashDays.value = newVal;
}, { immediate: true });

const updateTrashSettings = async (days: number) => {
  try {
    const res = await AuthService.updateSettings({ trash_expire_days: days });
    if (res.data.success) {
      showToast(`回收站清理周期已同步为 ${days} 天`, 'success');
      if (user.value) user.value.trash_expire_days = days;
    }
  } catch (err) {
    showToast('更新设置失败', 'error');
  }
};

// 拖拽上传逻辑
const dropZoneRef = ref<HTMLDivElement>();
const onDrop = (files: File[] | null) => {
  if (files && files.length > 0) {
    inputBarRef.value?.externalSetFiles(files);
    showToast(`准备上传 ${files.length} 个文件`, 'info');
  }
};
const { isOverDropZone } = useDropZone(dropZoneRef, onDrop);

const checkLatency = async () => {
  const start = performance.now();
  try {
    await client.get('/messages', { params: { limit: 1 } });
    latency.value = Math.round(performance.now() - start);
  } catch (err) {
    latency.value = null;
  }
};

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const quotaPercentage = computed(() => {
  if (!user.value) return 0;
  return Math.min(100, (user.value.used_storage / user.value.storage_quota) * 100);
});

onMounted(() => {
  fetchUser();
  checkLatency();
  latencyTimer = setInterval(checkLatency, 10000);

  // 监听业务变更事件以同步配额与设备信息
  onMessage((msg) => {
    if (msg.type === 'MSG_NEW' || msg.type === 'MSG_DELETE') {
      fetchUser();
    }
  });
});

onUnmounted(() => {
  if (latencyTimer) clearInterval(latencyTimer);
});

const refreshTimeline = async () => {
  if (isRefreshing.value) return;
  isRefreshing.value = true;
  fetchUser(); 
  
  rotation.value += 720; 
  
  const startTime = performance.now();
  await timelineRef.value?.loadMessages('initial', null);
  const endTime = performance.now();
  
  const elapsed = endTime - startTime;
  const minTime = 800;
  
  setTimeout(() => {
    isRefreshing.value = false;
  }, Math.max(0, minTime - elapsed));
};

const handleLogout = async () => {
  const token = getToken();
  if (!token) return;

  try {
    await AuthService.logout(token);
    showToast('已安全退出登录', 'success');
  } catch (err) {
    console.error('Logout request failed');
  } finally {
    clearToken();
    localStorage.removeItem('udrop_last_anchor_id');
    router.push('/login');
  }
};

const resetTheme = () => {
  settings.accentColor = '#00A3FF';
  settings.pitColor = '#4a9ecc';
  settings.cardColorStart = '#7fb2d5';
  settings.cardColorEnd = '#a4d8f0';
  settings.surroundColor = '#aed9f4';
  showToast('配色方案已重置', 'info');
};

const navItems = computed(() => {
  const items = [
    { id: 'timeline', icon: History, label: '时间线' },
    { id: 'shares', icon: Share2, label: '我的分享' },
    { id: 'trash', icon: Trash2, label: '回收站' },
    { id: 'devices', icon: MonitorSmartphone, label: '设备管理' },
    { id: 'storage', icon: PieChart, label: '存储分析' },
    { id: 'settings', icon: Settings, label: '设置' },
  ];
  
  if (user.value?.role === 'admin') {
    items.splice(5, 0, { id: 'manage', icon: ShieldCheck, label: '系统管理' });
  }
  
  return items;
});
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-[#aed9f4]" :style="{ backgroundColor: 'var(--surround-color)' }">
    <!-- Backdrop Overlay (Mobile only) -->
    <Transition
      enter-active-class="transition-opacity duration-300"
      enter-from-class="opacity-0"
      leave-active-class="transition-opacity duration-200"
      leave-to-class="opacity-0"
    >
      <div 
        v-if="isMobileSidebarOpen" 
        @click="isMobileSidebarOpen = false"
        class="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 md:hidden"
      ></div>
    </Transition>

    <!-- Sidebar -->
    <aside 
      :class="[
        'fixed inset-y-0 left-0 w-64 bg-[#bce4ff]/60 backdrop-blur-2xl border-r border-black/5 p-6 z-50 transition-transform duration-500 ease-spring md:static md:translate-x-0 flex flex-col',
        isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full'
      ]"
    >
      <div class="flex items-center justify-between mb-12">
        <div class="flex items-center space-x-3">
          <div class="w-10 h-10 bg-primary rounded-full flex items-center justify-center text-white font-bold shrink-0" :style="{ backgroundColor: 'var(--accent-color)' }">U</div>
          <div class="min-w-0">
            <h1 class="font-bold text-xl text-primary-dark tracking-tight truncate">U-Drop</h1>
            <p class="text-[10px] text-secondary font-mono uppercase tracking-widest truncate">Ethereal Precision</p>
          </div>
        </div>
        <!-- Close button (Mobile only) -->
        <button @click="isMobileSidebarOpen = false" class="md:hidden p-2 text-secondary hover:text-primary transition-colors">
          <XIcon class="w-5 h-5" />
        </button>
      </div>

      <nav class="flex-1 space-y-2 overflow-y-auto">
        <button 
          v-for="item in navItems" 
          :key="item.id"
          @click="currentTab = item.id"
          :class="[
            'w-full flex items-center space-x-3 px-4 py-3 rounded-global transition-all duration-300 ease-spring',
            currentTab === item.id ? 'bg-primary/10 text-primary shadow-ambient' : 'text-secondary hover:translate-x-1 hover:text-primary'
          ]"
          :style="currentTab === item.id ? { color: 'var(--accent-color)', backgroundColor: 'color-mix(in srgb, var(--accent-color) 10%, transparent)' } : {}"
        >
          <component :is="item.icon" class="w-5 h-5" />
          <span class="font-medium text-sm">{{ item.label }}</span>
        </button>
      </nav>

      <div class="mt-auto pt-6 space-y-6 shrink-0">
        <!-- Quota Progress Bar -->
        <div v-if="user" class="px-2 space-y-3">
          <div class="flex justify-between items-end">
            <div class="flex flex-col min-w-0">
              <span class="text-[10px] font-black text-secondary/70 uppercase tracking-widest truncate">Storage Used</span>
              <span class="text-xs font-bold text-primary-dark truncate">{{ formatBytes(user.used_storage) }} / {{ formatBytes(user.storage_quota) }}</span>
            </div>
            <span class="text-[10px] font-mono text-secondary/70 shrink-0">{{ Math.round(quotaPercentage) }}%</span>
          </div>
          <div class="h-1.5 w-full bg-black/5 rounded-full overflow-hidden shadow-inner border border-white/20">
            <div 
              class="h-full transition-all duration-1000 ease-spring"
              :style="{ 
                width: `${quotaPercentage}%`,
                backgroundColor: quotaPercentage > 90 ? '#ef4444' : quotaPercentage > 70 ? '#f97316' : 'var(--accent-color)',
                boxShadow: `0 0-10px ${quotaPercentage > 90 ? '#ef4444' : quotaPercentage > 70 ? '#f97316' : 'var(--accent-color)'}44`
              }"
            ></div>
          </div>
        </div>

        <button 
          @click="handleLogout"
          class="w-full flex items-center space-x-3 text-secondary px-4 py-3 hover:text-red-500 hover:bg-red-50 rounded-global transition-all active:scale-95"
        >
          <LogOut class="w-5 h-5" />
          <span class="text-sm font-medium">退出登录</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col relative bg-transparent min-w-0">
      <!-- Header Bar -->
      <header class="h-12 md:h-14 bg-[#bce4ff]/40 backdrop-blur-xl border-b border-black/5 shadow-sm flex items-center justify-between px-3 md:px-6 z-30 shrink-0">
        <div class="flex items-center space-x-2 md:space-x-3">
          <!-- Mobile Menu Button -->
          <button @click="isMobileSidebarOpen = true" class="md:hidden p-2 text-secondary hover:text-primary transition-colors">
            <Menu class="w-5 h-5" />
          </button>
          
          <div :class="[
            'w-1.5 h-1.5 md:w-2 md:h-2 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]',
            wsStatus === 'connected' ? 'bg-green-500 shadow-green-500/50' : (latency !== null ? 'bg-orange-400' : 'bg-red-500')
          ]"></div>
          <span class="text-[10px] md:text-xs font-mono text-secondary truncate max-w-[80px] md:max-w-none">
            {{ currentTab === 'settings' ? '系统配置' : (currentTab === 'manage' ? '管理后台' : (wsStatus === 'connected' ? '实时通信' : `延迟: ${latency !== null ? `${latency}ms` : '断开'}`)) }}
          </span>
        </div>

        <div class="flex items-center space-x-1 md:space-x-2">
          <!-- Morphing Search Bar -->
          <div v-if="currentTab === 'timeline'" class="flex items-center space-x-1 md:space-x-2">
            <div class="flex items-center">
              <div 
                :class="[
                  'flex items-center bg-black/5 rounded-full transition-all duration-500 ease-spring overflow-hidden',
                  isSearchOpen ? 'w-32 md:w-64 px-2 md:px-3 py-1 md:py-1.5' : 'w-8 h-8 md:w-9 md:h-9 justify-center'
                ]"
              >
                <SearchIcon 
                  @click="isSearchOpen = !isSearchOpen"
                  :class="['w-4 h-4 cursor-pointer transition-colors', isSearchOpen ? 'text-primary' : 'text-secondary/85 hover:text-primary']" 
                  :style="isSearchOpen ? { color: 'var(--accent-color)' } : {}"
                />
                <input 
                  v-if="isSearchOpen"
                  v-model="searchQuery"
                  type="text"
                  placeholder="搜索..."
                  class="flex-1 bg-transparent border-none outline-none text-[10px] md:text-xs ml-1 md:ml-2 text-on-surface placeholder:text-secondary/60 min-w-0"
                />
                <XIcon 
                  v-if="isSearchOpen && searchQuery" 
                  @click="searchQuery = ''" 
                  class="w-3 h-3 text-secondary/70 hover:text-red-500 cursor-pointer ml-1" 
                />
              </div>
            </div>

            <!-- Bulk Action Toggle (Middle) -->
            <button 
              @click="timelineRef?.toggleBulkMode()"
              :class="[
                'w-8 h-8 md:w-9 md:h-9 flex items-center justify-center rounded-full transition-all active:scale-90',
                timelineRef?.isBulkMode ? 'bg-primary text-white shadow-lg shadow-primary/20' : 'text-secondary/85 hover:bg-black/5'
              ]"
              :style="timelineRef?.isBulkMode ? { backgroundColor: 'var(--accent-color)' } : {}"
              title="批量管理"
            >
              <ListChecks class="w-4 h-4" />
            </button>

            <!-- Refresh Button (Right) -->
            <button 
              @click="refreshTimeline" 
              :disabled="isRefreshing"
              :style="{ transform: `rotate(${rotation}deg)`, color: 'var(--accent-color)' }"
              :class="[
                'transition-all duration-700 ease-spring flex items-center justify-center p-1.5 rounded-full',
                isRefreshing 
                  ? 'scale-125 bg-primary/20 shadow-[0_0_20px_rgba(0,163,255,0.4),_0_0_40px_rgba(0,163,255,0.1)]' 
                  : 'hover:bg-primary/5'
              ]"
            >
              <RotateCw class="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <!-- View Switcher -->
      <div v-if="currentTab === 'timeline'" ref="dropZoneRef" class="flex-1 flex flex-col min-h-0 overflow-hidden relative">
        <!-- Drag & Drop Overlay -->
        <Transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="opacity-0 scale-95"
          leave-active-class="transition duration-200 ease-in"
          leave-to-class="opacity-0 scale-105"
        >
          <div v-if="isOverDropZone" class="absolute inset-0 z-[100] m-4 bg-primary/20 backdrop-blur-md rounded-[20px] border-4 border-dashed border-primary/40 flex flex-col items-center justify-center space-y-4 pointer-events-none">
            <div class="p-6 bg-white rounded-full shadow-lg animate-bounce">
              <UploadCloud class="w-12 h-12 text-primary" :style="{ color: 'var(--accent-color)' }" />
            </div>
            <p class="text-xl font-bold text-primary-dark tracking-widest uppercase drop-shadow-sm">Release to Upload</p>
          </div>
        </Transition>

        <!-- 上部：时间线占据剩余空间 -->
        <Timeline ref="timelineRef" class="flex-1 min-h-0" :search-query="searchQuery" />
        
        <!-- 下部：输入框固定在底部，缩窄缓冲区 -->
        <div class="bg-transparent px-6 pb-4 pt-1 border-t border-black/5 z-40">
           <InputBar ref="inputBarRef" :timeline="timelineRef" @message-sent="refreshTimeline" />
        </div>
      </div>

      <div v-else-if="currentTab === 'shares'" class="flex-1 flex flex-col min-h-0 overflow-hidden">
        <MyShares />
      </div>

      <div v-else-if="currentTab === 'trash'" class="flex-1 flex flex-col min-h-0 overflow-hidden">
        <TrashBin />
      </div>

      <div v-else-if="currentTab === 'storage'" class="flex-1 flex flex-col min-h-0 overflow-hidden">
        <StorageAssistant />
      </div>

      <div v-else-if="currentTab === 'devices'" class="flex-1 flex flex-col min-h-0 overflow-hidden">
        <Devices />
      </div>

      <div v-else-if="currentTab === 'settings'" class="flex-1 overflow-y-auto p-12">
        <div class="max-w-2xl mx-auto space-y-12">
           <section>
             <h2 class="text-2xl font-bold text-on-surface mb-6">界面与体验偏好</h2>
             <div class="card-glass p-4 md:p-6 space-y-4 md:space-y-6">
                <div class="flex items-center justify-between">
                  <div class="pr-4">
                    <p class="text-sm md:text-base font-medium text-on-surface">自动滚动至底端</p>
                    <p class="text-[10px] md:text-xs text-secondary/85">发送消息或有新信令进入时，视图将自动锁定至最新位置</p>
                  </div>
                  <button 
                    @click="settings.autoScrollToBottom = !settings.autoScrollToBottom"
                    :class="['w-10 md:w-12 h-5 md:h-6 rounded-full transition-all relative shrink-0', settings.autoScrollToBottom ? 'bg-primary' : 'bg-secondary/20']"
                    :style="{ backgroundColor: settings.autoScrollToBottom ? 'var(--accent-color)' : '' }"
                  >
                    <div :class="['absolute top-0.5 md:top-1 w-4 h-4 bg-white rounded-full transition-all', settings.autoScrollToBottom ? 'left-5 md:left-7' : 'left-1']"></div>
                  </button>
                </div>

                <div class="pt-4 md:pt-6 border-t border-black/5">
                   <div class="flex items-center justify-between">
                      <div class="pr-4">
                        <p class="text-sm md:text-base font-medium text-on-surface">消息卡片圆角</p>
                        <p class="text-[10px] md:text-xs text-secondary/85">调整时间线消息气泡的圆润程度</p>
                      </div>
                      <div class="flex items-center space-x-2 md:space-x-4">
                         <input 
                            type="range" 
                            min="0" max="48" 
                            v-model.number="settings.messageBorderRadius" 
                            class="w-20 md:w-32 accent-primary"
                            :style="{ accentColor: 'var(--accent-color)' }"
                         />
                         <span class="text-xs md:text-sm font-bold text-primary min-w-[32px]" :style="{ color: 'var(--accent-color)' }">{{ settings.messageBorderRadius }}px</span>
                      </div>
                   </div>
                </div>
             </div>
           </section>

           <section>
             <h2 class="text-2xl font-bold text-on-surface mb-6">存储与会话管理</h2>
             <div class="card-glass p-4 md:p-6 space-y-6">
                <div v-if="user" class="flex items-center justify-between">
                   <div class="pr-2">
                     <p class="text-sm md:text-base font-medium text-on-surface">回收站清理周期</p>
                     <p class="text-[10px] md:text-xs text-secondary/85">消息在 {{ user.trash_expire_days }} 天后被抹除</p>
                   </div>
                   <div class="flex items-center space-x-2 md:space-x-4">
                      <input 
                         type="range" 
                         min="1" max="30" 
                         v-model.number="tempTrashDays" 
                         @change="updateTrashSettings(tempTrashDays)"
                         class="w-20 md:w-32 accent-primary"
                         :style="{ accentColor: 'var(--accent-color)' }"
                      />
                      <span class="text-xs md:text-sm font-bold text-primary min-w-[24px]" :style="{ color: 'var(--accent-color)' }">{{ tempTrashDays }}d</span>
                   </div>
                </div>

                <div v-if="user" class="pt-6 border-t border-black/5 space-y-6">
                   <div class="flex items-center justify-between">
                      <div class="pr-4">
                        <p class="text-sm md:text-base font-medium text-on-surface">临时会话寿命</p>
                        <p class="text-[10px] md:text-xs text-secondary/85">非记住我模式下的 Token 有效时长 (1-24h)</p>
                      </div>
                      <div class="flex items-center space-x-2 md:space-x-4">
                         <input 
                            type="range" 
                            min="1" max="24" 
                            v-model.number="user.temp_expire_hours" 
                            @change="AuthService.updateSettings({ temp_expire_hours: user.temp_expire_hours })"
                            class="w-20 md:w-32 accent-primary"
                            :style="{ accentColor: 'var(--accent-color)' }"
                         />
                         <span class="text-xs md:text-sm font-bold text-primary min-w-[24px]" :style="{ color: 'var(--accent-color)' }">{{ user.temp_expire_hours }}h</span>
                      </div>
                   </div>

                   <div class="pt-6 border-t border-black/5">
                      <div class="flex items-center justify-between">
                         <div class="pr-4">
                           <p class="text-sm md:text-base font-medium text-on-surface">长效续期天数</p>
                           <p class="text-[10px] md:text-xs text-secondary/85">开启记住我后，每次活动自动续期的时长 (1-365d)</p>
                         </div>
                         <div class="flex items-center space-x-2 md:space-x-4">
                            <input 
                               type="range" 
                               min="1" max="365" 
                               v-model.number="user.sliding_window_days" 
                               @change="AuthService.updateSettings({ sliding_window_days: user.sliding_window_days })"
                               class="w-20 md:w-32 accent-primary"
                               :style="{ accentColor: 'var(--accent-color)' }"
                            />
                            <span class="text-xs md:text-sm font-bold text-primary min-w-[24px]" :style="{ color: 'var(--accent-color)' }">{{ user.sliding_window_days }}d</span>
                         </div>
                      </div>
                   </div>
                </div>
             </div>
           </section>

           <section>
             <h2 class="text-2xl font-bold text-on-surface mb-6">主题配置</h2>
             <div class="card-glass p-6 space-y-8">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-8">
                  <!-- Accent Color -->
                  <div class="space-y-3">
                    <div class="flex justify-between items-center">
                      <label class="text-[10px] font-black uppercase tracking-[0.2em] text-secondary/85">强调色 (Accent)</label>
                      <span class="text-[10px] font-mono opacity-40">{{ settings.accentColor }}</span>
                    </div>
                    <div class="flex items-center space-x-4 p-2 bg-black/5 rounded-xl">
                      <input type="color" v-model="settings.accentColor" class="w-12 h-10 rounded-lg cursor-pointer border-none bg-transparent overflow-hidden" />
                      <div class="flex-1 h-2 rounded-full overflow-hidden bg-white/20">
                         <div class="h-full transition-all" :style="{ width: '100%', backgroundColor: settings.accentColor }"></div>
                      </div>
                    </div>
                  </div>

                  <!-- Surround Color -->
                  <div class="space-y-3">
                    <div class="flex justify-between items-center">
                      <label class="text-[10px] font-black uppercase tracking-[0.2em] text-secondary/85">环境基色 (Surround)</label>
                      <span class="text-[10px] font-mono opacity-40">{{ settings.surroundColor }}</span>
                    </div>
                    <div class="flex items-center space-x-4 p-2 bg-black/5 rounded-xl">
                      <input type="color" v-model="settings.surroundColor" class="w-12 h-10 rounded-lg cursor-pointer border-none bg-transparent overflow-hidden" />
                      <div class="flex-1 h-2 rounded-full overflow-hidden bg-white/20">
                         <div class="h-full transition-all" :style="{ width: '100%', backgroundColor: settings.surroundColor }"></div>
                      </div>
                    </div>
                  </div>

                  <!-- Pit Color -->
                  <div class="space-y-3">
                    <div class="flex justify-between items-center">
                      <label class="text-[10px] font-black uppercase tracking-[0.2em] text-secondary/85">盆地底色 (Pit)</label>
                      <span class="text-[10px] font-mono opacity-40">{{ settings.pitColor }}</span>
                    </div>
                    <div class="flex items-center space-x-4 p-2 bg-black/5 rounded-xl">
                      <input type="color" v-model="settings.pitColor" class="w-12 h-10 rounded-lg cursor-pointer border-none bg-transparent overflow-hidden" />
                      <div class="flex-1 h-2 rounded-full overflow-hidden bg-white/20">
                         <div class="h-full transition-all" :style="{ width: '100%', backgroundColor: settings.pitColor }"></div>
                      </div>
                    </div>
                  </div>

                  <!-- Card Gradient -->
                  <div class="space-y-3 md:col-span-2">
                    <label class="text-[10px] font-black uppercase tracking-[0.2em] text-secondary/85">卡片渐变 (Card Gradient)</label>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="flex items-center space-x-4 p-2 bg-black/5 rounded-xl">
                        <input type="color" v-model="settings.cardColorStart" class="w-10 h-10 rounded-lg cursor-pointer border-none bg-transparent overflow-hidden" />
                        <span class="text-[10px] font-mono opacity-60">起始</span>
                      </div>
                      <div class="flex items-center space-x-4 p-2 bg-black/5 rounded-xl">
                        <input type="color" v-model="settings.cardColorEnd" class="w-10 h-10 rounded-lg cursor-pointer border-none bg-transparent overflow-hidden" />
                        <span class="text-[10px] font-mono opacity-60">结束</span>
                      </div>
                    </div>
                    <div class="h-12 rounded-2xl mt-4 shadow-inner border border-white/10" 
                         :style="{ background: `linear-gradient(145deg, ${settings.cardColorStart}, ${settings.cardColorEnd})` }">
                    </div>
                  </div>
                </div>
                
                <div class="pt-6 border-t border-black/5 flex justify-between items-center">
                   <p class="text-[10px] text-secondary/70 font-mono tracking-tighter italic">* 配置将实时同步至本地持久化存储</p>
                   <button @click="resetTheme" class="px-4 py-2 text-[11px] font-black uppercase tracking-widest text-secondary hover:text-red-500 transition-all active:scale-95">
                     恢复 UI 默认配色
                   </button>
                </div>
             </div>
           </section>
        </div>
      </div>

      <div v-else-if="currentTab === 'manage'" class="flex-1 flex flex-col min-h-0 overflow-hidden">
        <AdminPanel />
      </div>
    </main>
  </div>
</template>
