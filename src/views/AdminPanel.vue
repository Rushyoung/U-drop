<script setup>
import { ref, onMounted, computed } from 'vue';
import { 
  Users, 
  Settings as SettingsIcon, 
  Database, 
  ShieldAlert,
  Loader2,
  HardDrive,
  Activity,
  AlertTriangle,
  UserMinus,
  Edit3,
  X,
  UserCheck,
  UserX,
  Lock,
  Copy
} from 'lucide-vue-next';
import { ManageService } from '../api/services';
import { useToast } from '../utils/toast';
import { clearToken } from '../utils/auth';
import { useContextMenu } from '../utils/contextMenu';
import { showConfirm } from '../utils/confirm';
import DotLoading from '../components/atomic/DotLoading.vue';

const { showToast } = useToast();
const { openMenu } = useContextMenu();

const isLoading = ref(false);
const users = ref([]);
const systemSettings = ref({});
const isSaving = ref(false);

const sortedUsers = computed(() => {
  return [...users.value].sort((a, b) => {
    if (a.role === 'admin' && b.role !== 'admin') return -1;
    if (a.role !== 'admin' && b.role === 'admin') return 1;
    return a.account.localeCompare(b.account);
  });
});

const loadData = async () => {
  try {
    isLoading.value = true;
    const [usersRes, settingsRes] = await Promise.all([
      ManageService.listUsers(),
      ManageService.getSettings()
    ]);
    
    if (usersRes.data.success) users.value = usersRes.data.data || [];
    if (settingsRes.data.success) systemSettings.value = settingsRes.data.data || {};
  } catch (err) {
    showToast('获取管理数据失败', 'error');
  } finally {
    isLoading.value = false;
  }
};

const handleUpdateSettings = async () => {
  try {
    isSaving.value = true;
    const res = await ManageService.updateSettings({
      allow_registration: systemSettings.value.allow_registration,
      auth_rate_limit: systemSettings.value.auth_rate_limit,
      default_token_expire: systemSettings.value.default_token_expire
    });
    if (res.data.success) {
      showToast('设置已保存', 'success');
    }
  } catch (err) {
    showToast('保存失败', 'error');
  } finally {
    isSaving.value = false;
  }
};

const handleCopyUuid = (uuid) => {
  navigator.clipboard.writeText(uuid);
  showToast('UUID 已复制', 'success');
};

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

onMounted(loadData);

const editingQuotaUuid = ref(null);
const tempQuotaGB = ref(5);
const isUpdatingQuota = ref(false);

const startEditQuota = (u) => {
  editingQuotaUuid.value = u.uuid;
  tempQuotaGB.value = Number((u.storage_quota / (1024 * 1024 * 1024)).toFixed(2));
};

const handleQuotaUpdate = async () => {
  if (!editingQuotaUuid.value) return;
  try {
    isUpdatingQuota.value = true;
    const bytes = Math.round(tempQuotaGB.value * 1024 * 1024 * 1024);
    const res = await ManageService.updateUserQuota(editingQuotaUuid.value, { storage_quota: bytes });
    if (res.data.success) {
      showToast('配额已更新', 'success');
      loadData();
      editingQuotaUuid.value = null;
    }
  } catch (err) {
    showToast('更新配额失败', 'error');
  } finally {
    isUpdatingQuota.value = false;
  }
};

const isDeletingUser = ref(null);
const handleDeleteAccount = async (u) => {
  if (u.role === 'admin') {
    showToast('禁止删除管理员账号', 'error');
    return;
  }

  const confirmed = await showConfirm({
    title: '删除账户',
    message: `确定要彻底删除账户 "${u.account}" 吗？此操作将立即踢出该用户并抹除其所有附件！`,
    isDanger: true,
    confirmText: '立即彻底删除'
  });
  
  if (!confirmed) return;

  try {
    isDeletingUser.value = u.uuid;
    const res = await ManageService.deleteUser(u.uuid);
    if (res.data.success) {
      showToast('账户已删除', 'success');
      loadData();
    }
  } catch (err) {
    showToast('删除失败', 'error');
  } finally {
    isDeletingUser.value = null;
  }
};

