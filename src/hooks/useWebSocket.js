import { ref } from 'vue';
import { getToken } from '../utils/auth';

const socket = ref(null);
const status = ref('disconnected');
const currentSyncSeq = ref(0);
const eventHandlers = new Set();

let reconnectTimer = null;
let heartbeatTimer = null;
let reconnectAttempts = 0;

export function useWebSocket() {
  const connect = () => {
    const token = getToken();
    if (!token) {
      status.value = 'error';
      return;
    }

    if (socket.value || reconnectTimer) return;

    status.value = 'connecting';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/ws?token=${token}`;

    console.log(`[WS] Connecting to ${wsUrl}...`);
    socket.value = new WebSocket(wsUrl);

    socket.value.onopen = () => {
      console.log('[WS] Connection established');
      status.value = 'connected';
      reconnectAttempts = 0;
      startHeartbeat();
    };

    socket.value.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
      } catch (err) {
        console.error('[WS] Failed to parse message:', err);
      }
    };

    socket.value.onclose = () => {
      console.warn('[WS] Connection closed');
      socket.value = null;
      status.value = 'disconnected';
      stopHeartbeat();
      scheduleReconnect();
    };

    socket.value.onerror = (err) => {
      console.error('[WS] Connection error:', err);
      status.value = 'error';
    };
  };

  const handleMessage = (msg) => {
    if (msg.type === 'INIT') {
      currentSyncSeq.value = msg.data?.sync_seq || 0;
      console.log(`[WS] Initialized. Sync Seq: ${currentSyncSeq.value}`);
    }

    if (msg.sync_seq) {
      currentSyncSeq.value = Math.max(currentSyncSeq.value, msg.sync_seq);
    }

    // 分发事件
    eventHandlers.forEach(handler => handler(msg));
  };

  const startHeartbeat = () => {
    stopHeartbeat();
    heartbeatTimer = setInterval(() => {
      if (socket.value?.readyState === WebSocket.OPEN) {
        socket.value.send(JSON.stringify({ type: 'PING' }));
      }
    }, 30000);
  };

  const stopHeartbeat = () => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  };

  const scheduleReconnect = () => {
    if (reconnectTimer) return;
    const delay = Math.min(30000, Math.pow(2, reconnectAttempts) * 1000);
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      reconnectAttempts++;
      connect();
    }, delay);
  };

  const disconnect = () => {
    stopHeartbeat();
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (socket.value) {
      socket.value.close();
      socket.value = null;
    }
    status.value = 'disconnected';
  };

  const onMessage = (handler) => {
    eventHandlers.add(handler);
    return () => eventHandlers.delete(handler);
  };

  return {
    status,
    currentSyncSeq,
    connect,
    disconnect,
    onMessage
  };
}
