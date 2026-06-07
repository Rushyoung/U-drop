<script setup>
import { AlertTriangle, Info, X } from 'lucide-vue-next';
import { confirmState, handleConfirm } from '../../utils/confirm';
</script>

<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="opacity-0"
    leave-active-class="transition duration-200 ease-in"
    leave-to-class="opacity-0"
  >
    <div v-if="confirmState.show" class="fixed inset-0 z-[1000] flex items-center justify-center p-6 bg-black/20 backdrop-blur-sm" @click.self="handleConfirm(false)">
      <Transition
        enter-active-class="transition duration-500 ease-spring"
        enter-from-class="translate-y-12 opacity-0 scale-95"
        leave-active-class="transition duration-300 ease-in"
        leave-to-class="translate-y-8 opacity-0 scale-105"
      >
        <div 
          v-if="confirmState.show"
          class="w-full max-w-sm card-glass p-8 space-y-6 relative overflow-hidden"
          :class="confirmState.isDanger ? 'border-red-500/30 bg-red-50/10' : 'bg-white/80'"
          style="border-radius: 32px; border: 1px solid rgba(255,255,255,0.8);"
        >
          <!-- Close Button -->
          <button @click="handleConfirm(false)" class="absolute top-6 right-6 p-2 text-secondary/50 hover:text-secondary transition-colors">
            <X class="w-5 h-5" />
          </button>

          <div class="flex items-start space-x-4">
            <div :class="['p-3 rounded-2xl shrink-0 shadow-sm border border-white/40', confirmState.isDanger ? 'bg-red-500/5 text-red-500' : 'bg-primary/5 text-primary']" :style="!confirmState.isDanger ? { color: 'var(--accent-color)' } : {}">
              <AlertTriangle v-if="confirmState.isDanger" class="w-5 h-5 md:w-6 md:h-6" />
              <Info v-else class="w-5 h-5 md:w-6 md:h-6" />
            </div>
            <div class="space-y-2">
              <h3 class="text-xl font-black text-primary-dark tracking-tight">{{ confirmState.title }}</h3>
              <p class="text-sm text-secondary/80 font-medium leading-relaxed">
                {{ confirmState.message }}
              </p>
            </div>
          </div>

          <div class="flex space-x-3 pt-4">
            <button 
              @click="handleConfirm(false)"
              class="flex-1 px-6 py-4 bg-white/60 text-secondary rounded-2xl font-black text-xs uppercase tracking-widest border border-black/5 hover:bg-white transition-all active:scale-95"
            >
              {{ confirmState.cancelText }}
            </button>
            <button 
              @click="handleConfirm(true)"
              :class="['flex-1 px-6 py-4 text-white rounded-2xl font-black text-xs uppercase tracking-widest shadow-xl transition-all active:scale-[0.98]', confirmState.isDanger ? 'bg-red-500 hover:bg-red-600 shadow-red-500/20' : 'bg-primary shadow-primary/20']"
              :style="!confirmState.isDanger ? { backgroundColor: 'var(--accent-color)' } : {}"
            >
              {{ confirmState.confirmText }}
            </button>
          </div>

          <!-- Decorative background for danger -->
          <AlertTriangle v-if="confirmState.isDanger" class="absolute -right-6 -bottom-6 w-32 h-32 text-red-500/5 rotate-12 pointer-events-none" />
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
.ease-spring {
  transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
}
.shadow-key {
  box-shadow: 
    8px 8px 16px rgba(0,0,0,0.05),
    -8px -8px 16px rgba(255,255,255,0.8);
}
</style>
