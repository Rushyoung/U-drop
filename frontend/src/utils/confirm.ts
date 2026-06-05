import { reactive } from 'vue';

interface ConfirmState {
  show: boolean;
  title: string;
  message: string;
  confirmText: string;
  cancelText: string;
  isDanger: boolean;
  resolve: (value: boolean) => void;
}

export const confirmState = reactive<ConfirmState>({
  show: false,
  title: '确认操作',
  message: '',
  confirmText: '确定',
  cancelText: '取消',
  isDanger: false,
  resolve: () => {}
});

export function showConfirm(options: {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  isDanger?: boolean;
}): Promise<boolean> {
  return new Promise((resolve) => {
    confirmState.title = options.title || (options.isDanger ? '高危操作确认' : '确认操作');
    confirmState.message = options.message;
    confirmState.confirmText = options.confirmText || '确定';
    confirmState.cancelText = options.cancelText || '取消';
    confirmState.isDanger = !!options.isDanger;
    confirmState.resolve = resolve;
    confirmState.show = true;
  });
}

export function handleConfirm(value: boolean) {
  confirmState.show = false;
  confirmState.resolve(value);
}
