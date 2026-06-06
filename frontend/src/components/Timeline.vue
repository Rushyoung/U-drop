<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch, nextTick, computed } from 'vue';
import { useTimeline } from '../hooks/useTimeline';
import MessageBubble from './atomic/MessageBubble.vue';
import { useIntersectionObserver, useScroll, useDebounceFn } from '@vueuse/core';
import { getLastAnchor, saveLastAnchor } from '../utils/device';
import { Loader2, Search, Trash2, X, Circle, CheckCircle2, History } from 'lucide-vue-next';
import { useSettings } from '../utils/settings';
import { useUser } from '../utils/user';
import { MessageService } from '../api/services';
import { useToast } from '../utils/toast';
import { showConfirm } from '../utils/confirm';


const props = defineProps<{
  searchQuery?: string;
}>();

const { 
  messages, 
  isLoading, 
  loadMessages, 
  loadMoreAfter, 
  startPolling, 
  addOptimisticMessage,
  updateMessageId,
  refreshMessage,
  removeMessage,
  destroy
} = useTimeline();

const { settings: _settings } = useSettings();
const containerRef = ref<HTMLElement | null>(null);
const topAnchor = ref<HTMLElement | null>(null);
const bottomAnchor = ref<HTMLElement | null>(null);
const isInitialPositioning = ref(true);

const { y: containerY } = useScroll(containerRef);
const showScrollButton = ref(false);
const isBulkMode = ref(false);
const selectedIds = ref(new Set<number>());

const toggleBulkMode = () => {
  isBulkMode.value = !isBulkMode.value;
  if (!isBulkMode.value) selectedIds.value.clear();
};
const { fetchUser } = useUser();
const { showToast } = useToast();

const toggleSelection = (id: number) => {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id);
  } else {
    selectedIds.value.add(id);
  }
};

const formatDateSeparator = (timestamp: number) => {
  const date = new Date(timestamp * 1000);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterday = today - 86400000;
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();

  if (target === today) return '今天';
  if (target === yesterday) return '昨天';
  
  return date.toLocaleDateString('zh-CN', { 
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    month: 'long', 
    day: 'numeric',
    weekday: 'long'
  });
};

const shouldShowDateSeparator = (idx: number) => {
  if (idx === 0) return true;
  const curr = new Date(filteredMessages.value[idx].timestamp * 1000).toDateString();
  const prev = new Date(filteredMessages.value[idx - 1].timestamp * 1000).toDateString();
  return curr !== prev;
};

const handleBulkDelete = async () => {
  if (selectedIds.value.size === 0) return;

  const confirmed = await showConfirm({
    title: '批量删除',
    message: `确定要将选中的 ${selectedIds.value.size} 条消息移入回收站吗？`,
    isDanger: true,
    confirmText: '移入回收站'
  });
  
  if (!confirmed) return;

  const ids = Array.from(selectedIds.value);
  let successCount = 0;

  for (const id of ids) {
    try {
      const res = await MessageService.delete(id);
      if (res.data.success) {
        removeMessage(id);
        successCount++;
      }
    } catch (err) {
      console.error(`Failed to delete ${id}`, err);
    }
  }

  if (successCount > 0) {
    showToast(`已将 ${successCount} 条消息移入回收站`, 'success');
    fetchUser();
  }
  
  isBulkMode.value = false;
  selectedIds.value.clear();
};

const filteredMessages = computed(() => {
  if (!props.searchQuery?.trim()) return messages.value;
  const q = props.searchQuery.toLowerCase();
  return messages.value.filter(m => {
    const contentMatch = m.content?.toLowerCase().includes(q);
    const tagMatch = m.tags.some(t => t.toLowerCase().includes(q));
    const attachmentMatch = m.attachments.some(a => a.display_name.toLowerCase().includes(q));
    return contentMatch || tagMatch || attachmentMatch;
  });
});

/**
 * 实时保存阅读进度
 */
const updateReadingProgress = useDebounceFn(() => {
  if (!containerRef.value || isInitialPositioning.value || isLoading.value) return;
  
  const container = containerRef.value;
  const containerRect = container.getBoundingClientRect();
  const bubbles = Array.from(container.querySelectorAll('[data-anchor-id]'));
  
  for (const bubble of bubbles) {
    const rect = bubble.getBoundingClientRect();
    if (rect.bottom > containerRect.top + 50) {
      const id = parseInt(bubble.getAttribute('data-anchor-id') || '0', 10);
      if (id > 0) {
        saveLastAnchor(id);
        break;
      }
    }
  }
}, 500);

