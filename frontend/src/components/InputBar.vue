<script setup lang="ts">
import { ref, computed } from 'vue';
import { Send, Paperclip, X, FileText, CheckCircle2, RotateCw, ArrowDown } from 'lucide-vue-next';
import { MessageService } from '../api/services';
import { useUpload } from '../hooks/useUpload';
import { calculateSparseMd5 } from '../utils/hash';
import { getDeviceId } from '../utils/device';

const text = ref('');
const fileInput = ref<HTMLInputElement | null>(null);
const pendingFiles = ref<File[]>([]);
const hashingCount = ref(0);
const isPreHashing = computed(() => hashingCount.value > 0);
const hasPreHashed = computed(() => pendingFiles.value.length > 0 && hashingCount.value === 0);

const { startUpload } = useUpload();
const props = defineProps<{
  timeline: any; // 传入 timeline 实例以便直接操作
}>();

const emit = defineEmits(['message-sent']);

const handleFileSelect = async (e: Event) => {
  const target = e.target as HTMLInputElement;
  const files = Array.from(target.files || []);
  if (files.length === 0) return;
  externalSetFiles(files);
};

/**
 * 暴露给外部（如 Home.vue 的拖拽逻辑）使用的文件注入接口
 */
const externalSetFiles = (files: File[]) => {
  const newFiles = [...pendingFiles.value, ...files];
  // 简单的去重逻辑 (基于文件名和大小)
  const uniqueFiles = newFiles.filter((file, index, self) =>
    index === self.findIndex((f) => f.name === file.name && f.size === file.size)
  );
  
  pendingFiles.value = uniqueFiles;
  
  // 对新加入的文件异步计算哈希
  files.forEach(file => {
    hashingCount.value++;
    calculateSparseMd5(file).then(() => {
      hashingCount.value--;
    }).catch(() => {
      hashingCount.value--;
    });
  });
};

const removeFile = (index: number) => {
  pendingFiles.value.splice(index, 1);
  if (fileInput.value) fileInput.value.value = '';
};

const clearAllFiles = () => {
  pendingFiles.value = [];
  if (fileInput.value) fileInput.value.value = '';
};

const handleSend = async () => {
  const currentText = text.value;
  const currentFiles = [...pendingFiles.value];

  if (!currentText.trim() && currentFiles.length === 0) return;

  text.value = '';
  clearAllFiles();

  // 为本地占位生成一个临时的负数 ID
  const tempId = -Date.now();

  if (currentFiles.length > 0) {
    // 1. 乐观展示文件占位
    props.timeline.addOptimisticMessage({
      id: tempId,
      type: 1, // 混合/附件模式
      content: currentText || null,
      timestamp: Math.floor(Date.now() / 1000),
      device_name: `Web Browser [${getDeviceId().slice(0, 6)}]`,
      device_type: 0,
      tags: [],
      attachments: [] // 初始化为空列表
    });

    // 2. 异步上传
    startUpload(currentFiles, currentText, (msgId) => {
      // 获得正式 ID 的瞬间，原地更新本地卡片
      props.timeline.updateMessageId(tempId, msgId);
    }).then(async (finalId) => {
       if (finalId) {
         // 上传完成后的双重同步策略：
         // 1. 立即精准重载该消息，以获取后端生成的 attachments 和 mime_type 信息
         await props.timeline.refreshMessage(finalId);
         // 2. 触发常规增量拉取，确保同步该消息之后的任何新内容
         await props.timeline.loadMoreAfter();
       } else {
         props.timeline.removeMessage(tempId);
       }
    });
  } else {
    // 纯文本：乐观展示 + 实时发送
    props.timeline.addOptimisticMessage({
      id: tempId,
      type: 0,
      content: currentText,
      timestamp: Math.floor(Date.now() / 1000),
      device_name: `Web Browser [${getDeviceId().slice(0, 6)}]`,
      device_type: 0,
      tags: [],
      attachments: []
    });

    try {
      const res = await MessageService.create({ content: currentText, type: 0 });
      if (res.data.success) {
        props.timeline.removeMessage(tempId);
        await props.timeline.loadMoreAfter();
      }
    } catch (err) {
      props.timeline.removeMessage(tempId);
      console.error(err);
    }
  }
};

defineExpose({
  externalSetFiles,
  // 兼容旧的单文件调用
  externalSetFile: (file: File) => externalSetFiles([file])
});
</script>

