import { v4 as uuidv4 } from "uuid";

const DEVICE_ID_KEY = "udrop_device_id";
const CUSTOM_DEVICE_NAME_KEY = "udrop_custom_device_name";
const LAST_ANCHOR_KEY = "udrop_last_anchor_id";

export function getDeviceId() {
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = uuidv4();
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

export function saveCustomDeviceName(name) {
  localStorage.setItem(CUSTOM_DEVICE_NAME_KEY, name);
}

export function getDeviceName() {
  const shortId = getDeviceId().slice(0, 6);
  const customName = localStorage.getItem(CUSTOM_DEVICE_NAME_KEY);

  if (customName) {
    return `${customName} [${shortId}]`;
  }

  const ua = navigator.userAgent;
  let os = "Unknown OS";
  let browser = "Unknown Browser";

  // 简单的 OS 判定
  if (ua.indexOf("Win") !== -1) os = "Windows";
  if (ua.indexOf("Mac") !== -1) os = "macOS";
  if (ua.indexOf("X11") !== -1) os = "Linux";
  if (ua.indexOf("Android") !== -1) os = "Android";
  if (ua.indexOf("iPhone") !== -1) os = "iOS";

  // 强化的浏览器判定
  if (ua.indexOf("Edg/") !== -1) {
    browser = "Edge";
  } else if (ua.indexOf("Chrome") !== -1) {
    browser = "Chrome";
  } else if (ua.indexOf("Firefox") !== -1) {
    browser = "Firefox";
  } else if (ua.indexOf("Safari") !== -1) {
    browser = "Safari";
  }

  return `${os} - ${browser} [${shortId}]`;
}

export function saveLastAnchor(id) {
  localStorage.setItem(LAST_ANCHOR_KEY, id.toString());
}

export function getLastAnchor() {
  const id = localStorage.getItem(LAST_ANCHOR_KEY);
  return id ? parseInt(id, 10) : null;
}
