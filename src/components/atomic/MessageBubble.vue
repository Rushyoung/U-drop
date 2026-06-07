<script setup>
import { computed, ref, onMounted, watch } from 'vue';
import { onLongPress } from '@vueuse/core';
import { 
  FileIcon, Clock, Download, Monitor, Smartphone, 
  Copy, Trash2, Info, Chrome, Compass, Globe, Share2, MonitorSmartphone,
  Loader2
} from 'lucide-vue-next';
import { FileService, ShareService, MessageService } from '../../api/services';
import { useUploadManager } from '../../utils/uploadManager';
import { getDeviceId } from '../../utils/device';
import { useContextMenu } from '../../utils/contextMenu';
import { useToast } from '../../utils/toast';
import { useUser } from '../../utils/user';
import { useSettings } from '../../utils/settings';
import { showConfirm } from '../../utils/confirm';
import { getCachedAsset, cacheAsset } from '../../utils/assetManager';
import ImageOverlay from './ImageOverlay.vue';
import ShareModal from './ShareModal.vue';

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  isSelected: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['deleted']);

const { openMenu } = useContextMenu();
const { showToast } = useToast();
const { fetchUser } = useUser();
const { settings } = useSettings();

const mainCardRef = ref(null);
onLongPress(mainCardRef, (e) => {
  handleContextMenu(e);
}, { delay: 600 });

const showShareModal = ref(false);
const isGeneratingShare = ref(false);
const activeShareHash = ref(null);
const activeShareName = ref(null);
const activeAttachmentId = ref(null);

const handleShareRequest = (attId, hash, name) => {
  activeAttachmentId.value = attId;
  activeShareHash.value = hash;
  activeShareName.value = name;
  showShareModal.value = true;
};

const confirmShare = async (params) => {
  if (activeAttachmentId.value === null) return;
  
  try {
    isGeneratingShare.value = true;
    const res = await ShareService.create({
      attachment_id: activeAttachmentId.value,
      display_name: params.display_name,
      expire_in: params.expire_in,
      max_uses: params.max_uses
    });
    
    if (res.data.success && res.data.data) {
      await navigator.clipboard.writeText(res.data.data.share_url);
      showToast('分享链接已复制到剪贴板', 'success');
      showShareModal.value = false;
    }
  } catch (err) {
    showToast('生成分享链接失败', 'error');
  } finally {
    isGeneratingShare.value = false;
  }
};

const handleContextMenu = (e) => {
  const options = [
    { 
      label: '复制文本', 
      icon: Copy, 
      action: () => {
        const textToCopy = props.message.content || '';
        navigator.clipboard.writeText(textToCopy);
        showToast('文本已复制', 'success');
      }
    },
    {
      label: '查看元数据',
      icon: Info,
      action: () => {
        showToast(`PK: 0X${props.message.id.toString(16).toUpperCase()}`, 'info');
      }
    }
  ];

  if (props.message.attachments.length === 1) {
    const att = props.message.attachments[0];
    options.push({
      label: '生成分享链接',
      icon: Share2,
      action: () => handleShareRequest(att.id, att.file_hash, att.display_name)
    });
    options.push({
      label: '下载附件',
      icon: Download,
      action: () => handleDownload(att.id, att.display_name)
    });
  }

  options.push({
    label: '删除消息',
    icon: Trash2,
    danger: true,
    action: handleDelete
  });

  openMenu(e, options);
};

const currentDeviceId = getDeviceId();
const isOwn = computed(() => {
  const shortId = currentDeviceId.slice(0, 6);
  return props.message.device_name.includes(`[${shortId}]`) || props.message.id < 0;
});

const { tasks } = useUploadManager();
const uploadTask = computed(() => tasks[props.message.id]);
const isUploading = computed(() => !!uploadTask.value && !uploadTask.value.isComplete);
const uploadProgress = computed(() => uploadTask.value?.progress || 0);

const isPending = computed(() => props.message.id < 0);