const handleToggleUserStatus = async (u) => {
  if (u.role === 'admin') {
    showToast('禁止操作管理员状态', 'error');
    return;
  }
  
  const newStatus = !u.is_active;
  const actionName = newStatus ? '启用' : '禁用';
  
  const confirmed = await showConfirm({
    title: `${actionName}账户`,
    message: `确定要 ${actionName} 账户 "${u.account}" 吗？${newStatus ? '' : '禁用后该用户将立即断开连接。'}`,
    isDanger: !newStatus,
    confirmText: actionName
  });
  
  if (!confirmed) return;

  try {
    const res = await ManageService.updateUserStatus(u.uuid, { is_active: newStatus });
    if (res.data.success) {
      showToast(`账户已${actionName}`, 'success');
      loadData();
    }
  } catch (err) {
    showToast(`${actionName}失败`, 'error');
  }
};

const openUserMenu = (e, u) => {
  const options = [
    {
      label: '修改配额',
      icon: Edit3,
      action: () => startEditQuota(u)
    }
  ];

  if (u.role !== 'admin') {
    options.push({
      label: u.is_active ? '禁用账户' : '启用账户',
      icon: u.is_active ? UserX : UserCheck,
      danger: u.is_active,
      action: () => handleToggleUserStatus(u)
    });

    options.push({
      label: '删除账户',
      icon: UserMinus,
      danger: true,
      action: () => handleDeleteAccount(u)
    });
  }

  openMenu(e, options);
};

const confirmReset = ref(false);
const adminPassword = ref('');
const isResetting = ref(false);

const handleFactoryReset = async () => {
  if (!adminPassword.value) return;
  try {
    isResetting.value = true;
    const res = await ManageService.factoryReset({ admin_password: adminPassword.value });
    if (res.data.success) {
      showToast('系统已重置，正在进入初始化向导', 'success');
      clearToken();
      localStorage.removeItem('udrop_last_anchor_id');
      setTimeout(() => {
        window.location.href = '/'; 
      }, 2000);
    }
  } catch (err) {
    showToast(err.response?.data?.message || '重置失败', 'error');
  } finally {
    isResetting.value = false;
    confirmReset.value = false;
  }
};
</script>