// 监听滚动位置
watch(containerY, () => {
  if (containerRef.value) {
    const threshold = containerRef.value.scrollHeight - containerRef.value.clientHeight - 400;
    showScrollButton.value = (containerRef.value.scrollTop) < threshold;
  }
  updateReadingProgress();
});

// 监听新消息到达并根据用户偏好自动滚动
watch(() => filteredMessages.value.length, (newLen, oldLen) => {
  if (newLen > oldLen && !isInitialPositioning.value && _settings.autoScrollToBottom) {
    const container = containerRef.value;
    if (container) {
      // 智能判断：只有当用户当前就在底部附近时，才自动跟进新内容
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 300;
      if (isNearBottom) {
        nextTick(() => {
          scrollToBottom('smooth');
        });
      }
    }
  }
});

const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
  if (containerRef.value) {
    const container = containerRef.value;
    if (behavior === 'instant' as any || behavior === 'auto') {
      container.scrollTop = container.scrollHeight;
      // 关键：在下一帧再次校准，防止图片渲染导致的布局抖动
      requestAnimationFrame(() => {
        if (container) container.scrollTop = container.scrollHeight;
      });
    } else {
      container.scrollTo({
        top: container.scrollHeight,
        behavior
      });
    }
  }
};

/**
 * 核心：跳转到全站最新消息
 */
const jumpToLatest = async () => {
  if (isInitialPositioning.value) return;
  
  isInitialPositioning.value = true;
  saveLastAnchor(0); // 重置锚点，标记为“处于最底部”
  
  try {
    // 传入 null，强制后端返回最后 limit 条数据
    await loadMessagesWithAnchoring('initial', null); 
    await nextTick();
    
    // 多重校准触底
    const forceScroll = () => {
       if (containerRef.value) {
         containerRef.value.scrollTop = containerRef.value.scrollHeight;
       }
    };
    
    forceScroll();
    requestAnimationFrame(forceScroll);
    setTimeout(forceScroll, 100); // 最终保险
    
  } finally {
    setTimeout(() => {
      isInitialPositioning.value = false;
    }, 400);
  }
};

const scrollToAnchor = (anchorId: number | null, behavior: any = 'auto') => {
  if (!anchorId || !containerRef.value) return;
  
  const attemptScroll = () => {
    const element = containerRef.value?.querySelector(`[data-anchor-id="${anchorId}"]`);
    if (element) {
      element.scrollIntoView({ block: 'start', behavior: behavior === 'instant' ? 'auto' : behavior });
      return true;
    }
    return false;
  };

  if (!attemptScroll()) {
    scrollToBottom(behavior);
  } else {
    setTimeout(attemptScroll, 150);
  }
};

/**
 * 带锚定保护的加载逻辑
 */
const loadMessagesWithAnchoring = async (mode: any, anchor: any) => {
  if (!containerRef.value) return;

  const container = containerRef.value;
  const oldScrollHeight = container.scrollHeight;
  const oldScrollTop = container.scrollTop;

  if (mode === 'before' || mode === 'initial') {
    container.classList.remove('scroll-smooth');
  }

  await loadMessages(mode, anchor);
  await nextTick();

  if (mode === 'before' && container) {
    const newScrollHeight = container.scrollHeight;
    const heightDiff = newScrollHeight - oldScrollHeight;
    container.scrollTop = oldScrollTop + heightDiff;
    requestAnimationFrame(() => container.classList.add('scroll-smooth'));
  } else if (mode === 'initial') {
    if (anchor) {
      scrollToAnchor(anchor, 'instant' as any);
    } else {
      container.scrollTop = container.scrollHeight;
    }
    requestAnimationFrame(() => container.classList.add('scroll-smooth'));
  }
};

const handleLoadMoreBefore = async () => {
  if (isLoading.value) return;
  await loadMessagesWithAnchoring('before', messages.value[0]?.id);
};

const handleLoadMoreAfter = async () => {
  if (isLoading.value) return;
  await loadMessagesWithAnchoring('after', messages.value[messages.value.length - 1]?.id);
};

onMounted(async () => {
  const lastId = getLastAnchor();
  isInitialPositioning.value = true;
  await loadMessages('initial');
  await nextTick();
  if (lastId) {
    scrollToAnchor(lastId, 'instant' as any);
  } else {
    scrollToBottom('instant' as any);
  }
  setTimeout(() => {
    isInitialPositioning.value = false;
    startPolling();
  }, 300); 
});

