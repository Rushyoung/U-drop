<script setup lang="ts">
import { ref, computed } from 'vue';
import { 
  User, 
  Lock, 
  ChevronRight, 
  ChevronLeft, 
  Settings, 
  CheckCircle2, 
  ShieldCheck,
  Loader2,
  AlertCircle
} from 'lucide-vue-next';
import { SystemService } from '../api/services';
import { useToast } from '../utils/toast';

const { showToast } = useToast();

const currentStep = ref(1);
const totalSteps = 3;
const isSubmitting = ref(false);
const slideDirection = ref('slide-right');

const formData = ref({
  account: '',
  password: '',
  confirmPassword: '',
  allow_registration: true,
  auth_rate_limit: 5,
  default_token_expire: 86400
});

const nextStep = () => {
  if (currentStep.value < totalSteps) {
    slideDirection.value = 'slide-right';
    currentStep.value++;
  }
};

const prevStep = () => {
  if (currentStep.value > 1) {
    slideDirection.value = 'slide-left';
    currentStep.value--;
  }
};

const isStepValid = computed(() => {
  if (currentStep.value === 1) {
    return formData.value.account.length >= 4 && formData.value.account.length <= 32;
  }
  if (currentStep.value === 2) {
    return formData.value.password.length >= 8 && formData.value.password === formData.value.confirmPassword;
  }
  return true;
});

const handleInitialize = async () => {
  if (!isStepValid.value) return;
  
  try {
    isSubmitting.value = true;
    const res = await SystemService.setup({
      account: formData.value.account,
      password: formData.value.password,
      allow_registration: formData.value.allow_registration,
      auth_rate_limit: formData.value.auth_rate_limit,
      default_token_expire: formData.value.default_token_expire
    });

    if (res.data.success) {
      showToast('系统初始化成功，即将跳转登录', 'success');
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
    } else {
      showToast(res.data.message || '初始化失败', 'error');
    }
  } catch (err: any) {
    const msg = err.response?.data?.message || '网络连接异常';
    showToast(msg, 'error');
  } finally {
    isSubmitting.value = false;
  }
};

const passwordStrength = computed(() => {
  const p = formData.value.password;
  if (!p) return 0;
  let strength = 0;
  if (p.length >= 8) strength += 25;
  if (/[A-Z]/.test(p)) strength += 25;
  if (/[0-9]/.test(p)) strength += 25;
  if (/[^A-Za-z0-9]/.test(p)) strength += 25;
  return strength;
});

