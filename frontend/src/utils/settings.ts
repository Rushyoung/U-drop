import { reactive, watch } from 'vue';

interface UserSettings {
  autoScrollToBottom: boolean;
  accentColor: string;
  pitColor: string;
  cardColorStart: string;
  cardColorEnd: string;
  surroundColor: string;
  messageBorderRadius: number;
}

const SETTINGS_KEY = 'udrop_settings';

const defaultSettings: UserSettings = {
  autoScrollToBottom: true,
  accentColor: '#00A3FF',
  pitColor: '#4a9ecc',
  cardColorStart: '#7fb2d5',
  cardColorEnd: '#a4d8f0',
  surroundColor: '#aed9f4',
  messageBorderRadius: 20
};

const stored = localStorage.getItem(SETTINGS_KEY);
const settings = reactive<UserSettings>(stored ? { ...defaultSettings, ...JSON.parse(stored) } : defaultSettings);

watch(settings, (newVal) => {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(newVal));
}, { deep: true });

export function useSettings() {
  return { settings };
}
