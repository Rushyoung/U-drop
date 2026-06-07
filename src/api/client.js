import { getDeviceId } from "../utils/device";
import { useToast } from "../utils/toast";
import { getToken, clearToken } from "../utils/auth";

const { showToast } = useToast();

const BASE_URL = "/api/v1";
const TIMEOUT = 15000;

const DEFAULT_HEADERS = {
  "Content-Type": "application/json",
  "X-Device-Id": getDeviceId(),
};

function buildURL(url, params) {
  if (!params) return BASE_URL + url;
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v != null && v !== "")
      .map(([k, v]) => [k, v]),
  ).toString();
  return BASE_URL + url + (qs ? `?${qs}` : "");
}

async function handleError(error) {
  if (error.name === "AbortError") {
    showToast("连接服务器超时，请检查网络", "error");
    return Promise.reject(new Error("请求超时"));
  }

  if (error.status === 401) {
    clearToken();
    if (!window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
  } else if (error.status === 403) {
    const bizMessage = error.data?.message || "";
    if (bizMessage.includes("未初始化") || bizMessage.includes("setup")) {
      window.location.href = "/init";
    }
  } else {
    const detail = error.data?.detail;
    const message = Array.isArray(detail)
      ? detail[0]?.msg
      : error.data?.message || error.statusText || "未知服务器错误";
    showToast(message, "error");
  }

  return Promise.reject(error);
}

function request(method, url, data, config = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), config.timeout || TIMEOUT);

  const urlWithParams = buildURL(url, config.params);
  const headers = { ...DEFAULT_HEADERS };

  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (config.headers) Object.assign(headers, config.headers);

  const isBlob = config.responseType === "blob";

  const init = { method, headers, signal: controller.signal };
  if (data !== undefined && data !== null) {
    init.body =
      headers["Content-Type"] === "application/json"
        ? JSON.stringify(data)
        : data;
  }

  return fetch(urlWithParams, init)
    .then(async (res) => {
      let body;
      if (isBlob) {
        body = await res.blob();
      } else {
        body = await res.json().catch(() => null);
      }

      const error = new Error(res.statusText);
      error.status = res.status;
      error.data = body;

      if (!res.ok) {
        throw error;
      }

      return { data: body, status: res.status, headers: res.headers };
    })
    .catch((err) => {
      if (err.status) return handleError(err);
      if (err.name === "AbortError") {
        showToast("连接服务器超时，请检查网络", "error");
        return Promise.reject(new Error("请求超时"));
      }
      showToast(err.message || "网络异常", "error");
      return Promise.reject(err);
    })
    .finally(() => clearTimeout(timer));
}

const client = {
  get: (url, config) => request("GET", url, undefined, config),
  post: (url, data, config) => request("POST", url, data, config),
  put: (url, data, config) => request("PUT", url, data, config),
  patch: (url, data, config) => request("PATCH", url, data, config),
  delete: (url, config) => request("DELETE", url, undefined, config),
};

export default client;
