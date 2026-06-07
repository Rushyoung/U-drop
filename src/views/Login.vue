<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { User as UserIcon, Lock, Loader2, Check } from 'lucide-vue-next';
import { AuthService } from '../api/services';
import { setToken } from '../utils/auth';
import { getDeviceId, getDeviceName } from '../utils/device';

const router = useRouter();
const account = ref('');
const password = ref('');
const rememberMe = ref(false);
const isLoading = ref(false);
const errorMsg = ref('');

const handleLogin = async () => {
  if (!account.value || !password.value) return;
  
  isLoading.value = true;
  errorMsg.value = '';
  
  try {
    const res = await AuthService.login({
      account: account.value,
      password: password.value,
      device_id: getDeviceId(),
      device_type: 0, // Web
      device_name: getDeviceName(),
      remember_me: rememberMe.value
    });
    
    if (res.data.success && res.data.data?.bearer) {
      setToken(res.data.data.bearer, !rememberMe.value);
      router.push('/');
    } else {
      errorMsg.value = res.data.message || '登录失败';
    }
  } catch (err) {
    const detail = err.response?.data?.detail;
    errorMsg.value = Array.isArray(detail) ? detail[0]?.msg : (err.response?.data?.message || '身份验证失败');
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-6 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-slate-50 to-blue-50/50">
    <div class="w-full max-w-md card-glass p-8 space-y-8">
      <div class="text-center">
        <h1 class="text-3xl font-bold text-primary tracking-tight">U-Drop</h1>
        <p class="text-xs font-mono text-secondary mt-2 uppercase tracking-widest">Secure Access</p>
      </div>

      <div class="space-y-4">
        <div class="relative">
          <UserIcon class="absolute left-4 top-3 w-5 h-5 text-secondary/80" />
          <input 
            v-model="account"
            type="text" 
            placeholder="账号" 
            class="w-full bg-white/50 border border-white/60 rounded-global pl-12 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-inter"
          />
        </div>
        <div class="relative">
          <Lock class="absolute left-4 top-3 w-5 h-5 text-secondary/80" />
          <input 
            v-model="password"
            type="password" 
            placeholder="密码" 
            @keyup.enter="handleLogin"
            class="w-full bg-white/50 border border-white/60 rounded-global pl-12 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-inter"
          />
        </div>
      </div>

      <!-- Remember Me Checkbox -->
      <div class="flex items-center space-x-3 px-1 cursor-pointer group select-none" @click="rememberMe = !rememberMe">
        <div 
          :class="[
            'w-5 h-5 rounded-md border-2 transition-all duration-300 flex items-center justify-center flex-shrink-0',
            rememberMe ? 'shadow-[0_0_15px_rgba(0,163,255,0.4)] scale-110' : 'bg-white/50 border-secondary/20 group-hover:border-primary/50'
          ]"
          :style="rememberMe ? { backgroundColor: 'var(--accent-color)', borderColor: 'var(--accent-color)' } : {}"
        >
          <Check v-if="rememberMe" class="w-3.5 h-3.5 text-white stroke-[4px]" />
        </div>
        <div class="flex flex-col">
          <span class="text-xs font-bold text-on-surface">记住我</span>
          <span class="text-[10px] text-secondary/80 uppercase tracking-tighter">开启长效会话 (滑动窗口续期)</span>
        </div>
      </div>

      <div v-if="errorMsg" class="text-red-500 text-xs text-center font-medium animate-pulse">
        {{ errorMsg }}
      </div>

      <button 
        @click="handleLogin"
        :disabled="isLoading"
        class="w-full btn-primary flex items-center justify-center space-x-2 shadow-lg shadow-primary/20"
      >
        <Loader2 v-if="isLoading" class="w-5 h-5 animate-spin" />
        <span>{{ isLoading ? '正在认证...' : '进入系统' }}</span>
      </button>

      <p class="text-center text-sm text-secondary">
        还没有账号？
        <router-link to="/register" class="text-primary font-medium hover:underline">立即注册</router-link>
      </p>
    </div>
  </div>
</template>