const isSupportedThumbnail = (mime) => {
  if (!mime) return false;
  const supported = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp'];
  return supported.includes(mime.toLowerCase());
};

const thumbnailUrls = ref({});
const showFullImage = ref(false);
const activeImageHash = ref(null);
const activeImageName = ref(null);
const activeImageId = ref(null);

const loadingRawHashes = ref<Set<string>>(new Set());

const loadThumbnails = async () => {
  for (const att of props.message.attachments) {
    if (isSupportedThumbnail(att.file_info.mime_type)) {
      const cached = getCachedAsset(`thumb_${att.file_hash}`);
      if (cached) {
        thumbnailUrls.value[att.file_hash] = cached;
        continue;
      }

      try {
        const res = await FileService.getThumbnail(att.id);
        const url = cacheAsset(`thumb_${att.file_hash}`, new Blob([res.data]));
        thumbnailUrls.value[att.file_hash] = url;
      } catch (err) {
        console.error('Thumbnail load failed', att.file_hash);
      }
    }
  }
};

const handleImageClick = async (attId, hash, name) => {
  if (isPending.value) return;

  const cachedRaw = getCachedAsset(`raw_${hash}`);
  if (cachedRaw) {
    activeImageHash.value = hash;
    activeImageName.value = name;
    activeImageId.value = attId;
    showFullImage.value = true;
    return;
  }

  if (loadingRawHashes.value.has(hash)) return;
  loadingRawHashes.value.add(hash);

  try {
    const res = await FileService.download(attId);
    cacheAsset(`raw_${hash}`, new Blob([res.data]));
    activeImageHash.value = hash;
    activeImageName.value = name;
    activeImageId.value = attId;
    showFullImage.value = true;
  } catch (err) {
    showToast('高清原图获取失败', 'error');
  } finally {
    loadingRawHashes.value.delete(hash);
  }
};

const handleDownload = async (attId, name) => {
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

const handleDelete = async () => {
  if (isPending.value) return;

  const confirmed = await showConfirm({
    title: '删除消息',
    message: '确定要将此消息移入回收站吗？',
    isDanger: true,
    confirmText: '移入回收站'
  });
  
  if (!confirmed) return;

  try {
    const res = await MessageService.delete(props.message.id);
    if (res.data.success) {
      showToast('已移入回收站', 'success');
      emit('deleted', props.message.id);
      fetchUser();
    }
  } catch (err) {
    showToast('删除失败', 'error');
  }
};

onMounted(loadThumbnails);
watch(() => props.message.attachments, loadThumbnails, { deep: true });

const formattedTime = computed(() => {
  const date = new Date(props.message.timestamp * 1000);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour12: false })}`;
});

const DeviceIcon = computed(() => {
  const name = props.message.device_name.toUpperCase();
  if (name.includes('EDGE')) return MonitorSmartphone;
  if (name.includes('CHROME')) return Chrome;
  if (name.includes('SAFARI')) return Compass;
  if (name.includes('FIREFOX')) return Globe;
  return props.message.device_type === 1 ? Smartphone : Monitor;
});

const parsedContent = computed(() => {
  if (!props.message.content) return [];
  
  const urlRegex = /((?:https?:\/\/|www\.)[^\s]+|[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|cn|io|me|info|biz|dev|cc|tv|icu|top|xyz|link)(?:\/[^\s]*)?|(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:\/[^\s]*)?)/gi;
  const parts = props.message.content.split(urlRegex);
  
  return parts.map(part => {
    const isLink = !!part.match(urlRegex);
    let href = part;
    if (isLink && !/^https?:\/\//i.test(part)) {
      href = `http://${part}`; 
    }
    return {
      text: part,
      isLink,
      href
    };
  });
});
</script>

