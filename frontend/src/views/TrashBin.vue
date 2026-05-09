<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { MessageService } from '../api/services';
import type { MessageResponse } from '../types/api';
import { useToast } from '../utils/toast';
import { useUser } from '../utils/user';
import { showConfirm } from '../utils/confirm';
import DotLoading from '../components/atomic/DotLoading.vue';
import { 
  Trash2, 
  RefreshCcw, 
  Clock, 
  FileIcon,
  Loader2,
  AlertCircle
} from 'lucide-vue-next';

const trashMessages = ref<MessageResponse[]>([]);
const isLoading = ref(false);
const isProcessing = ref<number | null>(null);
const { showToast } = useToast();
const { fetchUser } = useUser();

const loadTrash = async () => {
  try {
    isLoading.value = true;
    const res = await MessageService.getTrash();
    if (res.data.success && res.data.data) {
      trashMessages.value = res.data.data;
    }
  } catch (err) {
    console.error('Failed to load trash');
  } finally {
    isLoading.value = false;
  }
};

const handleRestore = async (messageId: number) => {
  try {
    isProcessing.value = messageId;
    const res = await MessageService.restore(messageId);
    if (res.data.success) {
      showToast('消息已成功恢复至时间线', 'success');
      trashMessages.value = trashMessages.value.filter(m => m.id !== messageId);
      fetchUser();
    }
  } catch (err) {
    showToast('恢复操作失败', 'error');
  } finally {
    isProcessing.value = null;
  }
};

const handleEmptyTrash = async () => {
  const confirmed = await showConfirm({
    title: '彻底清空回收站',
    message: '确定要物理抹除回收站中的所有内容吗？此操作将立即释放存储配额且不可撤销。',
    isDanger: true,
    confirmText: '立即物理抹除'
  });
  
  if (!confirmed) return;
  
  try {
    isLoading.value = true;
    const res = await MessageService.emptyTrash();
    if (res.data.success) {
      showToast('回收站数据已全量抹除', 'success');
      trashMessages.value = [];
      fetchUser();
    }
  } catch (err) {
    showToast('清空操作失败', 'error');
  } finally {
    isLoading.value = false;
  }
};

const formatTime = (ts: number) => {
  const date = new Date(ts * 1000);
  return date.toLocaleString();
};

onMounted(loadTrash);
</script>

<template>
  <div class="flex-1 overflow-y-auto p-12 bg-transparent">
    <div class="max-w-5xl mx-auto space-y-8">
      <header class="flex justify-between items-end mb-12">
        <div class="space-y-2">
          <h1 class="text-4xl font-black text-primary-dark tracking-tighter uppercase">Trash Bin</h1>
          <p class="text-sm text-secondary/85 font-medium tracking-wide">管理已删除的消息和附件</p>
        </div>
        <div class="flex items-center space-x-4">
           <button 
             @click="loadTrash" 
             :disabled="isLoading"
             class="p-4 rounded-2xl bg-white/50 hover:bg-white transition-all shadow-ambient active:scale-95 disabled:opacity-50"
           >
             <Loader2 v-if="isLoading" class="w-5 h-5 animate-spin text-primary" />
             <Trash2 v-else class="w-5 h-5 text-primary" />
           </button>
           <button 
             v-if="trashMessages.length > 0"
             @click="handleEmptyTrash" 
             :disabled="isLoading"
             class="px-6 py-4 rounded-2xl bg-red-500 text-white font-bold text-xs uppercase tracking-widest hover:bg-red-600 transition-all shadow-lg active:scale-95 disabled:opacity-50"
           >
             Empty Trash
           </button>
        </div>
      </header>

      <!-- List Content -->
      <div v-if="isLoading" class="card-glass p-20 flex flex-col items-center justify-center space-y-4">
        <DotLoading />
        <p class="text-[10px] font-black uppercase tracking-[0.2em] text-secondary/75 animate-pulse">正在检索回收站...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="trashMessages.length === 0" class="card-glass p-20 flex flex-col items-center justify-center space-y-6 text-center">
         <div class="p-6 bg-primary/5 rounded-full">
            <Trash2 class="w-12 h-12 text-primary/20" />
         </div>
         <div class="space-y-1">
           <h3 class="text-xl font-bold text-on-surface">回收站空空如也</h3>
           <p class="text-sm text-secondary/75">被删除的消息将在此保留一段时间</p>
         </div>
      </div>

      <div v-else class="space-y-4">
        <div 
          v-for="msg in trashMessages" 
          :key="msg.id"
          class="card-glass p-6 group transition-all flex items-center justify-between space-x-6 hover:shadow-[0_0_20px_rgba(0,163,255,0.06)] hover:bg-white/50 hover:border-white/60"
        >
          <div class="flex items-center space-x-6 flex-1 min-w-0">
            <div class="p-4 bg-black/5 rounded-2xl flex-shrink-0">
               <FileIcon v-if="msg.type === 1" class="w-6 h-6 text-secondary/85" />
               <AlertCircle v-else class="w-6 h-6 text-secondary/75" />
            </div>
            <div class="flex-1 min-w-0">
               <div class="flex items-center space-x-3 mb-1">
                 <span class="text-[10px] font-black uppercase tracking-widest text-secondary/75">{{ msg.device_name }}</span>
                 <span class="text-[10px] font-mono text-secondary/20">#{{ msg.id.toString(16).toUpperCase() }}</span>
               </div>
               <h4 class="font-bold text-primary-dark truncate text-lg">
                 {{ msg.content || (msg.attachments.length > 0 ? msg.attachments[0].display_name : '无内容') }}
               </h4>
               <div class="flex items-center space-x-4 mt-2">
                 <div class="flex items-center space-x-1.5 text-secondary/75">
                    <Clock class="w-3 h-3" />
                    <span class="text-[10px] font-medium">{{ formatTime(msg.timestamp) }}</span>
                 </div>
                 <div v-if="msg.attachments.length > 0" class="text-[10px] font-bold text-primary/40 uppercase tracking-tighter">
                    + {{ msg.attachments.length }} Attachment(s)
                 </div>
               </div>
            </div>
          </div>

          <div class="flex items-center space-x-2">
             <button 
               @click="handleRestore(msg.id)"
               :disabled="isProcessing === msg.id"
               class="p-4 rounded-2xl bg-white/80 hover:bg-primary hover:text-white transition-all shadow-sm active:scale-95 group/btn"
               title="还原"
             >
                <Loader2 v-if="isProcessing === msg.id" class="w-5 h-5 animate-spin" />
                <RefreshCcw v-else class="w-5 h-5 transition-transform group-hover/btn:-rotate-45" />
             </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
