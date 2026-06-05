import { ref } from 'vue';

export interface Toast {
  id: number;
  message: string;
  type: 'error' | 'success' | 'info';
}

const toasts = ref<Toast[]>([]);
let counter = 0;

export function useToast() {
  const showToast = (message: string, type: Toast['type'] = 'error') => {
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