<template>
  <div v-bind="$attrs">
    <div 
      :class="[
        'flex w-full mb-4 md:mb-10 group/item transition-all duration-500',
        isOwn ? 'justify-end pl-[5%] md:pl-[25%]' : 'justify-start pr-[5%] md:pr-[25%]'
      ]" 
      :data-anchor-id="message.id"
      @contextmenu="handleContextMenu"
    >
      <div :class="['flex flex-col relative max-w-[85vw] md:max-w-full', isOwn ? 'items-end' : 'items-start']">

        <!-- Sender Info -->
        <div class="flex items-center space-x-2 mb-1.5 px-1 text-[10px] md:text-[11px] font-black text-neutral-rich transition-all duration-500 uppercase opacity-70 md:opacity-100">
          <component :is="DeviceIcon" class="w-3 md:w-3.5 h-3 md:h-3.5" />
          <span>{{ message.device_name.replace(/\s\[.*\]$/, '') }}</span>
        </div>

        <!-- Main Card -->
        <div 
          ref="mainCardRef"
          :class="[
            'relative w-auto min-w-[120px] transition-all duration-700 overflow-hidden backdrop-blur-[2px]',
            isPending ? 'opacity-60 scale-[0.98]' : 'hover:-translate-y-0.5 active:scale-[0.99]',
            isSelected ? 'ring-2 ring-white/20' : ''
          ]"
          :style="{
            borderRadius: `${settings.messageBorderRadius}px`,
            background: 'linear-gradient(145deg, var(--card-start), var(--card-end))',
            boxShadow: isSelected 
              ? `0 0 30px color-mix(in srgb, var(--accent-color) 30%, transparent)` 
              : '6px 6px 12px rgba(0,0,0,0.1), -4px -4px 12px rgba(255,255,255,0.05)',
            border: isSelected ? '1px solid white' : '1px solid var(--card-border)'
          }"
          class="px-4 py-3 md:px-8 md:py-6"
        >
          <div v-if="isPending" class="absolute inset-0 bg-white/10 animate-pulse pointer-events-none"></div>

          <div class="relative z-10 text-white">
            <!-- Text Content -->
            <div v-if="message.content" class="text-[14px] md:text-[16px] leading-relaxed font-bold drop-shadow-md mb-3 md:mb-4 last:mb-0 break-words whitespace-pre-wrap overflow-hidden">
              <template v-for="(part, index) in parsedContent" :key="index">
                <a 
                  v-if="part.isLink" 
                  :href="part.href" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="underline decoration-2 underline-offset-2 transition-all hover:opacity-80 active:scale-[0.98] inline-block"
                  :style="{ color: 'var(--accent-color)', textDecorationColor: 'var(--accent-color)' }"
                >
                  {{ part.text }}
                </a>
                <span v-else>{{ part.text }}</span>
              </template>
            </div>

            <!-- Attachments (Type 1: Hybrid) -->
            <div v-if="message.type === 1" class="space-y-3 md:space-y-4">
              <div v-for="att in message.attachments" :key="att.id" class="group/att">
                  <!-- Image Attachment -->
                  <div v-if="isSupportedThumbnail(att.file_info.mime_type)" @click="handleImageClick(att.id, att.file_hash, att.display_name)" class="cursor-pointer">
                      <div class="relative rounded-xl md:rounded-2xl overflow-hidden bg-black/10 min-h-[100px] md:min-h-[120px] w-full md:min-w-[200px] flex items-center justify-center border border-white/20 shadow-inner group/img">
                          <!-- Local Loading Overlay -->
                          <div v-if="loadingRawHashes.has(att.file_hash)" class="absolute inset-0 z-20 bg-primary/20 backdrop-blur-sm flex flex-col items-center justify-center space-y-2">
                            <Loader2 class="w-5 h-5 md:w-6 md:h-6 text-white animate-spin" />
                            <span class="text-[7px] md:text-[8px] font-black uppercase tracking-widest animate-pulse">Fetching Raw</span>
                          </div>
                          
                          <img v-if="thumbnailUrls[att.file_hash]" :src="thumbnailUrls[att.file_hash]" class="max-w-full max-h-[280px] md:max-h-[360px] object-cover transition-all duration-1000 ease-spring group-hover/img:scale-[1.05]" />
                          <div v-else class="flex flex-col items-center space-y-2 opacity-20 p-6 md:p-8 text-white font-mono text-[9px] md:text-[10px]">PREVIEW</div>
                      </div>
                      <div class="flex justify-between items-center mt-1 px-1">
                          <p class="text-[9px] md:text-[10px] text-white/60 truncate italic">{{ att.display_name }}</p>
                          <button @click.stop="handleShareRequest(att.id, att.file_hash, att.display_name)" class="opacity-0 md:group-hover/att:opacity-100 p-1 hover:bg-white/10 rounded transition-all">
                              <Share2 class="w-3 h-3 text-white/60" />
                          </button>
                      </div>
                  </div>
                  
                  <!-- Regular File Attachment -->
                  <div v-else @click="handleDownload(att.id, att.display_name)" class="flex items-center space-x-3 md:space-x-4 p-2.5 md:p-3 bg-black/5 rounded-lg md:rounded-xl border border-white/10 cursor-pointer hover:bg-black/10 transition-all">
                      <div class="p-1.5 md:p-2 bg-white/10 rounded-lg shrink-0">
                          <FileIcon class="w-4 h-4 md:w-5 md:h-5 text-white" />
                      </div>
                      <div class="flex-1 min-w-0">
                          <h4 class="font-bold text-[12px] md:text-[13px] truncate text-white">{{ att.display_name }}</h4>
                          <p class="text-[8px] md:text-[9px] text-white/60 font-mono mt-0.5">{{ (att.file_info.file_size / 1024 / 1024).toFixed(2) }} MB</p>
                      </div>
                      <div class="flex flex-col space-y-1 shrink-0">
                          <Download class="w-3 h-3 md:w-3.5 md:h-3.5 text-white/75" />
                          <button @click.stop="handleShareRequest(att.id, att.file_hash, att.display_name)" class="opacity-0 md:group-hover/att:opacity-100 p-1 hover:bg-white/10 rounded transition-all">
                              <Share2 class="w-3 h-3 text-white/75" />
                          </button>
                      </div>
                  </div>
              </div>

              <!-- Uploading Task Progress -->
              <div v-if="isUploading" class="pt-1.5 md:pt-2">
                  <div class="h-1 w-full bg-black/10 rounded-full overflow-hidden">
                      <div class="h-full bg-white shadow-[0_0_10px_#fff] transition-all duration-500" :style="{ width: `${uploadProgress}%` }"></div>
                  </div>
                  <div class="flex justify-between items-center mt-1.5">
                      <span class="text-[7px] md:text-[8px] font-black italic uppercase text-white/50 tracking-tighter">Transmission</span>
                      <p class="text-[8px] md:text-[10px] text-white font-black italic uppercase tracking-widest drop-shadow-md">
                        {{ uploadProgress }}% 
                      </p>
                  </div>
              </div>
            </div>

            <!-- Metadata Footer -->
            <div class="flex items-center justify-between mt-3 md:mt-5 border-t border-white/10 pt-3 md:pt-4">
              <div class="flex items-center space-x-1.5 md:space-x-2 text-white/80">
                <Clock class="w-3 h-3 md:w-3.5 md:h-3.5 shadow-sm" />
                <span class="text-[10px] md:text-[12px] font-mono font-black tracking-tighter md:tracking-normal">{{ formattedTime }}</span>
              </div>
              <span class="text-[8px] md:text-[9px] font-mono text-white/60 tracking-tighter uppercase">
                #{{ message.id < 0 ? 'STAGED' : message.id.toString(16).toUpperCase() }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Overlays -->
    <Teleport to="body">
      <ImageOverlay v-if="showFullImage && activeImageId" :attachment-id="activeImageId" :file-name="activeImageName || 'image.png'" :file-hash="activeImageHash || ''" @close="showFullImage = false" />
      <ShareModal 
        v-if="showShareModal" 
        :file-name="activeShareName || '文件'" 
        :is-loading="isGeneratingShare"
        @close="showShareModal = false"
        @confirm="confirmShare"
      />
    </Teleport>
  </div>
</template>
