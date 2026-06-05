import { reactive } from 'vue';

export interface MenuOption {
  label: string;
  icon?: any;
  action: () => void;
  danger?: boolean;
}

interface ContextMenuState {
  show: boolean;
  x: number;
  y: number;
  options: MenuOption[];
}

export const contextMenuState = reactive<ContextMenuState>({
  show: false,
  x: 0,
  y: 0,
  options: []
});

export function useContextMenu() {
  const openMenu = (e: MouseEvent, options: MenuOption[]) => {
    e.preventDefault();
    contextMenuState.show = false; // 先关闭旧的
    
    // 确保在 nextTick 执行以触发动画
    setTimeout(() => {
      contextMenuState.x = e.clientX;
      contextMenuState.y = e.clientY;
      contextMenuState.options = options;
      contextMenuState.show = true;
    }, 10);
  };

  const closeMenu = () => {
    contextMenuState.show = false;
  };

  return { openMenu, closeMenu, state: contextMenuState };
}
