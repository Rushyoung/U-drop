<script setup>
import { onMounted, onUnmounted, ref } from 'vue';
import { useContextMenu } from '../../utils/contextMenu';

const { state, closeMenu } = useContextMenu();
const menuRef = ref(null);

const handleItemClick = (action) => {
  action();
  closeMenu();
};

const handleClickOutside = (e) => {
  if (menuRef.value && !menuRef.value.contains(e.target)) {
    closeMenu();
  }
};

onMounted(() => {
  window.addEventListener('mousedown', handleClickOutside);
  window.addEventListener('scroll', closeMenu, true);
});

onUnmounted(() => {
  window.removeEventListener('mousedown', handleClickOutside);
  window.removeEventListener('scroll', closeMenu, true);
});
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-spring"
      enter-from-class="opacity-0 scale-95"
      leave-active-class="transition duration-150 ease-in"
      leave-to-class="opacity-0 scale-98"
    >
      <div 
        v-if="state.show"
        ref="menuRef"
        class="fixed z-[300] min-w-[180px] p-2 rounded-[20px] bg-white/80 backdrop-blur-xl border border-white/40 shadow-[10px_10px_30px_rgba(0,0,0,0.1),-10px_-10px_30px_rgba(255,255,255,0.8)] pointer-events-auto"
        :style="{ left: `${state.x}px`, top: `${state.y}px` }"
      >
        <div class="flex flex-col space-y-1">
          <button 
            v-for="(option, idx) in state.options" 
            :key="idx"
            @click="handleItemClick(option.action)"
            :class="[
              'flex items-center space-x-3 px-4 py-2.5 rounded-[12px] text-[13px] font-bold transition-all active:scale-95',
              option.danger ? 'text-red-500 hover:bg-red-50' : 'text-secondary hover:bg-primary/10 hover:text-primary'
            ]"
          >
            <component :is="option.icon" class="w-4 h-4 opacity-70" v-if="option.icon" />
            <span class="tracking-tight">{{ option.label }}</span>
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.ease-spring {
  transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
}
</style>
