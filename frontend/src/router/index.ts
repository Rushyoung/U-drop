import { createRouter, createWebHistory } from 'vue-router';
import Home from '../views/Home.vue';
import Login from '../views/Login.vue';
import Register from '../views/Register.vue';
import Init from '../views/Init.vue';
import { getToken } from '../utils/auth';
import { SystemService } from '../api/services';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home,
      meta: { requiresAuth: true }
    },
    {
      path: '/login',
      name: 'login',
      component: Login
    },
    {
      path: '/register',
      name: 'register',
      component: Register
    },
    {
      path: '/init',
      name: 'init',
      component: Init
    }
  ]
});

let isSystemChecked = false;
let isInitialized = false;

router.beforeEach(async (to, _from, next) => {
  // 1. 系统初始化状态探测 (仅探测一次或按需探测)
  if (!isSystemChecked && to.name !== 'init') {
    try {
      const res = await SystemService.status();
      isInitialized = res.data.data?.initialized || false;
      isSystemChecked = true;
    } catch (err) {
      // 容错：如果 status 接口报错，可能是网络问题，允许继续但下次再试
    }
  }

  if (isSystemChecked && !isInitialized && to.name !== 'init') {
    return next('/init');
  }
  
  if (isSystemChecked && isInitialized && to.name === 'init') {
    return next('/login');
  }

  // 2. 原有的鉴权逻辑
  const token = getToken();
  if (to.meta.requiresAuth && !token) {
    next('/login');
  } else if ((to.name === 'login' || to.name === 'register') && token) {
    next('/');
  } else {
    next();
  }
});

export default router;