onUnmounted(() => destroy());

useIntersectionObserver(topAnchor, ([{ isIntersecting }]) => {
  if (isIntersecting) handleLoadMoreBefore();
});

useIntersectionObserver(bottomAnchor, ([{ isIntersecting }]) => {
  if (isIntersecting) handleLoadMoreAfter();
});

defineExpose({ 
  loadMoreAfter, 
  loadMessages: loadMessagesWithAnchoring,
  refreshMessage,
  addOptimisticMessage,
  updateMessageId,
  isBulkMode,
  toggleBulkMode,
  removeMessage,
  scrollToBottom,
  jumpToLatest,
  showScrollButton
});
</script>

<template>
  <div class="flex-1 relative m-2 md:m-4 overflow-hidden flex flex-col" style="border-radius: 16px;">
    <!-- 背景 -->
    <div 
      class="absolute inset-0 pointer-events-none z-0"
      style="
        border-radius: 16px;
        background: var(--pit-bg);
        box-shadow: inset 20px 20px 40px rgba(0,0,0,0.1), inset -20px -20px 40px rgba(255,255,255,0.1);
      "
    ></div>

    <!-- 遮罩 -->
    <Transition leave-active-class="transition duration-1000 ease-in-out" leave-to-class="opacity-0 backdrop-blur-0">
      <div v-if="isInitialPositioning" class="absolute inset-0 z-50 bg-[#aed9f4] flex items-center justify-center rounded-[16px]" :style="{ backgroundColor: 'var(--surround-color)' }">
         <div class="flex flex-col items-center space-y-6">
           <div class="relative">
             <div class="w-16 h-16 border-4 border-primary/10 rounded-full" :style="{ borderColor: 'color-mix(in srgb, var(--accent-color) 10%, transparent)' }"></div>
             <Loader2 class="absolute inset-0 w-16 h-16 text-primary animate-spin" :style="{ color: 'var(--accent-color)' }" />
           </div>
           <div class="flex flex-col items-center space-y-1">
             <span class="text-xs font-black text-primary uppercase tracking-[0.5em] animate-pulse" :style="{ color: 'var(--accent-color)' }">Restoring State</span>
             <span class="text-[9px] font-mono text-primary/40 uppercase" :style="{ color: 'color-mix(in srgb, var(--accent-color) 40%, transparent)' }">Synchronizing Ledger Data</span>
           </div>
         </div>
      </div>
    </Transition>

    <!-- 滚动容器 -->
    <div 
      ref="containerRef" 
      class="flex-1 relative z-10 overflow-y-auto overscroll-none scroll-smooth pr-1"
    >
      <div 
        ref="contentAreaRef" 
        :class="[
          'max-w-4xl mx-auto flex flex-col min-h-full px-2 md:px-8 pt-6 md:pt-12 pb-4 transition-all duration-700 ease-spring',
          isInitialPositioning ? 'opacity-0 translate-y-4' : 'opacity-100 translate-y-0'
        ]"
      >
        <!-- 顶部拉取条 -->
        <div ref="topAnchor" class="h-10 w-full flex flex-col justify-center items-center relative overflow-hidden mb-4">
          <div v-if="isLoading" class="absolute inset-x-0 top-0 h-1 bg-primary/10 overflow-hidden">
             <div class="h-full bg-primary animate-scan w-1/2 shadow-[0_0_15px_#00A3FF]"></div>
          </div>
          <div v-if="isLoading" class="text-[9px] font-black text-primary uppercase tracking-[0.4em] animate-pulse">
            Retrieving History
          </div>
        </div>

        <!-- 本地搜索结果状态提示 -->
        <div v-if="searchQuery" class="mb-6 px-4 py-2 bg-white/5 rounded-xl border border-white/10 flex items-center justify-between">
           <div class="flex items-center space-x-2 text-[10px] font-bold text-white/80 uppercase tracking-widest">
              <Search class="w-3 h-3" />
              <span>Filtering Cache</span>
           </div>
           <span class="text-[10px] font-mono text-primary animate-pulse" :style="{ color: 'var(--accent-color)' }">
              {{ filteredMessages.length }} MATCH(ES)
           </span>
        </div>

        <!-- 消息流 -->
        <div class="space-y-4">
          <!-- Empty State Placeholder -->
          <div v-if="filteredMessages.length === 0 && !isLoading && !isInitialPositioning" class="flex flex-col items-center justify-center py-20 animate-in fade-in zoom-in duration-1000">
            <div class="relative mb-6">
              <div class="w-24 h-24 bg-white/10 rounded-[40px] flex items-center justify-center shadow-key border border-white/10">
                <History class="w-10 h-10 text-white/60" />
              </div>
              <div class="absolute -bottom-2 -right-2 w-8 h-8 bg-primary/40 rounded-full blur-xl animate-pulse" :style="{ backgroundColor: 'var(--accent-color)' }"></div>
            </div>
            <div class="text-center space-y-2">
              <h3 class="text-lg font-black text-white/70 uppercase tracking-[0.3em]">你已抵达世界尽头</h3>
              <p class="text-[10px] font-mono text-white/50 uppercase tracking-widest">暂无消息，来发送消息给自己吧</p>
            </div>
          </div>

          <template v-for="(msg, idx) in filteredMessages" :key="msg.id">
            <!-- Date Separator -->
            <div v-if="shouldShowDateSeparator(idx)" class="flex items-center justify-center my-8 md:my-12">
              <div class="h-px flex-1 bg-white/5 shadow-inner"></div>
              <div class="px-4 py-1.5 rounded-full bg-white/5 border border-white/5 backdrop-blur-md shadow-ambient mx-4">
                <span class="text-[10px] md:text-[11px] font-black uppercase tracking-[0.2em] text-white/80 drop-shadow-sm">
                  {{ formatDateSeparator(msg.timestamp) }}
                </span>
              </div>
              <div class="h-px flex-1 bg-white/5 shadow-inner"></div>
            </div>

            <div 
              :class="['transition-all duration-500 flex items-center group/row', isBulkMode ? 'pl-4' : '']"
            >
              <!-- 批量选择图标按钮 -->
              <div 
                v-if="isBulkMode" 
                @click="toggleSelection(msg.id)"
                class="w-10 h-10 flex items-center justify-center cursor-pointer transition-all flex-shrink-0 mr-2 group/check"
              >
                 <component 
                   :is="selectedIds.has(msg.id) ? CheckCircle2 : Circle" 
                   :class="[
                     'w-5 h-5 transition-all duration-300',
                     selectedIds.has(msg.id) 
                      ? 'text-primary scale-110' 
                      : 'text-white/40 group-hover/check:text-white/80'
                   ]"
                   :style="selectedIds.has(msg.id) ? { color: 'var(--accent-color)' } : {}"
                 />
              </div>
              
              <MessageBubble 
                :message="msg" 
                :is-selected="selectedIds.has(msg.id)"
                class="flex-1"
                @deleted="removeMessage" 
              />
            </div>
          </template>
        </div>

        <!-- 底部哨兵 -->
        <div ref="bottomAnchor" class="h-8 w-full flex justify-center items-center">
          <div v-if="isLoading" class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin opacity-20"></div>
        </div>
      </div>
    </div>

    <!-- 批量操作悬浮条 -->
    <Transition
      enter-active-class="transition duration-500 ease-spring"
      enter-from-class="translate-y-20 opacity-0"
      leave-active-class="transition duration-300 ease-in"
      leave-to-class="translate-y-20 opacity-0"
    >
      <div v-if="isBulkMode && selectedIds.size > 0" class="absolute bottom-8 left-1/2 -translate-x-1/2 z-[100] w-auto">
         <div class="card-glass px-6 py-4 flex items-center space-x-8 shadow-2xl border-white/10 bg-black/40 backdrop-blur-2xl">
            <div class="flex flex-col">
               <span class="text-[9px] font-black uppercase text-white/80 tracking-widest leading-none mb-1">Batch Manager</span>
               <span class="text-xs font-bold text-white">{{ selectedIds.size }} items selected</span>
            </div>

            <div class="w-px h-6 bg-white/10"></div>

            <div class="flex items-center space-x-3">
               <button 
                 @click="handleBulkDelete"
                 class="flex items-center space-x-2 px-4 py-2 bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white rounded-xl transition-all font-bold text-[10px] uppercase tracking-widest active:scale-95"
               >
                 <Trash2 class="w-3.5 h-3.5" />
                 <span>Move to Trash</span>
               </button>
               
               <button 
                 @click="selectedIds.clear()"
                 class="p-2 text-white/60 hover:text-white transition-colors"
               >
                 <X class="w-4 h-4" />
               </button>
            </div>
         </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
@keyframes scan {
  0% { transform: translateX(-150%); }
  100% { transform: translateX(350%); }
}
.animate-scan {
  animation: scan 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
