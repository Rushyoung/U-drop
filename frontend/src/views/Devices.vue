<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { AuthService } from '../api/services';
import type { DeviceResponse } from '../types/api';
import { useToast } from '../utils/toast';
import { getDeviceId, getDeviceName, saveCustomDeviceName } from '../utils/device';
import { showConfirm } from '../utils/confirm';
import DotLoading from '../components/atomic/DotLoading.vue';
import { 
  Monitor, 
  Smartphone, 
  Laptop, 
  Trash2, 
  History,
  ShieldCheck,
  Loader2,
  RefreshCw,
  LogOut,
  Edit3
} from 'lucide-vue-next';

const devices = ref<DeviceResponse[]>([]);
const isLoading = ref(false);
const isRevoking = ref<string | null>(null);
const currentDeviceId = getDeviceId();
const { showToast } = useToast();

const sortedDevices = computed(() => {
  return [...devices.value].sort((a, b) => {
    if (a.device_id === currentDeviceId) return -1;
    if (b.device_id === currentDeviceId) return 1;
    return b.last_seen - a.last_seen;
  });
});

const currentDeviceInputName = ref(getDeviceName().replace(/\s\[.*\]$/, ''));
const isRenaming = ref(false);

const loadDevices = async () => {
  try {
    isLoading.value = true;
    const res = await AuthService.listDevices();
    if (res.data.success && res.data.data) {
      devices.value = res.data.data;
    }
  } catch (err) {
    showToast('获取设备列表失败', 'error');
  } finally {
    isLoading.value = false;
  }
};

const handleDeviceNameUpdate = async () => {
  if (!currentDeviceInputName.value.trim()) return;
  try {
    isRenaming.value = true;
    const baseName = currentDeviceInputName.value.trim();
    const shortId = getDeviceId().slice(0, 6);
    const fullName = `${baseName} [${shortId}]`;
    
    const res = await AuthService.updateDevice({ device_name: fullName });
    if (res.data.success) {
      showToast('设备名称已更新', 'success');
      saveCustomDeviceName(baseName);
      const current = devices.value.find(d => d.device_id === currentDeviceId);
      if (current) current.device_name = fullName;
    }
  } catch (err) {
    showToast('更新失败', 'error');
  } finally {
    isRenaming.value = false;
  }
};

const handleRevoke = async (device: DeviceResponse) => {
  const isCurrent = device.device_id === currentDeviceId;
  
  const confirmed = await showConfirm({
    title: isCurrent ? '退出登录' : '下线该设备',
    message: isCurrent 
        ? '确定要退出当前账号吗？'
        : `确定要强制下线设备 "${device.device_name || '未知设备'}" 吗？该设备将无法继续访问。`,
    isDanger: true,
    confirmText: isCurrent ? '退出登录' : '强制下线'
  });

  if (!confirmed) return;

  try {
    isRevoking.value = device.device_id;
    const res = await AuthService.revokeDevice(device.device_id);
    if (res.data.success) {
      showToast(isCurrent ? '已退出登录' : '设备已下线', 'success');
      if (isCurrent) {
          localStorage.removeItem('udrop_token');
          window.location.href = '/login';
      } else {
          devices.value = devices.value.filter(d => d.device_id !== device.device_id);
      }
    }
  } catch (err) {
    showToast('操作失败', 'error');
  } finally {
    isRevoking.value = null;
  }
};

const formatTime = (ts: number) => {
  const now = Math.floor(Date.now() / 1000);
  const diff = now - ts;
  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  return new Date(ts * 1000).toLocaleDateString();
};

const getDeviceIcon = (type: number) => {
  if (type === 1) return Smartphone;
  if (type === 2) return Laptop;
  return Monitor;
};

onMounted(loadDevices);
</script>