const strengthColor = computed(() => {
  const s = passwordStrength.value;
  if (s <= 25) return '#ef4444';
  if (s <= 50) return '#f97316';
  if (s <= 75) return '#eab308';
  return '#22c55e';
});
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4 md:p-8 bg-[#aed9f4]">
    <!-- Background Decor -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] rounded-full bg-white/20 blur-[120px]"></div>
      <div class="absolute -bottom-[10%] -right-[10%] w-[40%] h-[40%] rounded-full bg-primary/20 blur-[120px]" :style="{ backgroundColor: 'var(--accent-color)22' }"></div>
    </div>

    <div class="w-full max-w-md relative z-10">
      <!-- Logo/Header -->
      <div class="text-center mb-8 md:mb-12">
        <div class="w-16 h-16 md:w-20 md:h-20 bg-white rounded-[24px] md:rounded-[30px] mx-auto flex items-center justify-center shadow-key mb-4 md:mb-6 animate-float">
          <ShieldCheck class="w-8 h-8 md:w-10 md:h-10 text-primary" :style="{ color: 'var(--accent-color)' }" />
        </div>
        <h1 class="text-2xl md:text-3xl font-black text-primary-dark tracking-tighter uppercase mb-2">System Setup</h1>
        <p class="text-[10px] md:text-xs font-mono text-secondary uppercase tracking-[0.3em] opacity-60">Initializing Core Services</p>
      </div>

      <!-- Main Wizard Card -->
      <div class="card-glass p-8 md:p-10 relative overflow-hidden">
        <!-- Progress Dots -->
        <div class="flex justify-center space-x-3 mb-10">
          <div 
            v-for="i in totalSteps" 
            :key="i"
            :class="[
              'h-1.5 rounded-full transition-all duration-500',
              currentStep === i ? 'w-8 bg-primary shadow-[0_0_10px_rgba(0,163,255,0.5)]' : 'w-2 bg-white/30'
            ]"
            :style="currentStep === i ? { backgroundColor: 'var(--accent-color)' } : {}"
          ></div>
        </div>

        <div class="relative min-h-[280px]">
          <Transition :name="slideDirection" mode="out-in">
            <!-- Step 1: Account -->
            <div v-if="currentStep === 1" :key="1" class="space-y-6">
              <div class="space-y-2">
                <h2 class="text-lg font-bold text-primary-dark">创建管理员账号</h2>
                <p class="text-xs text-secondary/85">此账号将拥有系统的最高权限，请谨慎设置。</p>
              </div>
              <div class="group">
                <label class="block text-[10px] font-black text-secondary/75 uppercase tracking-widest mb-2 ml-1">Admin Account</label>
                <div class="relative">
                  <User class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary/75 group-focus-within:text-primary transition-colors" />
                  <input 
                    v-model="formData.account"
                    type="text"
                    placeholder="4-32 位字母或数字"
                    class="u-hard-input w-full pl-12 pr-4 py-4 rounded-xl bg-[#ccc] text-sm text-on-surface outline-none focus:bg-white focus:shadow-lg transition-all"
                  />
                </div>
              </div>
            </div>

            <!-- Step 2: Password -->
            <div v-else-if="currentStep === 2" :key="2" class="space-y-6">
              <div class="space-y-2">
                <h2 class="text-lg font-bold text-primary-dark">设置安全密码</h2>
                <p class="text-xs text-secondary/85">建议包含大小写字母、数字及特殊符号。</p>
              </div>
              
              <div class="space-y-4">
                <div class="relative group">
                  <Lock class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary/75 group-focus-within:text-primary transition-colors" />
                  <input 
                    v-model="formData.password"
                    type="password"
                    placeholder="输入管理员密码"
                    class="u-hard-input w-full pl-12 pr-4 py-4 rounded-xl bg-[#ccc] text-sm text-on-surface outline-none focus:bg-white focus:shadow-lg transition-all"
                  />
                </div>

                <div class="relative group">
                  <CheckCircle2 class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary/75 group-focus-within:text-primary transition-colors" />
                  <input 
                    v-model="formData.confirmPassword"
                    type="password"
                    placeholder="再次确认密码"
                    class="u-hard-input w-full pl-12 pr-4 py-4 rounded-xl bg-[#ccc] text-sm text-on-surface outline-none focus:bg-white focus:shadow-lg transition-all"
                  />
                </div>

                <!-- Password Strength Meter -->
                <div class="px-1 space-y-2">
                  <div class="flex justify-between text-[9px] font-black uppercase tracking-tighter">
                    <span class="text-secondary/75">Security Level</span>
                    <span :style="{ color: strengthColor }">{{ passwordStrength }}%</span>
                  </div>
                  <div class="h-1 w-full bg-black/5 rounded-full overflow-hidden">
                    <div 
                      class="h-full transition-all duration-1000 ease-spring"
                      :style="{ width: `${passwordStrength}%`, backgroundColor: strengthColor }"
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="currentStep === 3" :key="3" class="space-y-6">
              <div class="space-y-2">
                <h2 class="text-lg font-bold text-primary-dark">系统初始偏好</h2>
                <p class="text-xs text-secondary/85">初始化完成后，您可以在管理面板中随时修改。</p>
              </div>

              <div class="p-4 rounded-xl bg-black/5 border border-white/10 space-y-5">
                <!-- Registration Toggle -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center space-x-3">
                    <div class="p-2 bg-white/50 rounded-lg">
                      <User class="w-4 h-4 text-primary" :style="{ color: 'var(--accent-color)' }" />
                    </div>
                    <div>
                      <p class="text-xs font-bold text-primary-dark">开放新用户注册</p>
                      <p class="text-[9px] text-secondary/85">允许任何人访问您的主页并注册账号</p>
                    </div>
                  </div>
                  <button 
                    @click="formData.allow_registration = !formData.allow_registration"
                    :class="['w-10 h-5 rounded-full transition-all relative shrink-0', formData.allow_registration ? 'bg-primary' : 'bg-secondary/20']"
                    :style="{ backgroundColor: formData.allow_registration ? 'var(--accent-color)' : '' }"
                  >
                    <div :class="['absolute top-0.5 w-4 h-4 bg-white rounded-full transition-all', formData.allow_registration ? 'left-5' : 'left-1']"></div>
                  </button>
                </div>

                <!-- Rate Limit & Token Expire -->
                <div class="pt-4 border-t border-black/5 space-y-4">
                    <div class="flex items-center justify-between">
                        <p class="text-xs font-bold text-primary-dark">接口频率限制</p>
                        <div class="flex items-center space-x-2">
                           <input 
                             type="number" 
                             v-model.number="formData.auth_rate_limit" 
                             class="w-16 bg-white border-2 border-black/5 rounded-lg px-2 py-1 text-xs font-black outline-none focus:border-primary transition-all text-center"
                           />
                           <span class="text-[8px] font-black text-secondary/80">次/分</span>
                        </div>
                    </div>
                    <div class="flex items-center justify-between">
                        <p class="text-xs font-bold text-primary-dark">默认 Token 有效期</p>
                        <div class="flex items-center space-x-2">
                           <input 
                             type="number" 
                             :value="Math.round(formData.default_token_expire / 3600)" 
                             @input="formData.default_token_expire = (Number(($event.target as HTMLInputElement).value) * 3600)"
                             class="w-16 bg-white border-2 border-black/5 rounded-lg px-2 py-1 text-xs font-black outline-none focus:border-primary transition-all text-center"
                           />
                           <span class="text-[8px] font-black text-secondary/80">小时</span>
                        </div>
                    </div>
                </div>
              </div>

              <div class="flex items-start space-x-2 p-3 rounded-lg bg-orange-400/10 border border-orange-400/20">
                <AlertCircle class="w-4 h-4 text-orange-500 shrink-0 mt-0.5" />
                <p class="text-[9px] text-orange-700 leading-normal">
                  请务必牢记您的管理员账号。如果丢失，可能需要通过服务器控制台手动重置数据库。
                </p>
              </div>
            </div>
          </Transition>
        </div>

        <!-- Navigation Buttons -->
        <div class="mt-10 flex items-center justify-between">
          <button 
            v-if="currentStep > 1"
            @click="prevStep"
            class="flex items-center space-x-2 text-xs font-black uppercase text-secondary/85 hover:text-primary transition-all active:scale-90"
          >
            <ChevronLeft class="w-4 h-4" />
            <span>Back</span>
          </button>
          <div v-else></div>

          <button 
            v-if="currentStep < totalSteps"
            @click="nextStep"
            :disabled="!isStepValid"
            class="flex items-center space-x-2 px-6 py-3 bg-primary text-white rounded-xl font-bold text-xs uppercase tracking-widest hover:scale-105 active:scale-95 disabled:opacity-30 transition-all shadow-lg"
            :style="{ backgroundColor: 'var(--accent-color)' }"
          >
            <span>Next Step</span>
            <ChevronRight class="w-4 h-4" />
          </button>

          <button 
            v-else
            @click="handleInitialize"
            :disabled="isSubmitting"
            class="flex items-center space-x-2 px-8 py-3 bg-primary text-white rounded-xl font-bold text-xs uppercase tracking-widest hover:scale-110 active:scale-95 disabled:opacity-30 transition-all shadow-[0_0_20px_rgba(0,163,255,0.4)]"
            :style="{ backgroundColor: 'var(--accent-color)' }"
          >
            <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
            <template v-else>
              <span>Initialize System</span>
              <Settings class="w-4 h-4" />
            </template>
          </button>
        </div>
      </div>

      <!-- Footer Info -->
      <div class="mt-8 text-center space-y-1 opacity-30">
        <p class="text-[10px] font-mono text-secondary uppercase tracking-widest">U-Drop v0.5.1 Deployment Wizard</p>
        <p class="text-[8px] font-mono text-secondary">© 2026 Ethereal Systems • Industrial Grade Security</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.u-hard-input {
  box-shadow: inset 2px 5px 10px rgba(0,0,0,0.15);
}

.u-hard-input:focus {
  background-color: white;
  transform: scale(1.02);
  box-shadow: 
    13px 13px 60px rgba(150, 150, 150, 0.4), 
    -13px -13px 60px rgba(255, 255, 255, 0.7);
  outline: none;
}

.ease-spring {
  transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
.animate-float {
  animation: float 6s ease-in-out infinite;
}

/* Transitions: Slide Right */
.slide-right-enter-active,
.slide-right-leave-active,
.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.slide-right-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.slide-right-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

/* Transitions: Slide Left */
.slide-left-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}
.slide-left-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