<template>
  <div class="flex-1 overflow-y-auto p-4 md:p-12 pb-24 md:pb-12 bg-transparent">
    <div class="max-w-5xl mx-auto space-y-12 md:space-y-16">
      
      <!-- PAGE HEADER -->
      <header class="flex items-center justify-between">
        <div>
          <div class="flex items-center space-x-2 mb-1">
            <div class="w-2 h-2 rounded-full bg-primary animate-pulse" :style="{ backgroundColor: 'var(--accent-color)' }"></div>
            <span class="text-[10px] font-black text-secondary/70 uppercase tracking-[0.3em]">管理员模式</span>
          </div>
          <h1 class="text-3xl md:text-4xl font-black text-primary-dark tracking-tighter uppercase">系统管理中心</h1>
        </div>
        <div class="hidden md:flex items-center space-x-4">
            <div class="px-4 py-2 bg-white/40 backdrop-blur-md rounded-2xl border border-white/20 shadow-ambient flex items-center space-x-3">
                <Activity class="w-4 h-4 text-primary" :style="{ color: 'var(--accent-color)' }" />
                <div class="flex flex-col">
                    <span class="text-[8px] font-black text-secondary/70 uppercase">系统状态</span>
                    <span class="text-[10px] font-bold text-primary-dark uppercase tracking-widest">正常运行</span>
                </div>
            </div>
        </div>
      </header>

      <!-- SECTION 1: USER AUDIT & CORE STATS -->
      <section class="space-y-6">
        <div class="flex items-center justify-between px-1">
            <div class="flex items-center space-x-3">
                <div class="p-2 bg-primary/10 rounded-xl" :style="{ color: 'var(--accent-color)' }">
                    <Users class="w-5 h-5" />
                </div>
                <h2 class="text-lg font-black uppercase tracking-widest text-primary-dark">用户管理</h2>
            </div>
            <span class="text-[10px] font-mono text-secondary/70">总计: {{ sortedUsers.length }} 个账号</span>
        </div>

        <div class="card-glass p-0 overflow-hidden shadow-key min-h-[200px] flex flex-col">
            <div v-if="isLoading" class="flex-1 flex flex-col items-center justify-center py-20 space-y-4">
                <DotLoading />
                <p class="text-[10px] font-black uppercase tracking-[0.2em] text-secondary/70 animate-pulse">正在同步云端用户...</p>
            </div>
            <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-black/5">
                <div 
                    v-for="u in sortedUsers" 
                    :key="u.uuid" 
                    :class="[
                        'p-6 transition-all group relative cursor-default hover:bg-white/60 hover:shadow-[0_0_25px_rgba(0,163,255,0.08)] hover:border-primary/20',
                        u.is_active ? '' : 'bg-black/5 opacity-80'
                    ]"
                    @contextmenu.prevent="openUserMenu($event, u)"
                >
                    <!-- Deleting Overlay -->
                    <div v-if="isDeletingUser === u.uuid" class="absolute inset-0 z-20 bg-red-500/10 backdrop-blur-sm flex items-center justify-center">
                        <Loader2 class="w-6 h-6 text-red-500 animate-spin" />
                    </div>

                    <div class="flex justify-between items-start mb-4">
                        <div class="min-w-0">
                            <div class="flex items-center space-x-2">
                                <p :class="['text-base font-black truncate', u.is_active ? 'text-on-surface' : 'text-secondary/50']">{{ u.account }}</p>
                                <Lock v-if="!u.is_active" class="w-3.5 h-3.5 text-red-500/50" />
                            </div>
                            <div 
                                @click="handleCopyUuid(u.uuid)"
                                class="flex items-center space-x-1.5 cursor-pointer group/uuid hover:text-primary transition-colors mt-0.5"
                            >
                                <p class="text-[10px] md:text-[11px] font-mono font-bold text-secondary/70 uppercase tracking-tighter">{{ u.uuid }}</p>
                                <Copy class="w-2.5 h-3 opacity-0 group-hover/uuid:opacity-100 transition-opacity" />
                            </div>
                        </div>
                        <div class="flex flex-col items-end space-y-1">
                            <span :class="[
                                'text-[9px] font-black uppercase px-2.5 py-1 rounded-lg shadow-sm', 
                                u.role === 'admin' ? 'bg-primary text-white' : 'bg-black/5 text-secondary/60'
                            ]" :style="u.role === 'admin' ? { backgroundColor: 'var(--accent-color)' } : {}">
                                {{ u.role === 'admin' ? '管理员' : '普通用户' }}
                            </span>
                            <span v-if="!u.is_active" class="text-[8px] font-black text-red-500 uppercase tracking-widest bg-red-50 px-1.5 py-0.5 rounded border border-red-100">已禁用</span>
                        </div>
                    </div>
                    
                    <div class="space-y-4">
                        <!-- Quota Section -->
                        <div class="space-y-2">
                            <div class="flex justify-between items-center text-[11px] md:text-xs font-black text-secondary/60 uppercase italic">
                                <span>存储配额</span>
                                <span class="text-[8px] md:text-[9px] opacity-20 font-mono">右键管理</span>
                            </div>

                            <!-- In-place Quota Editor -->
                            <div v-if="editingQuotaUuid === u.uuid" class="p-3 bg-white/60 rounded-2xl border border-primary/20 space-y-3 animate-in fade-in zoom-in-95 duration-300">
                                <div class="flex items-center space-x-2">
                                  <input 
                                    type="number" step="0.1"
                                    v-model.number="tempQuotaGB" 
                                    class="flex-1 bg-white border-2 border-black/5 rounded-xl px-3 py-2 text-xs font-black outline-none focus:border-primary transition-all"
                                    autofocus
                                  />
                                  <span class="text-[10px] font-black text-secondary/70 uppercase tracking-widest">GB</span>
                                </div>
                                <div class="flex space-x-2">
                                  <button 
                                    @click="handleQuotaUpdate"
                                    :disabled="isUpdatingQuota"
                                    class="flex-1 py-2 bg-primary text-white text-[9px] font-black uppercase rounded-lg shadow-lg active:scale-95 transition-all"
                                    :style="{ backgroundColor: 'var(--accent-color)' }"
                                  >
                                    <Loader2 v-if="isUpdatingQuota" class="w-3 h-3 animate-spin mx-auto" />
                                    <span v-else>保存</span>
                                  </button>
                                  <button @click="editingQuotaUuid = null" class="p-2 bg-black/5 text-secondary rounded-lg hover:bg-black/10 transition-colors">
                                    <X class="w-3 h-3" />
                                  </button>
                                </div>
                            </div>

                            <div v-else class="space-y-2">
                                <div class="h-2.5 w-full bg-black/5 rounded-full overflow-hidden shadow-inner border border-white/10">
                                    <div 
                                        class="h-full transition-all duration-1000 ease-spring" 
                                        :style="{ 
                                            width: `${Math.min(100, (u.used_storage / u.storage_quota) * 100)}%`,
                                            backgroundColor: (u.used_storage / u.storage_quota) > 0.9 ? '#ef4444' : 'var(--accent-color)',
                                            opacity: 0.8
                                        }"
                                    ></div>
                                </div>
                                <div class="flex justify-between items-center">
                                    <span class="text-[10px] md:text-xs font-mono font-bold text-secondary/60">已用 {{ Math.round((u.used_storage / u.storage_quota) * 100) }}%</span>
                                    <p class="text-[10px] md:text-xs font-mono text-secondary/60 font-black">{{ formatBytes(u.used_storage) }} / {{ formatBytes(u.storage_quota) }}</p>
                                </div>
                            </div>
                        </div>

                        <div class="flex justify-between items-center pt-2 border-t border-black/5">
                            <span class="text-[10px] md:text-xs font-mono font-bold text-secondary/60">加入于 {{ new Date(u.created_at * 1000).toLocaleDateString() }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      </section>

      <!-- SECTION 2: SYSTEM CONFIGURATION -->
      <section class="space-y-6">
        <div class="flex items-center space-x-3 px-1">
            <div class="p-2 bg-primary/10 rounded-xl" :style="{ color: 'var(--accent-color)' }">
                <SettingsIcon class="w-5 h-5" />
            </div>
            <h2 class="text-lg font-black uppercase tracking-widest text-primary-dark">全局配置</h2>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="card-glass p-8 flex items-center justify-between hover:shadow-[0_0_30px_rgba(0,163,255,0.12)] hover:bg-white/60 hover:border-primary/20 transition-all">
                <div class="space-y-1">
                    <p class="text-base font-black text-on-surface">开放新用户注册</p>
                    <p class="text-xs text-secondary/70">允许任何人通过注册页面加入系统</p>
                </div>
                <button 
                    @click="systemSettings.allow_registration = !systemSettings.allow_registration; handleUpdateSettings()"
                    :disabled="isSaving"
                    :class="['w-14 h-7 rounded-full transition-all relative shrink-0 shadow-inner border border-white/20', systemSettings.allow_registration ? 'bg-primary' : 'bg-secondary/20']"
                    :style="{ backgroundColor: systemSettings.allow_registration ? 'var(--accent-color)' : '' }"
                >
                    <div :class="['absolute top-1 w-5 h-5 bg-white rounded-full transition-all shadow-md', systemSettings.allow_registration ? 'left-8' : 'left-1']"></div>
                </button>
            </div>

            <div class="card-glass p-8 space-y-5 hover:shadow-[0_0_30px_rgba(0,163,255,0.12)] hover:bg-white/60 hover:border-primary/20 transition-all">
                <div class="flex items-center justify-between">
                    <div class="space-y-0.5">
                        <p class="text-sm font-black text-on-surface">认证速率限制</p>
                        <p class="text-[10px] text-secondary/70 font-medium">登录/注册频率限制 (次/分钟)</p>
                    </div>
                    <div class="flex items-center space-x-2">
                      <input 
                        type="number" 
                        v-model.number="systemSettings.auth_rate_limit" 
                        @change="handleUpdateSettings"
                        class="w-16 bg-white border-2 border-black/5 rounded-xl px-2 py-1.5 text-xs font-black outline-none focus:border-primary transition-all text-center"
                      />
                    </div>
                </div>
                
                <div class="pt-4 border-t border-black/5 flex items-center justify-between">
                    <div class="space-y-0.5">
                        <p class="text-sm font-black text-on-surface">默认 Token 有效期</p>
                        <p class="text-[10px] text-secondary/70 font-medium">新登录会话的默认持续时间 (小时)</p>
                    </div>
                    <div class="flex items-center space-x-2">
                      <input 
                        type="number" 
                        :value="Math.round(systemSettings.default_token_expire / 3600)" 
                        @input="systemSettings.default_token_expire = (Number($event.target.value) * 3600); handleUpdateSettings()"
                        class="w-16 bg-white border-2 border-black/5 rounded-xl px-2 py-1.5 text-xs font-black outline-none focus:border-primary transition-all text-center"
                      />
                      <span class="text-[10px] font-black text-secondary/70 uppercase">h</span>
                    </div>
                </div>
            </div>
        </div>
      </section>

      <!-- SECTION 3: MAINTENANCE & DANGER ZONE -->
      <section class="space-y-6">
        <div class="flex items-center space-x-3 px-1">
            <div class="p-2 bg-red-500/10 rounded-xl text-red-500">
                <ShieldAlert class="w-5 h-5" />
            </div>
            <h2 class="text-lg font-black uppercase tracking-widest text-red-600">系统维护与安全</h2>
        </div>

        <div class="card-glass p-8 md:p-12 border-red-500/30 bg-red-500/[0.03] relative overflow-hidden group">
            <AlertTriangle class="absolute -right-8 -bottom-8 w-48 h-48 text-red-500/5 rotate-12 pointer-events-none group-hover:scale-110 transition-transform duration-1000" />
            
            <div class="relative z-10 max-w-2xl">
                <div class="flex items-center space-x-3 mb-6">
                    <div class="w-10 h-10 rounded-2xl bg-red-500/10 flex items-center justify-center">
                        <Database class="w-6 h-6 text-red-500" />
                    </div>
                    <h3 class="text-xl font-black text-red-600 uppercase italic tracking-tighter">工厂重置协议</h3>
                </div>

                <p class="text-sm text-red-900/90 leading-relaxed mb-8 font-medium">
                    执行此操作将物理性抹除系统中的所有业务数据，包括所有消息历史、已上传的附件、活跃的分享链接以及除您之外的所有普通用户账号。<span class="font-black underline">此操作一经启动，不可撤销。</span>
                </p>
                
                <div v-if="confirmReset" class="space-y-6 p-6 bg-white/40 backdrop-blur-xl rounded-3xl border border-red-200/50 shadow-2xl animate-in fade-in slide-in-from-bottom-4">
                    <div class="space-y-2">
                        <label class="block text-[10px] font-black text-red-600 uppercase tracking-widest ml-1">管理员身份二次验证</label>
                        <input 
                            v-model="adminPassword"
                            type="password"
                            placeholder="请输入管理员密码以确认"
                            class="w-full bg-white border-2 border-red-100 rounded-2xl py-4 px-6 text-sm outline-none focus:border-red-400 focus:ring-4 ring-red-500/10 transition-all"
                        />
                    </div>
                    
                    <div class="flex flex-col md:flex-row space-y-3 md:space-y-0 md:space-x-4">
                        <button 
                            @click="handleFactoryReset"
                            :disabled="isResetting || !adminPassword"
                            class="flex-1 py-4 bg-red-600 text-white rounded-2xl font-black text-xs uppercase tracking-[0.2em] hover:bg-red-700 active:scale-[0.98] transition-all shadow-[0_10px_30px_rgba(239,68,68,0.3)] flex items-center justify-center space-x-3"
                        >
                            <Loader2 v-if="isResetting" class="w-3 h-3 animate-spin" />
                            <Database v-else class="w-4 h-4" />
                            <span>确认物理级数据抹除</span>
                        </button>
                        <button 
                            @click="confirmReset = false" 
                            class="px-8 py-4 bg-white/80 text-secondary rounded-2xl font-black text-xs uppercase tracking-widest border border-black/5 hover:bg-white transition-all active:scale-[0.98]"
                        >
                            放弃操作
                        </button>
                    </div>
                </div>

                <button 
                    v-else
                    @click="confirmReset = true"
                    class="group/btn relative px-8 py-4 bg-white border-2 border-red-500/20 rounded-2xl overflow-hidden transition-all hover:border-red-500/50"
                >
                    <div class="absolute inset-0 bg-red-500 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-300"></div>
                    <span class="relative z-10 text-red-500 group-hover/btn:text-white font-black text-xs uppercase tracking-[0.2em] flex items-center space-x-3">
                        <AlertTriangle class="w-4 h-4" />
                        <span>启动系统重置程序</span>
                    </span>
                </button>
            </div>
        </div>
      </section>

      <!-- FOOTER -->
      <footer class="pt-16 pb-12 text-center space-y-3 border-t border-black/5 opacity-60">
        <div class="flex items-center justify-center space-x-3 text-primary-dark">
            <HardDrive class="w-4 h-4" />
            <span class="text-xs font-black uppercase tracking-[0.4em]">U-Drop 核心版本 v0.5.1</span>
        </div>
        <p class="text-[9px] font-mono text-secondary italic">加密标准: AES-256-GCM • 数据完整性: BLAKE3 实时校验</p>
      </footer>

    </div>
  </div>
</template>

<style scoped>
.card-glass {
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 32px;
}

.ease-spring {
  transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
}

.shadow-key {
  box-shadow: 
    10px 10px 30px rgba(0,0,0,0.05),
    -10px -10px 30px rgba(255,255,255,0.5);
}

.shadow-ambient {
  box-shadow: 0 10px 40px rgba(0, 163, 255, 0.1);
}

input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>
