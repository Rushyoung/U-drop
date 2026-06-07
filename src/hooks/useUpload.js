import { MessageService, FileService, AuthService } from '../api/services';
import { calculateSparseMd5, calculateFullBlake3, getMimeType } from '../utils/hash';
import { useUploadManager } from '../utils/uploadManager';
import { useToast } from '../utils/toast';
import { useUser } from '../utils/user';

export function useUpload() {
  const { setTask, updateProgress, completeTask } = useUploadManager();
  const { showToast } = useToast();
  const { fetchUser } = useUser();

  /**
   * 上传单个文件的核心逻辑 (真正的并行赛跑)
   */
  const uploadSingleFile = async (
    messageId,
    uploadId,
    file,
    fullHashPromise
  ) => {
    let calculatedFullHash = null;
    let hashError = null;

    // 后台静默接收哈希结果，绝对不阻塞下面的 try 块
    fullHashPromise.then(res => {
      calculatedFullHash = res.hash;
      console.log(`[Upload Diagnostic] Parallel Hash READY for ${file.name}: ${res.hash}`);
    }).catch(err => {
      hashError = err.message;
      console.error(`[Upload Diagnostic] Parallel Hashing FAILED`, err);
    });

    try {
      // 动态分片尺寸优化
      let chunkSize = 1024 * 1024 * 2; 
      if (file.size > 2 * 1024 * 1024 * 1024) chunkSize = 1024 * 1024 * 20;
      else if (file.size > 512 * 1024 * 1024) chunkSize = 1024 * 1024 * 5;
      
      const totalChunks = Math.ceil(file.size / chunkSize);
      let isHijacked = false;

      console.log(`[Upload Diagnostic] Starting Immediate Upload for ${file.name} (${totalChunks} chunks)`);

      for (let i = 0; i < totalChunks; i++) {
        const start = i * chunkSize;
        const end = Math.min(start + chunkSize, file.size);
        const chunk = file.slice(start, end);

        // 如果此时哈希已经算好了，就带上 X-Full-Hash 尝试秒传
        const currentHash = calculatedFullHash || undefined;
        
        try {
          const uploadRes = await FileService.uploadChunk(uploadId, chunk, currentHash);
          if (uploadRes.data.data?.status === 'deduplicated') {
            console.log(`[Upload Diagnostic] HIJACKED! Deduped at chunk ${i+1}`);
            isHijacked = true;
            break;
          }
        } catch (patchErr) {
          if (patchErr.response?.status === 404) {
             showToast('任务已失效，上传终止', 'error');
             return false;
          }
          throw patchErr;
        }
        
        updateProgress(messageId, Math.round(((i + 1) / totalChunks) * 100));
      }

      // 无论分片传多快，commit 之前必须确保哈希已到手
      if (!isHijacked) {
        if (hashError) throw new Error(`哈希引擎异常: ${hashError}`);
        
        if (!calculatedFullHash) {
          console.log(`[Upload Diagnostic] Waiting for background hash to finish for COMMIT...`);
        }
        const finalHashRes = await fullHashPromise;
        console.log(`[Upload Diagnostic] Executing COMMIT with hash: ${finalHashRes.hash}`);
        await FileService.commit(uploadId, finalHashRes.hash);
      }
      
      return true;
    } catch (err) {
      console.error(`[Upload Diagnostic] FAILURE: ${file.name}`, err);
      return false;
    }
  };

  /**
   * 发起上传任务
   */
  const startUpload = async (files, content, onCreated) => {
    if (files.length === 0) return 0;
    
    // 0. 配额预检
    try {
      const meRes = await AuthService.me();
      if (meRes.data.success && meRes.data.data) {
        const { used_storage, storage_quota } = meRes.data.data;
        const totalNewSize = files.reduce((acc, f) => acc + f.size, 0);
        if (used_storage + totalNewSize > storage_quota) {
          showToast(`存储空间不足`, 'error');
          return 0;
        }
      }
    } catch (err) {
       console.warn('Quota check skipped');
    }

    const totalStartTime = performance.now();

    try {
      // 1. 同时启动所有哈希（Worker 内部排队，但不阻塞主线程）
      const sparsePromises = files.map(f => calculateSparseMd5(f));
      const fullPromises = files.map(f => calculateFullBlake3(f));

      // 仅等待快速哈希以创建 ID
      const sparseResults = await Promise.all(sparsePromises);

      // 2. 创建消息任务
      const fileIntents = files.map((f, i) => ({
        file_name: f.name,
        total_size: f.size,
        sparse_hash: sparseResults[i].hash,
        mime_type: getMimeType(f.name)
      }));

      const res = await MessageService.create({
        content: content || null,
        type: 1, 
        files: fileIntents
      });

      if (!res.data.success || !res.data.data) throw new Error('Backend rejected task');

      const { status, message_id, upload_tasks } = res.data.data;
      
      setTask(message_id, {
        progress: 0,
        fileName: files.length > 1 ? `${files[0].name} 等 ${files.length} 个文件` : files[0].name,
        isComplete: false,
        error: null
      });

      onCreated?.(message_id);

      if (status === 'created') {
        updateProgress(message_id, 100);
        completeTask(message_id);
        fetchUser();
        return message_id;
      }

      // 3. 核心：立即发起分片上传任务
      const taskPromises = upload_tasks.map(task => {
        const fileObj = files.find(f => f.name === task.file_name);
        if (!fileObj) return Promise.resolve(false);
        const fileIndex = files.indexOf(fileObj);
        return uploadSingleFile(message_id, task.upload_id, fileObj, fullPromises[fileIndex]);
      });

      const results = await Promise.all(taskPromises);
      const allSuccess = results.every(r => r === true);

      fetchUser(); 
      if (allSuccess) {
        const totalDuration = (performance.now() - totalStartTime) / 1000;
        updateProgress(message_id, 100);
        completeTask(message_id);
        showToast(`上传成功 (${totalDuration.toFixed(2)}s)`, 'success');
      } else {
        showToast('上传中途遇到错误', 'error');
      }

      return message_id;

    } catch (err) {
      console.error(`[Upload Diagnostic] GLOBAL FAILURE:`, err);
      showToast(`传输中断`, 'error');
      return 0;
    }
  };

  return { startUpload };
}
