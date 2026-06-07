/* eslint-disable no-restricted-globals */
import createHashModule from '../lib/wasm/hash.js';
import wasmUrl from '../lib/wasm/hash.wasm?url';

let wasmModule = null;

const initWasm = async () => {
    if (!wasmModule) {
        wasmModule = await createHashModule({
            locateFile: (path) => {
                if (path.endsWith('.wasm')) return wasmUrl;
                return path;
            }
        });
    }
    return wasmModule;
};

function getHEAPU8(module) {
    if (module.HEAPU8 && module.HEAPU8.byteLength > 0) return module.HEAPU8;
    let buffer = module.wasmMemory?.buffer || module.buffer;
    if (!buffer && module.asm && module.asm.memory) buffer = module.asm.memory.buffer;
    if (buffer) {
        module.HEAPU8 = new Uint8Array(buffer);
        return module.HEAPU8;
    }
    return null;
}

const yieldControl = () => new Promise(resolve => setTimeout(resolve, 0));

self.onmessage = async (e) => {
    const { id, chunk, type } = e.data; 
    const module = await initWasm();

    if (type === 'sparse-md5') {
        try {
            const blockSize = 4096;
            const size = chunk.size;
            const buffers = [];
            if (size <= blockSize * 3) {
                buffers.push(await chunk.arrayBuffer());
            } else {
                buffers.push(await chunk.slice(0, blockSize).arrayBuffer());
                buffers.push(await chunk.slice(Math.floor((size - blockSize) / 2), Math.floor((size - blockSize) / 2) + blockSize).arrayBuffer());
                buffers.push(await chunk.slice(size - blockSize, size).arrayBuffer());
            }
            const combined = new Uint8Array(buffers.reduce((acc, b) => acc + b.byteLength, 0));
            let offset = 0;
            for (const b of buffers) {
                combined.set(new Uint8Array(b), offset);
                offset += b.byteLength;
            }
            const tempFileName = `temp_sparse_${id}`;
            module.FS.writeFile(tempFileName, combined);
            const calcStart = performance.now();
            const calculateMD5 = module.cwrap('CalculateFastFileMD5', 'number', ['string', 'number']);
            const resPtr = module._malloc(33); 
            calculateMD5(tempFileName, resPtr);
            const HEAPU8 = getHEAPU8(module);
            const hash = new TextDecoder().decode(HEAPU8.slice(resPtr, resPtr + 32));
            const internalTime = performance.now() - calcStart;
            module.FS.unlink(tempFileName);
            module._free(resPtr);
            self.postMessage({ id, hash, internalTime });
        } catch (error) {
            self.postMessage({ id, error: error.message });
        }
    } else if (type === 'full-blake3') {
        try {
            const calcStart = performance.now();
            const ctxSize = module._get_blake3_hasher_size();
            const ctxPtr = module._malloc(ctxSize);
            module._BLAKE3_Init_Ex(ctxPtr);

            // 优化：采用更高效的 4MB 内存分块，减少 I/O 切换
            const ioBlockSize = 4 * 1024 * 1024; 
            const dataPtr = module._malloc(ioBlockSize);
            
            let offset = 0;
            const totalSize = chunk.size;
            let counter = 0;

            while (offset < totalSize) {
                const end = Math.min(offset + ioBlockSize, totalSize);
                const len = end - offset;
                
                // 执行 I/O 读取
                const buf = await chunk.slice(offset, end).arrayBuffer();
                const uint8 = new Uint8Array(buf);
                
                const HEAPU8 = getHEAPU8(module);
                if (!HEAPU8) throw new Error("WASM Memory View lost");
                
                HEAPU8.set(uint8, dataPtr);
                module._BLAKE3_Update_Ex(ctxPtr, dataPtr, len);
                
                offset = end;
                counter++;

                // 适当的 Yield 频率 (每 32MB 一次)
                if (counter % 8 === 0) {
                    await yieldControl();
                    const progress = (offset / totalSize * 100).toFixed(1);
                    console.log(`[Hash Worker] BLAKE3 Progress: ${progress}% (${(offset/1024/1024).toFixed(0)}MB)`);
                }
            }

            const digestPtr = module._malloc(32);
            module._BLAKE3_Final_Ex(digestPtr, ctxPtr);
            
            const HEAPU8 = getHEAPU8(module);
            const digest = HEAPU8.slice(digestPtr, digestPtr + 32);
            const hash = Array.from(digest).map(b => b.toString(16).padStart(2, '0')).join('');
            const internalTime = performance.now() - calcStart;

            module._free(ctxPtr);
            module._free(dataPtr);
            module._free(digestPtr);
            
            console.log(`[Hash Worker] BLAKE3 Finished. Speed: ${(totalSize / 1024 / 1024 / (internalTime / 1000)).toFixed(2)} MB/s`);
            self.postMessage({ id, hash, internalTime });
        } catch (error) {
            console.error("Critical BLAKE3 Failure:", error);
            self.postMessage({ id, error: `计算崩溃: ${error.message}` });
        }
    }
};
