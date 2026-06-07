import { reactive } from "vue";

// Key 是 message_id (临时或正式)
const tasks = reactive({});

export function useUploadManager() {
  const setTask = (id, task) => {
    tasks[id] = task;
  };

  const updateProgress = (id, progress) => {
    if (tasks[id]) tasks[id].progress = progress;
  };

  const completeTask = (id) => {
    if (tasks[id]) tasks[id].isComplete = true;
    // 延迟 5s 清理，确保 Timeline 轮询已完成
    setTimeout(() => {
      delete tasks[id];
    }, 5000);
  };

  const setError = (id, error) => {
    if (tasks[id]) tasks[id].error = error;
  };

  return {
    tasks,
    setTask,
    updateProgress,
    completeTask,
    setError,
  };
}
