<script setup>
import { ref, onMounted, computed } from 'vue';
import { X, Copy, Download, Loader2, Maximize2 } from 'lucide-vue-next';
import { useToast } from '../../utils/toast';
import { FileService } from '../../api/services';
import { getCachedAsset, cacheAsset } from '../../utils/assetManager';
import { useSwipe } from '@vueuse/core';

const props = defineProps({
  attachmentId: {
    type: Number,
    required: true
  },
  fileName: {
    type: String,
    required: true
  },
  fileHash: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['close']);
const { showToast } = useToast();
const isCopying = ref(false);
const isImageLoaded = ref(false);
const imageSrc = ref(null);
const showUI = ref(true);

const containerRef = ref(null);
const { isSwiping, lengthY } = useSwipe(containerRef, {
  onSwipeEnd: () => {
    if (Math.abs(lengthY.value) > 100) {
      emit('close');
    }
  }
});

const swipeOpacity = computed(() => {
  if (!isSwiping.value) return 1;
  const ratio = Math.max(0, 1 - Math.abs(lengthY.value) / 400);
  return ratio;
});

const loadFullImage = async () => {
  // 检查全局缓存 (使用物理哈希)
  const cached = getCachedAsset(`raw_${props.fileHash}`);
  if (cached) {
    imageSrc.value = cached;
    isImageLoaded.value = true;
    return;
  }

  try {
    const res = await FileService.download(props.attachmentId);
    const url = cacheAsset(`raw_${props.fileHash}`, new Blob([res.data]));
    imageSrc.value = url;
  } catch (err) {
    showToast('原图获取失败', 'error');
    emit('close');
  }
};

const handleDownload = () => {
  if (!imageSrc.value) return;
  const link = document.createElement('a');
  link.href = imageSrc.value;
  link.download = props.fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('正在开始下载...', 'success');
};

const handleCopy = async () => {
  if (!imageSrc.value) return;
  try {
    isCopying.value = true;
    const response = await fetch(imageSrc.value);
    const blob = await response.blob();
    await navigator.clipboard.write([
      new ClipboardItem({ [blob.type]: blob })
    ]);
    showToast('图片已复制到剪贴板', 'success');
  } catch (err) {
    showToast('复制失败，浏览器可能不支持', 'error');
  } finally {
    isCopying.value = false;
  }
};

onMounted(loadFullImage);
</script>

<template>
  <div ref="containerRef" class="fixed inset-0 z-[500] flex items-center justify-center overflow-hidden touch-none">
    <!-- Dark Backdrop -->
    <div 
      class="absolute inset-0 bg-neutral/95 backdrop-blur-3xl transition-opacity duration-700"
      @click="emit('close')"
    ></div>

    <!-- Ultra-Precision Loading State -->
    <div v-if="!isImageLoaded" class="absolute inset-0 flex flex-col items-center justify-center space-y-6 z-[510] pointer-events-none">
       <div class="relative">
         <div class="w-16 h-20 md:w-20 md:h-24 border-2 border-white/5 rounded-full animate-ping"></div>
         <Loader2 class="absolute inset-0 w-20 h-20 md:w-24 md:h-24 text-primary animate-spin" :style="{ color: 'var(--accent-color)' }" />
         <Maximize2 class="absolute inset-0 m-auto w-6 h-6 md:w-8 md:h-8 text-white/40 animate-pulse" />
       </div>
       <div class="flex flex-col items-center space-y-1 px-4 text-center">
         <span class="text-[10px] md:text-xs font-black text-white uppercase tracking-[0.4em] md:tracking-[0.6em] animate-pulse">Restoring High-Res</span>
         <span class="text-[8px] md:text-[9px] font-mono text-white/30 uppercase tracking-widest">Downloading raw source data...</span>
       </div>
    </div>

    <!-- Image Container (Only Image, Toolbar moved) -->
    <div 
      v-if="imageSrc"
      class="relative max-w-full max-h-full flex flex-col items-center transition-all duration-1000 ease-spring"
      :class="isImageLoaded ? 'opacity-100 scale-100' : 'opacity-0 scale-95'"
      :style="{ opacity: swipeOpacity, transform: isSwiping ? `translateY(${-lengthY}px)` : '' }"
    >
      <img 
        :src="imageSrc" 
        @load="isImageLoaded = true"
        @click="showUI = !showUI"
        class="max-w-[95vw] md:max-w-full max-h-[85vh] object-contain shadow-2xl rounded-lg border border-white/10 cursor-zoom-in"
      />
    </div>

    <!-- Persistent/Togglable Floating Toolbar at Bottom -->
    <Transition
      enter-active-class="transition duration-500 ease-spring"
      enter-from-class="translate-y-20 opacity-0"
      leave-active-class="transition duration-300 ease-in"
      leave-to-class="translate-y-20 opacity-0"
    >
      <div 
        v-if="isImageLoaded && showUI"
        class="absolute bottom-10 md:bottom-12 flex flex-col items-center space-y-4 z-[520]"
      >
        <!-- Mobile Hint (Now above toolbar) -->
        <div class="md:hidden text-[8px] text-white/30 font-mono uppercase tracking-[0.3em] animate-pulse mb-2">
          Swipe to close • Tap image to hide UI
        </div>

        <div class="flex items-center space-x-2 md:space-x-4 px-4 md:px-6 py-2.5 md:py-3 card-glass bg-white/5 border-white/10 shadow-2xl backdrop-blur-2xl shrink-0 mx-4">
          <span class="hidden sm:inline text-[10px] text-white/50 font-mono mr-2 md:mr-4 truncate max-w-[120px] md:max-w-[240px] uppercase tracking-tighter">{{ fileName }}</span>
          
          <button 
            @click="handleCopy"
            :disabled="isCopying"
            class="p-2 text-white/60 hover:text-white hover:bg-white/10 rounded-full transition-all active:scale-90"
            title="复制图片"
          >
            <Loader2 v-if="isCopying" class="w-4 h-4 md:w-5 md:h-5 animate-spin" />
            <Copy v-else class="w-3.5 h-3.5 md:w-4 md:h-4" />
          </button>

          <button 
            @click="handleDownload"
            class="p-2 text-white/60 hover:text-white hover:bg-white/10 rounded-full transition-all active:scale-90"
            title="保存原图"
          >
            <Download class="w-3.5 h-3.5 md:w-4 md:h-4" />
          </button>

          <div class="w-px h-4 bg-white/10 mx-1 md:mx-2"></div>

          <button 
            @click="emit('close')"
            class="p-2 text-white/60 hover:text-red-400 hover:bg-red-500/10 rounded-full transition-all active:scale-90"
          >
            <X class="w-4 h-4 md:w-5 md:h-5" />
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>
