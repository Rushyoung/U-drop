// src/utils/auth.ts
import { clearAssetCache } from './assetManager';

const TOKEN_KEY = 'udrop_token';

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string, temporary: boolean = false) {
  if (temporary) {
    sessionStorage.setItem(TOKEN_KEY, token);
    localStorage.removeItem(TOKEN_KEY);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TOKEN_KEY);
  clearAssetCache();
}

export function isTemporarySession(): boolean {
  return !!sessionStorage.getItem(TOKEN_KEY);
}
