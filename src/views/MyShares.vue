<script setup>
import { ref, onMounted } from "vue";
import { ShareService } from "../api/services";
import { useToast } from "../utils/toast";
import DotLoading from "../components/atomic/DotLoading.vue";
import {
  FileIcon,
  Trash2,
  Clock,
  MousePointer2,
  Share2,
  Copy,
  Loader2,
  RotateCw,
} from "lucide-vue-next";

const shares = ref([]);
const isLoading = ref(false);
const isRevoking = ref(null);
const { showToast } = useToast();

const loadShares = async () => {
  try {
    isLoading.value = true;
    const res = await ShareService.list();
    if (res.data.success && res.data.data) {
      shares.value = res.data.data;
    }
  } catch (err) {
    console.error("Failed to load shares");
  } finally {
    isLoading.value = false;
  }
};

const handleRevoke = async (shareId) => {
  try {
    isRevoking.value = shareId;
    const res = await ShareService.revoke(shareId);
    if (res.data.success) {
      showToast("分享票据已成功撤销", "success");
      shares.value = shares.value.filter((s) => s.share_id !== shareId);
    }
  } catch (err) {
    showToast("撤销操作失败", "error");
  } finally {
    isRevoking.value = null;
  }
};

const copyLink = (shareId) => {
  const url = `${window.location.origin}/share/${shareId}`;
  navigator.clipboard.writeText(url);
  showToast("分享 URL 已复制至剪贴板", "success");
};

const formatTime = (ts) => {
  if (!ts) return "永久有效";
  const date = new Date(ts * 1000);
  return date.toLocaleString();
};

onMounted(loadShares);
</script>

<template>
  <div class="flex-1 overflow-y-auto p-12 bg-transparent">
    <div class="max-w-5xl mx-auto space-y-8">
      <header class="flex justify-between items-end mb-12">
        <div class="space-y-2">
          <h1
            class="text-4xl font-black text-primary-dark tracking-tighter uppercase"
          >
            My Shares
          </h1>
          <p class="text-sm text-secondary/85 font-medium tracking-wide">
            管理您创建的所有临时下载凭据
          </p>
        </div>
        <button
          @click="loadShares"
          :disabled="isLoading"
          class="p-4 rounded-2xl bg-white/50 hover:bg-white transition-all shadow-ambient active:scale-95 disabled:opacity-50"
        >
          <Loader2 v-if="isLoading" class="w-5 h-5 animate-spin text-primary" />
          <RotateCw v-else class="w-5 h-5 text-primary" />
        </button>
      </header>

      <!-- List Content -->
      <div
        v-if="isLoading"
        class="card-glass p-20 flex flex-col items-center justify-center space-y-4"
      >
        <DotLoading />
        <p
          class="text-[10px] font-black uppercase tracking-[0.2em] text-secondary/75 animate-pulse"
        >
          正在载入分享凭据...
        </p>
      </div>

      <!-- Empty State -->
      <div
        v-else-if="shares.length === 0"
        class="card-glass p-20 flex flex-col items-center justify-center space-y-6 text-center"
      >
        <div class="p-6 bg-primary/5 rounded-full">
          <Share2 class="w-12 h-12 text-primary/20" />
        </div>
        <div class="space-y-1">
          <h3 class="text-xl font-bold text-on-surface">暂无分享记录</h3>
          <p class="text-sm text-secondary/75">
            在时间线中右键点击文件即可创建分享链接
          </p>
        </div>
      </div>

      <!-- Share Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          v-for="share in shares"
          :key="share.share_id"
          class="card-glass p-6 group transition-all hover:scale-[1.005] active:scale-[0.99] flex flex-col justify-between space-y-6 hover:shadow-[0_0_30px_rgba(0,163,255,0.15)] hover:bg-white/50 hover:border-primary/20"
        >
          <div class="space-y-4">
            <div class="flex items-start justify-between">
              <div class="p-3 bg-primary/10 rounded-2xl">
                <FileIcon class="w-6 h-6 text-primary" />
              </div>
              <div
                class="flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <button
                  @click="copyLink(share.share_id)"
                  class="p-2 hover:bg-primary/10 text-primary rounded-xl transition-colors shadow-sm bg-white/50"
                  title="复制链接"
                >
                  <Copy class="w-4 h-4" />
                </button>
                <button
                  @click="handleRevoke(share.share_id)"
                  :disabled="isRevoking === share.share_id"
                  class="p-2 hover:bg-red-50 text-red-500 rounded-xl transition-colors shadow-sm bg-white/50"
                  title="撤销分享"
                >
                  <Loader2
                    v-if="isRevoking === share.share_id"
                    class="w-4 h-4 animate-spin"
                  />
                  <Trash2 v-else class="w-4 h-4" />
                </button>
              </div>
            </div>

            <div>
              <h4
                class="font-bold text-lg text-primary-dark truncate mb-1"
                :title="share.display_name || share.target_payload"
              >
                {{ share.display_name || share.target_payload }}
              </h4>
              <p
                class="text-[10px] font-mono text-secondary/75 uppercase tracking-widest"
              >
                Hash ID: {{ share.target_payload.slice(0, 16) }}...
              </p>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 pt-6 border-t border-black/5">
            <div class="flex items-center space-x-2">
              <div class="p-1.5 bg-green-500/10 rounded-lg">
                <MousePointer2 class="w-3 h-3 text-green-600" />
              </div>
              <div class="flex flex-col">
                <span class="text-[10px] font-black text-secondary/75 uppercase"
                  >使用情况</span
                >
                <span class="text-xs font-bold text-on-surface"
                  >{{ share.use_count }} /
                  {{ share.max_uses === 0 ? "∞" : share.max_uses }}</span
                >
              </div>
            </div>
            <div class="flex items-center space-x-2">
              <div class="p-1.5 bg-orange-500/10 rounded-lg">
                <Clock class="w-3 h-3 text-orange-600" />
              </div>
              <div class="flex flex-col">
                <span class="text-[10px] font-black text-secondary/75 uppercase"
                  >失效时间</span
                >
                <span
                  class="text-xs font-bold text-on-surface truncate"
                  :title="formatTime(share.expire_time)"
                >
                  {{
                    share.expire_time
                      ? new Date(share.expire_time * 1000).toLocaleDateString()
                      : "永久"
                  }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