<template>
  <div class="relative w-full flex flex-col items-center z-50 pointer-events-none">
    
    <!-- Pending Files List -->
    <Transition
      enter-active-class="transition duration-300 ease-spring"
      enter-from-class="translate-y-4 opacity-0 scale-95"
      leave-active-class="transition duration-200 ease-in"
      leave-to-class="translate-y-2 opacity-0"
    >
      <div v-if="pendingFiles.length > 0" class="w-full max-w-lg mb-3 pointer-events-auto space-y-2 px-2">
        <div v-for="(file, idx) in pendingFiles" :key="file.name + file.size" class="card-glass p-2 md:p-3 flex items-center space-x-3 shadow-key bg-white/90 backdrop-blur-2xl">
          <div class="p-1.5 md:p-2 bg-primary/10 rounded-lg shrink-0">
            <FileText class="w-3.5 h-3.5 md:w-4 md:h-4 text-primary" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-[10px] md:text-xs font-medium text-on-surface truncate">{{ file.name }}</p>
            <p class="text-[8px] md:text-[9px] text-secondary/85 font-mono uppercase">{{ (file.size / 1024 / 1024).toFixed(2) }} MB</p>
          </div>
          <button @click="removeFile(idx)" class="p-1 hover:bg-red-50 text-secondary/75 hover:text-red-500 rounded-full transition-colors shrink-0">
            <X class="w-3 md:w-3.5 h-3 md:h-3.5" />
          </button>
        </div>
        <!-- Status Bar -->
        <div class="px-4 py-1 flex items-center justify-between">
             <div class="flex items-center space-x-2">
                <span v-if="isPreHashing" class="text-[8px] md:text-[10px] text-primary animate-pulse flex items-center">
                    <RotateCw class="w-2 h-2 mr-1 animate-spin" /> 正在预检 {{ hashingCount }} 个文件...
                </span>
                <span v-if="hasPreHashed" class="text-[8px] md:text-[10px] text-green-600 flex items-center font-medium">
                    <CheckCircle2 class="w-2 h-2 mr-1" /> {{ pendingFiles.length }} 就绪
                </span>
             </div>
             <button v-if="pendingFiles.length > 1" @click="clearAllFiles" class="text-[8px] md:text-[10px] text-secondary/75 hover:text-secondary underline decoration-dotted">清除</button>
        </div>
      </div>
    </Transition>

    <!-- Main Input Bar -->
    <div class="w-full max-w-2xl flex items-center space-x-2 md:space-x-3 pointer-events-auto p-2 md:p-4">
      <button 
        @click="fileInput?.click()"
        :class="[
          'p-3 md:p-4 transition-all rounded-[12px] md:rounded-[15px] shadow-[inset_2px_5px_10px_rgba(0,0,0,0.1)] bg-[#ccc] hover:bg-white active:scale-95 duration-300 shrink-0',
          pendingFiles.length > 0 ? 'text-green-600 bg-white' : 'text-secondary/85'
        ]"
      >
        <Paperclip v-if="pendingFiles.length === 0" class="w-4 h-4 md:w-5 md:h-5" />
        <CheckCircle2 v-else class="w-4 h-4 md:w-5 md:h-5" />
      </button>

      <div class="flex-1 relative group">
        <input 
          v-model="text"
          @keyup.enter="handleSend"
          class="u-hard-input w-full border-none outline-none rounded-[12px] md:rounded-[15px] p-3 md:p-4 bg-[#ccc] text-xs md:text-sm text-on-surface placeholder-secondary/80 font-inter transition-all duration-300"
          :placeholder="pendingFiles.length > 0 ? '描述...' : '输入指令或发送文件...'" 
        />
      </div>

      <input 
        type="file" 
        ref="fileInput" 
        class="hidden" 
        multiple
        @change="handleFileSelect"
      />

      <button 
        @click="handleSend"
        :disabled="!text.trim() && pendingFiles.length === 0"
        class="p-3 md:p-4 text-white rounded-[12px] md:rounded-[15px] hover:scale-105 active:scale-95 transition-all duration-300 shadow-lg disabled:opacity-30 flex-shrink-0"
        :style="{ backgroundColor: 'var(--accent-color)' }"
      >
        <Send class="w-4 h-4 md:w-5 md:h-5" />
      </button>

      <!-- Back to Latest Button -->
      <Transition
        enter-active-class="transition duration-500 ease-spring"
        enter-from-class="translate-x-12 opacity-0 scale-50"
        leave-active-class="transition duration-300 ease-in"
        leave-to-class="translate-y-4 opacity-0 scale-95"
      >
        <button 
          v-if="timeline?.showScrollButton"
          @click="timeline?.jumpToLatest()"
          class="btn-latest-pop flex-shrink-0 ml-1 md:ml-2"
        >
          <ArrowDown class="w-3 h-3 md:w-4 md:h-4" />
          <span class="hidden md:inline">最新</span>
        </button>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.u-hard-input {
  box-shadow: inset 2px 5px 10px rgba(0,0,0,0.3);
}

.u-hard-input:focus {
  background-color: white;
  transform: scale(1.02);
  box-shadow: 
    13px 13px 60px rgba(150, 150, 150, 0.5), 
    -13px -13px 60px rgba(255, 255, 255, 0.8);
  outline: none;
}

.ease-spring {
  transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
}
</style>