<template>
  <div class="flex-1 overflow-y-auto p-4 md:p-12 pb-32 bg-transparent">
    <div class="max-w-5xl mx-auto space-y-12">
      <!-- HEADER -->
      <header class="flex justify-between items-end">
        <div class="space-y-2">
          <div class="flex items-center space-x-2">
            <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span class="text-[10px] font-black text-secondary/70 uppercase tracking-[0.3em]">多端管控中心</span>
          </div>
          <h1 class="text-3xl md:text-4xl font-black text-primary-dark tracking-tighter uppercase">Device Mastery</h1>
          <p class="text-sm text-secondary/85 font-medium italic">实时监控与管理所有已授权的访问终端</p>
        </div>
        <button 
          @click="loadDevices" 
          :disabled="isLoading"
          class="p-4 rounded-3xl bg-white/50 hover:bg-white transition-all shadow-sm active:scale-95 disabled:opacity-50"
        >
          <RefreshCw class="w-6 h-6 text-primary" :class="{'animate-spin': isLoading}" />
        </button>
      </header>

      <!-- CONTENT -->
      <section class="space-y-6">
        <div v-if="isLoading" class="py-20 flex flex-col items-center justify-center space-y-4 card-glass shadow-sm">
           <DotLoading />
           <p class="text-[10px] font-black uppercase tracking-[0.2em] text-secondary/80 animate-pulse text-center">正在检索全网活跃终端状态...</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
           <div 
             v-for="device in sortedDevices" 
             :key="device.device_id"
             class="card-glass p-6 md:p-8 flex flex-col justify-between space-y-8 transition-all duration-500 hover:shadow-[0_0_30px_rgba(0,163,255,0.1)] hover:bg-white/50 border border-white/40"
             :class="{'ring-2 ring-primary/20 bg-white/60': device.device_id === currentDeviceId}"
           >
              <div class="space-y-6">
                <div class="flex items-start justify-between">
                   <div class="flex items-center space-x-4 min-w-0">
                      <div class="p-4 bg-primary/10 rounded-2xl shrink-0" :style="{ color: 'var(--accent-color)' }">
                         <component :is="getDeviceIcon(device.device_type)" class="w-6 h-6" />
                      </div>
                      <div class="min-w-0 space-y-1">
                         <div class="flex items-center space-x-2">
                            <h4 class="font-black text-primary-dark truncate text-lg uppercase tracking-tight">
                              {{ device.device_name?.replace(/\s\[.*\]$/, '') || '未知终端' }}
                            </h4>
                            <span v-if="device.device_id === currentDeviceId" class="text-[8px] font-black uppercase px-2 py-0.5 bg-primary text-white rounded-lg tracking-widest shadow-lg" :style="{backgroundColor: 'var(--accent-color)'}">
                               Current
                            </span>
                         </div>
                         <p class="text-[10px] font-mono font-bold text-secondary/60 uppercase tracking-tighter">
                            ID: {{ device.device_id.slice(0, 16).toUpperCase() }}...
                         </p>
                      </div>
                   </div>
                </div>

                <!-- Current Device Rename Section -->
                <div v-if="device.device_id === currentDeviceId" class="p-4 rounded-2xl bg-black/5 border border-white/10 space-y-3">
                   <div class="flex items-center justify-between">
                      <span class="text-[9px] font-black text-secondary/60 uppercase tracking-widest flex items-center">
                         <Edit3 class="w-3 h-3 mr-1.5" /> 修改设备名称
                      </span>
                   </div>
                   <div class="flex flex-col xs:flex-row items-stretch xs:items-center gap-3">
                      <input 
                        v-model="currentDeviceInputName"
                        type="text"
                        placeholder="输入新名称..."
                        class="flex-1 bg-white/50 border-2 border-transparent rounded-xl px-4 py-2 text-xs font-bold outline-none focus:border-primary/30 focus:bg-white transition-all min-w-0"
                      />
                      <button 
                        @click="handleDeviceNameUpdate"
                        :disabled="isRenaming || !currentDeviceInputName.trim()"
                        class="px-4 py-2 bg-primary text-white rounded-xl font-bold text-[10px] uppercase tracking-widest hover:scale-105 active:scale-95 disabled:opacity-30 transition-all shadow-md shrink-0 flex items-center justify-center space-x-2"
                        :style="{ backgroundColor: 'var(--accent-color)' }"
                      >
                        <Loader2 v-if="isRenaming" class="w-3.5 h-3.5 animate-spin" />
                        <span v-else>更新</span>
                      </button>
                   </div>
                </div>
              </div>

              <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between pt-6 border-t border-black/5 gap-4">
                 <div class="flex items-center space-x-4">
                    <div class="flex flex-col">
                       <span class="text-[9px] font-black text-secondary/60 uppercase tracking-widest flex items-center">
                          <History class="w-3 h-3 mr-1.5" /> 最后在线
                       </span>
                       <span class="text-xs font-bold text-on-surface">{{ formatTime(device.last_seen) }}</span>
                    </div>
                 </div>
                 
                 <button 
                   @click="handleRevoke(device)"
                   :disabled="isRevoking === device.device_id"
                   class="p-3 rounded-xl transition-all flex items-center space-x-2 group/btn w-full sm:w-auto justify-center"
                   :class="[
                      device.device_id === currentDeviceId 
                        ? 'bg-black/5 text-secondary/70 hover:bg-black/10' 
                        : 'bg-red-50 text-red-500 hover:bg-red-500 hover:text-white shadow-sm'
                   ]"
                 >
                    <Loader2 v-if="isRevoking === device.device_id" class="w-4 h-4 animate-spin" />
                    <template v-else>
                       <LogOut v-if="device.device_id === currentDeviceId" class="w-4 h-4" />
                       <Trash2 v-else class="w-4 h-4 transition-transform group-hover/btn:scale-110" />
                       <span class="text-[10px] font-black uppercase tracking-widest">{{ device.device_id === currentDeviceId ? '登出' : '下线' }}</span>
                    </template>
                 </button>
              </div>
           </div>
        </div>
      </section>

      <!-- SECURITY FOOTER -->
      <section class="card-glass p-8 md:p-12 border-dashed border-primary/20 bg-primary/[0.02]">
         <div class="max-w-2xl space-y-4">
            <div class="flex items-center space-x-3 text-primary" :style="{ color: 'var(--accent-color)' }">
               <ShieldCheck class="w-6 h-6" />
               <h3 class="text-lg font-black uppercase tracking-widest">安全审计说明</h3>
            </div>
            <p class="text-sm text-secondary/85 leading-relaxed font-medium">
               U-Drop 采用设备绑定的会话机制。如果您在列表中发现异常终端，请立即执行“下线”操作。该终端的所有访问票据将被立即作废。
            </p>
         </div>
      </section>
    </div>
  </div>
</template>
