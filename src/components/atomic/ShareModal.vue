<script setup>
import { ref, onMounted } from "vue";
import {
  X,
  Clock,
  MousePointer2 as ClickIcon,
  Share2,
  Loader2,
  FileText,
} from "lucide-vue-next";

const props = defineProps({
  fileName: {
    type: String,
    required: true,
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["close", "confirm"]);

const editableBaseName = ref("");
const editableExtension = ref("");
const hasExtension = ref(false);

onMounted(() => {
  const lastDotIndex = props.fileName.lastIndexOf(".");
  // 确保点号不在开头也不在结尾
  if (lastDotIndex > 0 && lastDotIndex < props.fileName.length - 1) {
    editableBaseName.value = props.fileName.substring(0, lastDotIndex);
    editableExtension.value = props.fileName.substring(lastDotIndex + 1);
    hasExtension.value = true;
  } else {
    editableBaseName.value = props.fileName;
    editableExtension.value = "";
    hasExtension.value = false;
  }
});

const expireOptions = [
  { label: "1 小时", value: 3600 },
  { label: "1 天", value: 86400 },
  { label: "7 天", value: 604800 },
  { label: "永久", value: null },
];

const useOptions = [
  { label: "1 次", value: 1 },
  { label: "5 次", value: 5 },
  { label: "10 次", value: 10 },
  { label: "无限制", value: 0 },
];

const selectedExpire = ref(3600);
const selectedUses = ref(1);

const handleConfirm = () => {
  const finalFileName =
    hasExtension.value && editableExtension.value
      ? `${editableBaseName.value}.${editableExtension.value}`
      : editableBaseName.value;

  emit("confirm", {
    expire_in: selectedExpire.value,
    max_uses: selectedUses.value,
    display_name: finalFileName,
  });
};
</script>

<template>
  <div
    class="fixed inset-0 z-[400] flex items-center justify-center p-6 bg-black/20 backdrop-blur-sm"
    @click.self="emit('close')"
  >
    <div
      class="w-full max-w-sm card-glass p-8 space-y-8 animate-focus relative overflow-hidden"
      style="
        background: linear-gradient(145deg, #f0f4f8, #d9e2ec);
        border-radius: 32px;
        border: 1px solid rgba(255, 255, 255, 0.8);
      "
    >
      <!-- Close Button -->
      <button
        @click="emit('close')"
        class="absolute top-6 right-6 p-2 text-secondary/75 hover:text-secondary transition-colors"
      >
        <X class="w-5 h-5" />
      </button>

      <div class="space-y-6">
        <h3
          class="text-xl font-black text-primary-dark flex items-center space-x-3"
        >
          <Share2 class="w-6 h-6" />
          <span>配置分享权限</span>
        </h3>

        <div class="group">
          <label
            class="block text-[10px] font-black text-secondary/80 uppercase tracking-widest mb-2 ml-1"
            >显示名称 (Display Name)</label
          >

          <!-- Single Input if no extension -->
          <div v-if="!hasExtension" class="relative">
            <FileText
              class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary/40 group-focus-within:text-primary transition-colors"
            />
            <input
              v-model="editableBaseName"
              type="text"
              placeholder="文件名..."
              class="u-hard-input w-full pl-12 pr-4 py-3.5 rounded-2xl bg-black/5 text-sm text-on-surface outline-none focus:bg-white focus:shadow-lg transition-all font-bold"
            />
          </div>

          <!-- Split Inputs if extension exists -->
          <div v-else class="flex items-center space-x-2">
            <div class="flex-1 relative group/name">
              <FileText
                class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary/40 group-focus-within/name:text-primary transition-colors"
              />
              <input
                v-model="editableBaseName"
                type="text"
                placeholder="主文件名"
                class="u-hard-input w-full pl-12 pr-3 py-3.5 rounded-2xl bg-black/5 text-sm text-on-surface outline-none focus:bg-white focus:shadow-lg transition-all font-bold text-right"
              />
            </div>
            <div class="text-secondary/40 font-black text-xl">.</div>
            <div class="w-24 relative group/ext">
              <input
                v-model="editableExtension"
                type="text"
                placeholder="后缀"
                class="u-hard-input w-full px-4 py-3.5 rounded-2xl bg-black/5 text-sm text-primary outline-none focus:bg-white focus:shadow-lg transition-all font-black uppercase tracking-tighter"
                :style="{ color: 'var(--accent-color)' }"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="space-y-6">
        <!-- Expire In -->
        <div class="space-y-3">
          <div
            class="flex items-center space-x-2 text-[10px] font-black uppercase tracking-widest text-secondary/80"
          >
            <Clock class="w-3 h-3" />
            <span>有效期 (Expiration)</span>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="opt in expireOptions"
              :key="opt.label"
              @click="selectedExpire = opt.value"
              :class="[
                'px-4 py-2.5 rounded-xl text-xs font-bold transition-all active:scale-95',
                selectedExpire === opt.value
                  ? 'bg-primary text-white shadow-lg'
                  : 'bg-white/40 text-secondary hover:bg-white/60',
              ]"
              :style="
                selectedExpire === opt.value
                  ? { backgroundColor: 'var(--accent-color)' }
                  : {}
              "
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <!-- Max Uses -->
        <div class="space-y-3">
          <div
            class="flex items-center space-x-2 text-[10px] font-black uppercase tracking-widest text-secondary/80"
          >
            <ClickIcon class="w-3 h-3" />
            <span>下载次数 (Max Uses)</span>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="opt in useOptions"
              :key="opt.label"
              @click="selectedUses = opt.value"
              :class="[
                'px-4 py-2.5 rounded-xl text-xs font-bold transition-all active:scale-95',
                selectedUses === opt.value
                  ? 'bg-primary text-white shadow-lg'
                  : 'bg-white/40 text-secondary hover:bg-white/60',
              ]"
              :style="
                selectedUses === opt.value
                  ? { backgroundColor: 'var(--accent-color)' }
                  : {}
              "
            >
              {{ opt.label }}
            </button>
          </div>
        </div>
      </div>

      <button
        @click="handleConfirm"
        :disabled="isLoading"
        class="w-full btn-primary py-4 rounded-2xl flex items-center justify-center space-x-3 text-sm font-black uppercase tracking-widest shadow-xl"
        :style="{
          backgroundColor: 'var(--accent-color)',
          boxShadow: '0 10px 30px rgba(0,163,255,0.3)',
        }"
      >
        <Loader2 v-if="isLoading" class="w-5 h-5 animate-spin" />
        <span>{{ isLoading ? "正在生成..." : "生成并复制链接" }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.u-hard-input {
  box-shadow: inset 2px 5px 10px rgba(0, 0, 0, 0.05);
}
</style>
