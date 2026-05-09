<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { FileService, MessageService } from '../api/services';
import type { BigFileResponse, BigFileReference, MessageResponse } from '../types/api';
import { useToast } from '../utils/toast';
import { useUser } from '../utils/user';
import { showConfirm } from '../utils/confirm';
import DotLoading from '../components/atomic/DotLoading.vue';
import MessageBubble from '../components/atomic/MessageBubble.vue';
import { 
  FileIcon, 
  Download,
  PieChart,
  HardDrive,
  Eye,
  Trash2,
  ChevronDown,
  ChevronUp,
  Hash,
  Info,
  Circle,
  CheckCircle2,
  X,
  AlertTriangle,
  History,
  ShieldX,
  Copy,
  Loader2
} from 'lucide-vue-next';

const largeFiles = ref<BigFileResponse[]>([]);
const isLoading = ref(false);
const expandedHashes = ref<Set<string>>(new Set());
const { showToast } = useToast();
const { fetchUser } = useUser();

// 预览相关
const previewMsgMap = ref<Map<number, MessageResponse>>(new Map());
const previewLoadingMap = ref<Record<number, boolean>>({}); 
const activePreviewId = ref<number | null>(null);

// 批量选择相关
const selectedRefs = ref<Set<string>>(new Set()); // Key: {file_hash}-{attachment_id}

const loadLargeFiles = async () => {
  try {
    isLoading.value = true;
    const res = await FileService.getLargeFiles(30);
    if (res.data.success && res.data.data) {
      largeFiles.value = res.data.data;
    }
  } catch (err) {
    showToast('获取存储数据失败', 'error');
  } finally {
    isLoading.value = false;
  }
};

const toggleExpand = (hash: string) => {
  if (expandedHashes.value.has(hash)) {
    expandedHashes.value.delete(hash);
  } else {
    expandedHashes.value.add(hash);
  }
};

const toggleRefSelection = (fileHash: string, attId: number) => {
  const key = `${fileHash}-${attId}`;
  if (selectedRefs.value.has(key)) {
    selectedRefs.value.delete(key);
  } else {
    selectedRefs.value.add(key);
  }
};

const isRefSelected = (fileHash: string, attId: number) => {
  return selectedRefs.value.has(`${fileHash}-${attId}`);
};

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 饼图相关逻辑
const hoveredSlice = ref<any>(null);
const chartColors = [
  '#00A3FF', '#22c55e', '#f97316', '#a855f7', '#ec4899', '#64748b'
];

const chartData = computed(() => {
  if (largeFiles.value.length === 0) return [];
  
  const sorted = [...largeFiles.value].sort((a, b) => b.file_size - a.file_size);
  const topCount = 5;
  const topFiles = sorted.slice(0, topCount);
  const otherFiles = sorted.slice(topCount);
  
  const totalSize = sorted.reduce((acc, f) => acc + f.file_size, 0);
  
  let currentAngle = 0;
  const data = topFiles.map((f, i) => {
    const percentage = f.file_size / totalSize;
    const angle = percentage * 360;
    const slice = {
      name: f.references[0]?.display_name || '未命名',
      size: f.file_size,
      percentage: (percentage * 100).toFixed(1),
      startAngle: currentAngle,
      angle: angle,
      color: chartColors[i % chartColors.length],
      full_hash: f.full_hash
    };
    currentAngle += angle;
    return slice;
  });
  
  if (otherFiles.length > 0) {
    const otherSize = otherFiles.reduce((acc, f) => acc + f.file_size, 0);
    const percentage = otherSize / totalSize;
    data.push({
      name: '其他文件',
      size: otherSize,
      percentage: (percentage * 100).toFixed(1),
      startAngle: currentAngle,
      angle: percentage * 360,
      color: '#94a3b8',
      full_hash: 'others'
    });
  }
  
  return data;
});

