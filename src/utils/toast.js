/**
 * @typedef {Object} Toast
 * @property {number} id
 * @property {string} message
 * @property {'error'|'success'|'info'} type
 */

import { ref } from 'vue';

const toasts = ref([]);
let counter = 0;

export function useToast() {
  const showToast = (message, type = 'error') => {
    const id = counter++;
    toasts.value.push({ id, message, type });
    
    // 如果是错误类型，同步输出到控制台以便调试
    if (type === 'error') {
      console.error(`[Toast Error] ${message}`);
    } else {
      console.log(`[Toast ${type.toUpperCase()}] ${message}`);
    }
    
    // 4秒后自动消失
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id);
    }, 4000);
  };

  return { toasts, showToast };
}
