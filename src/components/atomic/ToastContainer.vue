<script setup>
import { useToast } from "../../utils/toast";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-vue-next";

const { toasts } = useToast();

const remove = (id) => {
  const index = toasts.value.findIndex((t) => t.id === id);
  if (index !== -1) toasts.value.splice(index, 1);
};
</script>

<template>
  <div
    class="fixed top-8 left-1/2 -translate-x-1/2 z-[100] flex flex-col space-y-3 pointer-events-none items-center w-full max-w-xl"
  >
    <TransitionGroup
      enter-active-class="transition-all duration-500 ease-spring"
      enter-from-class="-translate-y-12 opacity-0 scale-90"
      leave-active-class="transition-all duration-300 ease-in"
      leave-to-class="-translate-y-8 opacity-0 scale-95"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto group card-glass px-5 py-4 min-w-[300px] max-w-md flex items-start space-x-3 shadow-key relative overflow-hidden"
      >
        <!-- Type Indicator Bar -->
        <div
          :class="[
            'absolute left-0 top-0 bottom-0 w-1',
            toast.type === 'error'
              ? 'bg-red-500'
              : toast.type === 'success'
                ? 'bg-green-500'
                : 'bg-primary',
          ]"
        ></div>

        <div class="flex-shrink-0 mt-0.5">
          <AlertCircle
            v-if="toast.type === 'error'"
            class="w-5 h-5 text-red-500"
          />
          <CheckCircle2
            v-else-if="toast.type === 'success'"
            class="w-5 h-5 text-green-500"
          />
          <Info v-else class="w-5 h-5 text-primary" />
        </div>

        <div class="flex-1">
          <p class="text-sm font-medium text-on-surface leading-tight">
            {{ toast.message }}
          </p>
        </div>

        <button
          @click="remove(toast.id)"
          class="text-secondary/40 hover:text-on-surface transition-colors"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
