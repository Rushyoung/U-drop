/**
 * @typedef {Object} HashResult
 * @property {string} hash
 * @property {number} internalTime
 */

let persistentWorker = null;
const taskMap = new Map();

function getWorker() {
  if (!persistentWorker) {
    persistentWorker = new Worker(
      new URL("../workers/hash.worker.js", import.meta.url),
      { type: "module" },
    );

    persistentWorker.onmessage = (e) => {
      const { id, hash, internalTime, error } = e.data;
      const task = taskMap.get(id);

      if (task) {
        clearTimeout(task.timer);
        if (error) {
          task.reject(new Error(error));
        } else {
          task.resolve({ hash, internalTime });
        }
        taskMap.delete(id);
      }
    };

    persistentWorker.onerror = (err) => {
      console.error("[Hash Worker] Critical Error:", err);
      // 广播错误给所有待处理任务
      taskMap.forEach((task) => {
        clearTimeout(task.timer);
        task.reject(new Error("哈希计算引擎崩溃，请刷新页面"));
      });
      taskMap.clear();
      persistentWorker?.terminate();
      persistentWorker = null;
    };
  }
  return persistentWorker;
}

export function warmupWorker() {
  getWorker();
}

/**
 * 带有 ID 追踪和超时保护的哈希请求
 */
async function requestHash(type, chunk, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const worker = getWorker();
    const taskId = `${type}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

    const timer = setTimeout(() => {
      if (taskMap.has(taskId)) {
        reject(new Error(`哈希计算超时 (${type})`));
        taskMap.delete(taskId);
      }
    }, timeoutMs);

    taskMap.set(taskId, { resolve, reject, timer });
    worker.postMessage({ type, chunk, id: taskId });
  });
}

export async function calculateSparseMd5(file) {
  return requestHash("sparse-md5", file, 30000);
}

export async function calculateFullBlake3(file) {
  // 动态超时：基础 60s + 每 GB 增加 60s (针对 4GB 以上文件)
  const timeout = 60000 + Math.ceil(file.size / (1024 * 1024 * 1024)) * 60000;
  return requestHash("full-blake3", file, timeout);
}

export function getMimeType(fileName) {
  const ext = fileName.split(".").pop()?.toLowerCase();
  const map = {
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    bmp: "image/bmp",
    gif: "image/gif",
    webp: "image/webp",
    svg: "image/svg+xml",
    txt: "text/plain",
    pdf: "application/pdf",
    zip: "application/zip",
    "7z": "application/x-7z-compressed",
    mp4: "video/mp4",
    mp3: "audio/mpeg",
  };
  return map[ext || ""] || "application/octet-stream";
}
