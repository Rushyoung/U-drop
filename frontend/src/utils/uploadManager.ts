import { reactive } from 'vue';

interface UploadTask {
  progress: number;
  fileName: string;
  isComplete: boolean;
  error: string | null;
}

// Key 是 message_id (临时或正式)
const tasks = reactive<Record<number, UploadTask>>({});

export function useUploadManager() {
  const setTask = (id: number, task: UploadTask) => {
    tasks[id] = task;
  };

  const updateProgress = (id: number, progress: number) => {
    if (tasks[id]) tasks[id].progress = progress;
  };

  const completeTask = (id: number) => {
    if (tasks[id]) tasks[id].isComplete = true;
    // 延迟 5s 清理，确保 Timeline 轮询已完成
    setTimeout(() => {
      delete tasks[id];
    }, 5000);
  };

  const setError = (id: number, error: string) => {
    if (tasks[id]) tasks[id].error = error;
  };

  return {
    tasks,
    setTask,
    updateProgress,
    completeTask,
    setError
  };
}