const getSlicePath = (startAngle: number, angle: number) => {
  const radius = 80;
  const centerX = 100;
  const centerY = 100;
  
  const x1 = centerX + radius * Math.cos((Math.PI * (startAngle - 90)) / 180);
  const y1 = centerY + radius * Math.sin((Math.PI * (startAngle - 90)) / 180);
  const x2 = centerX + radius * Math.cos((Math.PI * (startAngle + angle - 90)) / 180);
  const y2 = centerY + radius * Math.sin((Math.PI * (startAngle + angle - 90)) / 180);
  
  const largeArcFlag = angle > 180 ? 1 : 0;
  
  return `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;
};

onMounted(loadLargeFiles);

const handleDownload = async (attId: number, name: string) => {
  try {
    const res = await FileService.download(attId);
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', name);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (err) {
    showToast('下载失败', 'error');
  }
};

const handleCopyHash = (hash: string) => {
  navigator.clipboard.writeText(hash);
  showToast('哈希值已复制', 'success');
};

const handlePreview = async (msgId: number) => {
  if (activePreviewId.value === msgId) {
    activePreviewId.value = null;
    return;
  }
  
  if (previewMsgMap.value.has(msgId)) {
    activePreviewId.value = msgId;
    return;
  }

  try {
    previewLoadingMap.value[msgId] = true;
    const res = await MessageService.getOne(msgId);

    if (res.data.success && res.data.data) {
      previewMsgMap.value.set(msgId, res.data.data);
      activePreviewId.value = msgId;
    } else {
      showToast('未找到该消息', 'info');
    }
  } catch (err) {
    showToast('预览加载失败', 'error');
  } finally {
    previewLoadingMap.value[msgId] = false;
  }
};

const isBatchProcessing = ref(false);

const handleDetachSingle = async (r: BigFileReference) => {
  const confirmed = await showConfirm({
    title: '取消文件引用',
    message: `确定要从消息中移除该文件的关联吗？此操作不可撤销。`,
    isDanger: true,
    confirmText: '确认移除'
  });

  if (!confirmed) return;

  try {
    isBatchProcessing.value = true;
    const res = await FileService.detachAttachment(r.message_id, r.attachment_id);
    if (res.data.success) {
      showToast('引用已取消', 'success');
      await loadLargeFiles();
      fetchUser();
    }
  } catch (err) {
    showToast('操作失败', 'error');
  } finally {
    isBatchProcessing.value = false;
  }
};

// 路径 A：批量精准剥离
const handleBatchDetach = async () => {
  if (selectedRefs.value.size === 0) return;
  
  const confirmed = await showConfirm({
    title: '批量取消引用',
    message: `确定要移除选中的 ${selectedRefs.value.size} 处引用吗？如果这是文件的最后一次引用，系统将释放对应的存储空间。`,
    isDanger: true,
    confirmText: '批量移除'
  });

  if (!confirmed) return;

  try {
    isBatchProcessing.value = true;
    const tasks = Array.from(selectedRefs.value).map(key => {
      const [_, attIdStr] = key.split(/-(?=[^-]+$)/); 
      const attId = parseInt(attIdStr);
      let msgId = 0;
      for (const f of largeFiles.value) {
          const found = f.references.find(ri => ri.attachment_id === attId);
          if (found) { msgId = found.message_id; break; }
      }
      return { msgId, attId };
    });

    let successCount = 0;
    for (const task of tasks) {
        try {
            await FileService.detachAttachment(task.msgId, task.attId);
            successCount++;
        } catch (e) { console.error('Batch detach failed', task); }
    }

    showToast(`成功取消 ${successCount} 处引用`, 'success');
    selectedRefs.value.clear();
    await loadLargeFiles();
    fetchUser();
  } finally {
    isBatchProcessing.value = false;
  }
};

// 路径 B：批量整条删除
const handleBatchDeleteMessages = async () => {
  if (selectedRefs.value.size === 0) return;

  const confirmed = await showConfirm({
    title: '批量删除消息',
    message: `确定要将选中的 ${selectedRefs.value.size} 条消息移入回收站吗？`,
    isDanger: true,
    confirmText: '移入回收站'
  });

  if (!confirmed) return;

  try {
    isBatchProcessing.value = true;
    const msgIds = new Set<number>();
    selectedRefs.value.forEach(key => {
        const [_, attIdStr] = key.split(/-(?=[^-]+$)/);
        const attId = parseInt(attIdStr);
        for (const f of largeFiles.value) {
            const found = f.references.find(ri => ri.attachment_id === attId);
            if (found) { msgIds.add(found.message_id); break; }
        }
    });

    let successCount = 0;
    for (const id of Array.from(msgIds)) {
        try {
            await MessageService.delete(id);
            successCount++;
        } catch (e) { console.error('Batch delete msg failed', id); }
    }

    showToast(`已将 ${successCount} 条消息移入回收站`, 'success');
    selectedRefs.value.clear();
    await loadLargeFiles();
    fetchUser();
  } finally {
    isBatchProcessing.value = false;
  }
};
</script>

<template>
  <div class="flex-1 overflow-y-auto p-4 md:p-12 pb-32 md:pb-40 bg-transparent relative">
    <div class="max-w-5xl mx-auto space-y-12">
      <!-- HEADER -->
      <header class="flex justify-between items-end">
        <div class="space-y-2">
          <h1 class="text-3xl md:text-4xl font-black text-primary-dark tracking-tighter uppercase">Storage Assistant</h1>
          <p class="text-sm text-secondary/85 font-medium tracking-wide italic">
             <span class="text-primary" :style="{ color: 'var(--accent-color)' }">存储分析模式</span>：多重引用精准去重，实时掌握配额占用。
          </p>
        </div>
        <div class="p-4 rounded-3xl bg-white/50 shadow-ambient">
           <PieChart class="w-8 h-8 text-primary" />
        </div>
      </header>

      <!-- STATS OVERVIEW -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
         <!-- Original Stats Card -->
         <div class="card-glass p-8 flex flex-col justify-between space-y-4 shadow-sm">
            <div class="flex items-center space-x-3 text-secondary/70">
               <HardDrive class="w-4 h-4" />
               <span class="text-[11px] font-black uppercase tracking-widest">唯一物理文件</span>
            </div>
            <h3 class="text-2xl font-black text-primary-dark">{{ largeFiles.length }} 项数据</h3>
            <p class="text-[10px] text-secondary/60 font-mono tracking-tighter italic">仅统计占用实际配额的实体文件。</p>
         </div>

         <!-- Pie Chart Card -->
         <div class="md:col-span-2 card-glass p-6 md:p-8 flex flex-col md:flex-row items-center md:items-stretch space-y-6 md:space-y-0 md:space-x-8 shadow-sm relative overflow-hidden">
            <!-- SVG Pie Chart -->
            <div class="relative w-40 h-40 md:w-48 md:h-48 shrink-0 flex items-center justify-center">
                <svg viewBox="0 0 200 200" class="w-full h-full transform -rotate-6 transition-transform duration-1000 hover:rotate-0">
                  <defs>
                    <filter id="pie-glow" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur" />
                      <feOffset in="blur" dx="0" dy="0" result="offsetBlur" />
                      <feFlood flood-color="white" flood-opacity="0.3" result="offsetColor" />
                      <feComposite in="offsetColor" in2="offsetBlur" operator="in" result="glow" />
                      <feMerge>
                        <feMergeNode in="glow" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  </defs>
                  
                  <g v-if="chartData.length > 0">
                    <path 
                      v-for="(slice, i) in chartData" 
                      :key="i"
                      :d="getSlicePath(slice.startAngle, slice.angle)"
                      :fill="slice.color"
                      class="transition-all duration-500 cursor-pointer origin-center hover:scale-[1.03]"
                      :class="hoveredSlice?.name === slice.name ? 'filter-[url(#pie-glow)]' : 'opacity-80 hover:opacity-100'"
                      @mouseenter="hoveredSlice = slice"
                      @mouseleave="hoveredSlice = null"
                    />
                  </g>
                  <circle v-else cx="100" cy="100" r="80" fill="rgba(0,0,0,0.05)" />
                  
                  <!-- Donut Hole -->
                  <circle cx="100" cy="100" r="30" fill="white" fill-opacity="0.9" />
                  <text x="100" y="105" text-anchor="middle" class="text-[14px] font-black fill-primary-dark opacity-10">U</text>
                </svg>
            </div>

            <!-- Chart Info / Legend -->
            <div class="flex-1 flex flex-col justify-center min-w-0 space-y-4">
                <div v-if="hoveredSlice" class="animate-in fade-in slide-in-from-left-2 duration-300">
                    <div class="flex items-center space-x-2 mb-1">
                        <div class="w-2.5 h-2.5 rounded-full shadow-[0_0_8px_currentColor]" :style="{ backgroundColor: hoveredSlice.color, color: hoveredSlice.color }"></div>
                        <span class="text-[10px] font-black uppercase tracking-widest text-secondary/70">详细占用信息</span>
                    </div>
                    <h4 class="text-lg font-black text-primary-dark truncate leading-tight">{{ hoveredSlice.name }}</h4>
                    <div class="flex items-baseline space-x-3 mt-1">
                        <span class="text-sm font-black text-primary" :style="{ color: 'var(--accent-color)' }">{{ formatBytes(hoveredSlice.size) }}</span>
                        <span class="text-[10px] font-mono font-bold text-secondary/60">占总额 {{ hoveredSlice.percentage }}%</span>
                    </div>
                </div>
                <div v-else class="flex flex-col justify-center space-y-1 opacity-40">
                    <p class="text-sm font-bold text-primary-dark">存储分布概览</p>
                    <p class="text-[10px] font-medium text-secondary/80">悬停查看具体文件占用比例。</p>
                </div>

                <!-- Small Legend List -->
                <div class="flex flex-wrap gap-x-4 gap-y-1.5 mt-auto pt-4 border-t border-black/5">
                    <div v-for="slice in chartData" :key="slice.name" class="flex items-center space-x-2">
                        <div class="w-1.5 h-1.5 rounded-full shrink-0" :style="{ backgroundColor: slice.color }"></div>
                        <span class="text-[9px] font-bold text-secondary/60 truncate max-w-[80px]">{{ slice.name }}</span>
                    </div>
                </div>
            </div>
         </div>
      </div>

      <!-- MAIN LIST -->
      <section class="space-y-6">
        <div class="flex items-center justify-between px-1">
           <div class="flex items-center space-x-3">
              <h2 class="text-lg font-black uppercase tracking-widest text-primary-dark">占用排行 (TOP 30)</h2>
              <div class="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse"></div>
           </div>
           <button @click="loadLargeFiles" :disabled="isLoading" class="text-xs font-black text-primary hover:underline decoration-2 underline-offset-4 uppercase tracking-widest">扫描更新</button>
        </div>

        <div v-if="isLoading" class="py-20 flex flex-col items-center justify-center space-y-4 card-glass shadow-sm">
           <DotLoading />
           <p class="text-[10px] font-black uppercase tracking-[0.2em] text-secondary/80 animate-pulse text-center">正在扫描文件系统...</p>
        </div>

        <div v-else-if="largeFiles.length === 0" class="card-glass p-20 text-center space-y-4 shadow-sm">
            <div class="w-16 h-16 bg-black/5 rounded-full flex items-center justify-center mx-auto">
                <Info class="w-8 h-8 text-secondary/40" />
            </div>
            <p class="text-sm text-secondary/70 font-black uppercase tracking-widest">暂无大文件占用记录</p>
        </div>

        <div v-else class="space-y-4">
          <div 
            v-for="file in largeFiles" 
            :key="file.full_hash"
            class="card-glass overflow-hidden transition-all duration-500 ease-spring border border-white/40 shadow-sm"
            :class="[
              hoveredSlice?.full_hash === file.full_hash 
                ? 'scale-[1.01] ring-2 ring-primary/40 z-20 shadow-[0_0_30px_rgba(0,163,255,0.15)] relative bg-white/60' 
                : 'opacity-100 z-10 hover:bg-white/50 hover:shadow-[0_0_20px_rgba(0,163,255,0.08)]'
            ]"
            :style="hoveredSlice?.full_hash === file.full_hash ? { borderColor: hoveredSlice.color } : {}"
            @mouseenter="hoveredSlice = chartData.find(s => s.full_hash === file.full_hash) || null"
            @mouseleave="hoveredSlice = null"
          >
            <!-- File Header Card -->
            <div class="p-5 md:p-6 flex items-center justify-between">
                <div class="flex items-center space-x-4 flex-1 min-w-0">
                    <div class="p-3.5 bg-primary/5 rounded-2xl flex-shrink-0 shadow-sm border border-white/40">
                        <FileIcon class="w-6 h-6 text-primary" />
                    </div>
                    <div class="flex-1 min-w-0 space-y-1.5">
                        <div class="flex items-center space-x-3">
                            <h4 class="font-black text-primary-dark truncate text-base md:text-lg">
                                {{ file.references[0]?.display_name || '未命名文件' }}
                            </h4>
                            <span class="text-[9px] font-black uppercase px-2 py-0.5 bg-black/5 text-secondary/80 rounded-lg border border-black/5">
                                {{ file.mime_type || 'Unknown' }}
                            </span>
                        </div>
                        <div class="flex items-center space-x-4">
                            <p class="text-sm font-black text-primary" :style="{ color: 'var(--accent-color)' }">{{ formatBytes(file.file_size) }}</p>
                            <div 
                              @click="handleCopyHash(file.full_hash)"
                              class="flex items-center space-x-1.5 text-secondary/70 cursor-pointer group/hash hover:text-primary transition-colors"
                            >
                                <Hash class="w-3 h-3" />
                                <p class="text-[10px] font-mono font-bold uppercase tracking-tighter">{{ file.full_hash.slice(0, 16) }}...</p>
                                <Copy class="w-2.5 h-2.5 opacity-0 group-hover/hash:opacity-100 transition-opacity" />
                            </div>
                        </div>
                    </div>
                </div>

                <div class="flex items-center space-x-2 md:space-x-3 ml-4">
                    <button 
                        v-if="file.references.length > 0"
                        @click="handleDownload(file.references[0].attachment_id, file.references[0].display_name)"
                        class="p-3 rounded-xl bg-black/5 text-secondary/85 hover:bg-white hover:text-primary transition-all active:scale-90 shadow-sm"
                    >
                        <Download class="w-4 h-4 md:w-5 md:h-5" />
                    </button>
                    <button 
                        @click="toggleExpand(file.full_hash)"
                        class="px-4 py-3 rounded-xl flex items-center space-x-2 bg-primary/10 text-primary font-black text-[10px] uppercase tracking-widest transition-all active:scale-95 shadow-md"
                        :style="{ color: 'var(--accent-color)', backgroundColor: 'color-mix(in srgb, var(--accent-color) 10%, transparent)' }"
                    >
                        <span>{{ file.refer_count }} 处关联</span>
                        <ChevronDown v-if="!expandedHashes.has(file.full_hash)" class="w-3.5 h-3.5" />
                        <ChevronUp v-else class="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            <!-- References Detail List -->
            <Transition
              enter-active-class="transition-all duration-500 ease-spring"
              enter-from-class="max-h-0 opacity-0"
              enter-to-class="max-h-[1200px] opacity-100"
              leave-active-class="transition-all duration-300 ease-in"
              leave-from-class="max-h-[1200px] opacity-100"
              leave-to-class="max-h-0 opacity-0"
            >
              <div v-if="expandedHashes.has(file.full_hash)" class="bg-black/[0.03] border-t border-black/5 shadow-inner">
                <div class="p-2 space-y-1">
                    <div 
                        v-for="r in file.references" 
                        :key="r.attachment_id"
                        class="flex flex-col"
                    >
                        <!-- Ref Row -->
                        <div 
                          class="flex items-center justify-between p-3 md:p-4 rounded-2xl transition-all group/row"
                          :class="isRefSelected(file.full_hash, r.attachment_id) ? 'bg-primary/10 shadow-sm' : 'hover:bg-white/60'"
                        >
                            <div class="flex items-center space-x-4 min-w-0">
                                <div 
                                  @click="toggleRefSelection(file.full_hash, r.attachment_id)"
                                  class="cursor-pointer transition-transform active:scale-90"
                                >
                                    <component 
                                      :is="isRefSelected(file.full_hash, r.attachment_id) ? CheckCircle2 : Circle" 
                                      class="w-5 h-5 transition-all"
                                      :class="isRefSelected(file.full_hash, r.attachment_id) ? 'text-primary' : 'text-secondary/30 group-hover/row:text-secondary/60'"
                                      :style="isRefSelected(file.full_hash, r.attachment_id) ? { color: 'var(--accent-color)' } : {}"
                                    />
                                </div>
                                <div class="min-w-0">
                                    <p class="text-xs font-black text-on-surface truncate">{{ r.display_name }}</p>
                                    <p class="text-[10px] font-mono font-bold text-secondary/70 uppercase tracking-tighter">关联消息: #{{ r.message_id.toString(16).toUpperCase() }}</p>
                                </div>
                            </div>
                            
                            <div class="flex items-center space-x-2 ml-4 shrink-0">
                                <button 
                                    @click="handlePreview(r.message_id)"
                                    class="p-2 rounded-lg transition-all"
                                    :class="activePreviewId === r.message_id ? 'bg-primary/20 text-primary shadow-inner' : 'text-secondary/60 hover:bg-white'"
                                    :style="activePreviewId === r.message_id ? { color: 'var(--accent-color)' } : {}"
                                    title="预览消息上下文"
                                >
                                    <Loader2 v-if="previewLoadingMap[r.message_id]" class="w-4 h-4 animate-spin" />
                                    <Eye v-else class="w-4 h-4" />
                                </button>
                                <div class="w-px h-4 bg-black/10"></div>
                                <button 
                                    @click="handleDetachSingle(r)" 
                                    v-if="!isRefSelected(file.full_hash, r.attachment_id)"
                                    class="p-2 text-secondary/50 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover/row:opacity-100"
                                    title="取消此引用"
                                >
                                    <Trash2 class="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        <!-- In-place Preview Area -->
                        <Transition
                          enter-active-class="transition-all duration-500 ease-spring"
                          enter-from-class="max-h-0 opacity-0 -translate-y-2"
                          enter-to-class="max-h-[400px] opacity-100 translate-y-0"
                          leave-active-class="transition-all duration-300 ease-in"
                          leave-from-class="max-h-[400px] opacity-100 translate-y-0"
                          leave-to-class="max-h-0 opacity-0 -translate-y-2"
                        >
                           <div v-if="activePreviewId === r.message_id" class="px-6 py-4 bg-white/60 rounded-3xl mx-4 mb-4 border border-white/80 shadow-key overflow-hidden">
                              <div class="mb-3 flex items-center justify-between">
                                 <span class="text-[10px] font-black text-secondary/60 uppercase tracking-[0.2em] flex items-center">
                                    <History class="w-3 h-3 mr-2" /> 原始消息快照
                                 </span>
                                 <button @click="activePreviewId = null" class="text-secondary/50 hover:text-secondary"><X class="w-3.5 h-3.5" /></button>
                              </div>
                              <MessageBubble 
                                v-if="previewMsgMap.has(r.message_id)"
                                :message="previewMsgMap.get(r.message_id)!" 
                                class="scale-[0.9] origin-top-left -ml-4"
                              />
                           </div>
                        </Transition>
                    </div>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </section>
    </div>

    <!-- BATCH ACTION BAR -->
    <Transition
      enter-active-class="transition-all duration-500 ease-spring"
      enter-from-class="translate-y-20 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition-all duration-300 ease-in"
      leave-to-class="translate-y-20 opacity-0"
    >
        <div v-if="selectedRefs.size > 0" class="fixed bottom-10 left-1/2 -translate-x-1/2 z-[100] w-[90%] max-w-2xl">
            <div class="card-glass p-4 md:p-6 bg-white/90 border-primary/20 shadow-md backdrop-blur-2xl flex items-center justify-between border border-white/80">
                <div class="flex items-center space-x-4">
                    <div class="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center shadow-inner" :style="{ color: 'var(--accent-color)' }">
                        <AlertTriangle class="w-6 h-6 animate-pulse" />
                    </div>
                    <div class="flex flex-col">
                        <h4 class="text-sm font-black text-primary-dark uppercase tracking-widest">批量管理中心</h4>
                        <p class="text-[10px] font-black text-secondary/80">已选择 {{ selectedRefs.size }} 处文件引用</p>
                    </div>
                </div>

                <div class="flex items-center space-x-3">
                    <button 
                      @click="handleBatchDeleteMessages"
                      :disabled="isBatchProcessing"
                      class="px-5 py-3 rounded-xl bg-black/5 text-secondary font-black text-[10px] uppercase tracking-widest hover:bg-red-50 hover:text-red-500 transition-all flex items-center space-x-2"
                    >
                        <Trash2 class="w-3.5 h-3.5" />
                        <span class="hidden sm:inline">删除消息</span>
                    </button>
                    <button 
                      @click="handleBatchDetach"
                      :disabled="isBatchProcessing"
                      class="px-6 py-3 rounded-xl bg-primary text-white font-black text-[10px] uppercase tracking-widest hover:scale-105 active:scale-95 shadow-xl transition-all flex items-center space-x-2"
                      :style="{ backgroundColor: 'var(--accent-color)', boxShadow: `0 10px 30px color-mix(in srgb, var(--accent-color) 30%, transparent)` }"
                    >
                        <Loader2 v-if="isBatchProcessing" class="w-3.5 h-3.5 animate-spin" />
                        <ShieldX v-else class="w-3.5 h-3.5" />
                        <span>取消引用</span>
                    </button>
                    <button @click="selectedRefs.clear()" class="p-3 text-secondary/60 hover:text-secondary transition-colors"><X class="w-4 h-4" /></button>
                </div>
            </div>
        </div>
    </Transition>
  </div>
</template>

<style scoped>
.shadow-ambient {
  box-shadow: 0 2px 8px rgba(0, 163, 255, 0.02);
}
.ease-spring {
  transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
}
.shadow-sm {
  box-shadow: 
    1px 1px 4px rgba(0,0,0,0.01),
    -1px -1px 4px rgba(255,255,255,0.05);
}
</style>
