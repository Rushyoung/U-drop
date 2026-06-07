<template>
  <div class="flex items-center justify-center space-x-1.5 py-4">
    <div
      v-for="i in 3"
      :key="i"
      class="w-1.5 h-1.5 md:w-2 md:h-2 rounded-full bg-primary animate-dot-flow"
      :style="{
        backgroundColor: 'var(--accent-color)',
        animationDelay: `${(i - 1) * 0.2}s`,
      }"
    ></div>
  </div>
</template>

<style scoped>
@keyframes dot-flow {
  0%,
  100% {
    transform: translateY(0) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: translateY(-4px) scale(1.2);
    opacity: 1;
    box-shadow: 0 4px 10px var(--accent-color);
  }
}

.animate-dot-flow {
  animation: dot-flow 1.4s ease-in-out infinite;
}
</style>
