import { ref } from 'vue';
import { AuthService } from '../api/services';
import type { UserPublic } from '../types/api';

const user = ref<UserPublic | null>(null);

export function useUser() {
  const fetchUser = async () => {
    try {
      const res = await AuthService.me();
      if (res.data.success && res.data.data) {
        user.value = res.data.data;
      }
    } catch (err) {
      console.error('Failed to fetch user profile');
    }
  };

  return { 
    user,
    fetchUser
  };
}
