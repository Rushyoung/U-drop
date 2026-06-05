import axios from 'axios';
import { getDeviceId } from '../utils/device';
import { useToast } from '../utils/toast';
import { getToken, clearToken } from '../utils/auth';

const { showToast } = useToast();

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'X-Device-Id': getDeviceId(),
  },
});

client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => {
    const bizData = response.data;
    if (bizData && bizData.success === false) {
      showToast(bizData.message || '操作失败', 'error');
    }
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      clearToken();
      // 避免在登录页死循环
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    } else if (error.response?.status === 403) {
       // 特殊逻辑：如果是系统未初始化导致的 403，强跳 /init
       const bizMessage = error.response?.data?.message || '';
       if (bizMessage.includes('未初始化') || bizMessage.includes('setup')) {
          window.location.href = '/init';
       }
    } else if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      showToast('连接服务器超时，请检查网络', 'error');
    } else {
      // 解析 FastAPI 标准错误格式 (Pydantic 报错使用 .msg)
      const detail = error.response?.data?.detail;
      const message = Array.isArray(detail) 
        ? detail[0]?.msg 
        : (error.response?.data?.message || error.message || '未知服务器错误');
      
      showToast(message, 'error');
    }
    return Promise.reject(error);
  }
);

export default client;
