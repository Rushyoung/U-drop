import { ref } from "vue";
import { MessageService } from "../api/services";
import { getLastAnchor } from "../utils/device";
import { useToast } from "../utils/toast";
import { useWebSocket } from "./useWebSocket";

export function useTimeline() {
  const { showToast } = useToast();
  const { onMessage, status: wsStatus, currentSyncSeq } = useWebSocket();
  const messages = ref([]);
  const isLoading = ref(false);
  const hasMoreBefore = ref(true);
  let pollTimer = null;
  let isDestroyed = false;
  /**
   * 核心：幂等合并消息列表
   */
  const upsertMessages = (newMsgs) => {
    if (isDestroyed) return;

    console.log(
      `[Timeline Diagnostic] upsertMessages called with ${newMsgs.length} messages.`,
    );
    const msgMap = new Map(messages.value.map((m) => [m.id, m]));
    newMsgs.forEach((m) => {
      console.log(
        `[Timeline Diagnostic] Merging ID: ${m.id}. Attachments: ${m.attachments?.length || 0}`,
      );
      msgMap.set(m.id, m);
    });

    const merged = Array.from(msgMap.values()).sort(
      (a, b) => a.timestamp - b.timestamp,
    );
    messages.value = merged;
  };

  const loadMessages = async (mode = "initial", anchorId) => {
    if (isDestroyed || (isLoading.value && mode !== "after")) return;
    if (mode !== "after") isLoading.value = true;

    try {
      // 关键修正：只有在明确为 undefined 时才读取本地锚点。
      // 如果传入 null，说明调用者（如 jumpToLatest）想要绝对最新的消息。
      const targetAnchor =
        mode === "initial" && anchorId === undefined
          ? getLastAnchor()
          : anchorId;

      console.log(`[Timeline] Loading ${mode} with anchor: ${targetAnchor}`);

      const response = await MessageService.list({
        mode,
        anchor_id: targetAnchor,
        limit: 50,
      });

      if (!isDestroyed && response.data.success && response.data.data) {
        const fetchedMsgs = [...response.data.data].reverse();

        if (mode === "initial") {
          messages.value = fetchedMsgs;
          if (fetchedMsgs.length > 0) {
            showToast(`已同步 ${fetchedMsgs.length} 条消息`, "success");
          }
        } else {
          upsertMessages(fetchedMsgs);
        }
      }
    } finally {
      if (!isDestroyed && mode !== "after") isLoading.value = false;
    }
  };

  const addOptimisticMessage = (msg) => {
    upsertMessages([msg]);
  };

  /**
   * 原地转正：强制触发 Vue 的 Key 变更，确保组件彻底重载并看清最新的 attachments
   */
  const updateMessageId = (oldId, newId) => {
    const index = messages.value.findIndex((m) => m.id === oldId);
    if (index !== -1) {
      console.log(
        `[Timeline Diagnostic] PROMOTING ${oldId} -> ${newId}. Reference updated.`,
      );
      // 关键：创建全新的对象引用，确保 v-for 的 :key 侦测到物理变更
      const updatedMsg = { ...messages.value[index], id: newId };
      messages.value[index] = updatedMsg;
      messages.value = [...messages.value];
    } else {
      console.warn(
        `[Timeline Diagnostic] Promotion FAILED: Temp ID ${oldId} not found.`,
      );
    }
  };

  const removeMessage = (id) => {
    if (isDestroyed) return;
    messages.value = messages.value.filter((m) => m.id !== id);
  };

  const startPolling = () => {
    if (isDestroyed) return;
    stopPolling();

    // 如果 WS 已连接，降低轮询频率作为冗余校验
    const interval = wsStatus.value === "connected" ? 30000 : 5000;

    pollTimer = setInterval(() => {
      if (isDestroyed) {
        stopPolling();
        return;
      }
      if (messages.value.length > 0) {
        loadMoreAfter();
      }
    }, interval);
  };

  // 监听 WebSocket 事件
  const cleanupWS = onMessage((msg) => {
    // 对账检查：如果序列号跳跃，说明断线期间有消息丢失
    if (
      msg.sync_seq &&
      msg.sync_seq > currentSyncSeq.value + 1 &&
      currentSyncSeq.value !== 0
    ) {
      console.warn(`[Timeline] Sync Seq Gap detected! Recovering...`);
      loadMoreAfter(); // 立即补齐
    }

    switch (msg.type) {
      case "MSG_NEW":
        if (msg.data?.message_id) {
          console.log(
            `[Timeline] Real-time NEW_MESSAGE: ${msg.data.message_id}`,
          );
          refreshMessage(msg.data.message_id);
        }
        break;
      case "MSG_DELETE":
        if (msg.data?.message_id) {
          console.log(
            `[Timeline] Real-time MESSAGE_DELETED: ${msg.data.message_id}`,
          );
          removeMessage(msg.data.message_id);
        }
        break;
      case "DEVICE_UPDATE":
        if (msg.data?.device_id && msg.data?.device_name) {
          console.log(
            `[Timeline] Real-time DEVICE_UPDATE: ${msg.data.device_id} -> ${msg.data.device_name}`,
          );
          const { device_id, device_name } = msg.data;
          // 更新本地缓存中该设备的所有消息显示名称
          // 注意：device_id 匹配是通过 device_name 后缀中的 [shortId] 还是全量？
          // 后端推送的是原始 device_id
          messages.value = messages.value.map((m) => {
            if (m.device_name.includes(`[${device_id.slice(0, 6)}]`)) {
              // 重新合成名称，保持后缀
              const suffix = m.device_name.split(" ").pop();
              return { ...m, device_name: `${device_name} ${suffix}` };
            }
            return m;
          });
        }
        break;
    }
  });

  const stopPolling = () => {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  };

  const destroy = () => {
    isDestroyed = true;
    stopPolling();
    cleanupWS();
  };

  const loadMoreBefore = () => {
    if (isDestroyed || !hasMoreBefore.value || messages.value.length === 0)
      return;
    const oldestId = messages.value.find((m) => m.id > 0)?.id;
    if (oldestId) loadMessages("before", oldestId);
  };

  const loadMoreAfter = async () => {
    if (isDestroyed) return;
    const realMsgs = messages.value.filter((m) => m.id > 0);
    const newestId =
      realMsgs.length > 0 ? realMsgs[realMsgs.length - 1].id : null;
    return loadMessages("after", newestId);
  };

  /**
   * 刷新单条消息：用于上传完成后拉取完整的附件信息
   */
  const refreshMessage = async (messageId) => {
    try {
      console.log(
        `[Timeline Diagnostic] refreshMessage requesting ID: ${messageId}`,
      );
      // 拉取 3 条以确保覆盖锚点，防止后端游标偏移
      const response = await MessageService.list({
        mode: "initial",
        anchor_id: messageId,
        limit: 3,
      });
      if (!isDestroyed && response.data.success && response.data.data) {
        console.log(
          `[Timeline Diagnostic] refreshMessage received ${response.data.data.length} items`,
        );
        upsertMessages(response.data.data);
      }
    } catch (err) {
      console.error(`Failed to refresh message ${messageId}:`, err);
    }
  };

  return {
    messages,
    isLoading,
    loadMessages,
    loadMoreBefore,
    loadMoreAfter,
    startPolling,
    stopPolling,
    addOptimisticMessage,
    updateMessageId,
    refreshMessage,
    removeMessage,
    destroy,
  };
}
