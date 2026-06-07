<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { AuthService } from '../api/services';
import { getDeviceId, getDeviceName } from '../utils/device';
import { Lock, User as UserIcon, Loader2, ShieldCheck } from 'lucide-vue-next';

const router = useRouter();
const account = ref('');
const password = ref('');
const confirmPassword = ref('');
const isLoading = ref(false);
const errorMsg = ref('');

const handleRegister = async () => {
  if (isLoading.value) return;
  if (password.value !== confirmPassword.value) {
    errorMsg.value = '两次输入的密码不一致';
    return;
  }
  
  isLoading.value = true;
  errorMsg.value = '';
  
  try {
    const res = await AuthService.register({
      account: account.value,
      password: password.value,
      device_id: getDeviceId(),
      device_type: 0,
      device_name: getDeviceName()
    });
    
    if (res.data.success && res.data.data?.bearer) {
      localStorage.setItem('udrop_token', res.data.data.bearer);
      router.push('/');
    } else {
      errorMsg.value = res.data.message || '注册失败';
    }
  } catch (err) {
    errorMsg.value = err.response?.data?.detail?.[0]?.msg || '该账号标识已被占用或不符合规范';
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-6 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-slate-50 to-blue-50/50">
    <div class="w-full max-w-md card-glass p-8 space-y-8">
      <div class="text-center">
        <h1 class="text-3xl font-bold text-primary tracking-tight">创建账户</h1>
        <p class="text-xs font-mono text-secondary mt-2 uppercase tracking-widest">Join U-Drop</p>
      </div>

      <div class="space-y-4">
        <div class="relative">
          <UserIcon class="absolute left-4 top-3 w-5 h-5 text-secondary/80" />
          <input 
            v-model="account"
            type="text" 
            placeholder="设置账号" 
            class="w-full bg-white/50 border border-white/60 rounded-global pl-12 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
          />
        </div>
        <div class="relative">
          <Lock class="absolute left-4 top-3 w-5 h-5 text-secondary/80" />
          <input 
            v-model="password"
            type="password" 
            placeholder="设置密码" 
            class="w-full bg-white/50 border border-white/60 rounded-global pl-12 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
          />
        </div>
        <div class="relative">
          <ShieldCheck class="absolute left-4 top-3 w-5 h-5 text-secondary/80" />
          <input 
            v-model="confirmPassword"
            type="password" 
            placeholder="确认密码" 
            class="w-full bg-white/50 border border-white/60 rounded-global pl-12 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
          />
        </div>
      </div>

      <div v-if="errorMsg" class="text-red-500 text-xs text-center font-medium">
        {{ errorMsg }}
      </div>

      <button 
        @click="handleRegister"
        :disabled="isLoading"
        class="w-full btn-primary flex items-center justify-center space-x-2 shadow-lg shadow-primary/20"
      >
        <Loader2 v-if="isLoading" class="w-5 h-5 animate-spin" />
        <span>{{ isLoading ? '正在创建...' : '即刻开始' }}</span>
      </button>

      <p class="text-center text-sm text-secondary">
        已有账号？
        <router-link to="/login" class="text-primary font-medium hover:underline">返回登录</router-link>
      </p>
    </div>
  </div>
</template>
