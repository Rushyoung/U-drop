// BLAKE3 Web Worker
importScripts('/static/md5.js');

let wasm;
const wasmPromise = MD5Module({ locateFile: (path) => `/static/${path}` });

function ensureWasmMemory(instance) {
    const currentBuffer = instance.HEAPU8 ? instance.HEAPU8.buffer : 
                         (instance.memory ? instance.memory.buffer : 
                         (instance.wasmMemory ? instance.wasmMemory.buffer : instance.buffer));
    if (!instance.HEAPU8 || instance.HEAPU8.buffer !== currentBuffer) {
        instance.HEAPU8 = new Uint8Array(currentBuffer);
    }
}

onmessage = async (e) => {
    const { chunk, type, id } = e.data;
    if (!wasm) wasm = await wasmPromise;

    ensureWasmMemory(wasm);

    const ctxPtr = wasm._malloc(1024);
    const dataPtr = wasm._malloc(chunk.byteLength);
    const digestPtr = wasm._malloc(32);

    try {
        const uint8 = new Uint8Array(chunk);
        
        ensureWasmMemory(wasm);
        wasm.HEAPU8.set(uint8, dataPtr);

        // 初始化并计算这一块的哈希 (作为独立 Chunk)
        wasm._BLAKE3_Init_Ex(ctxPtr);
        wasm._BLAKE3_Update_Ex(ctxPtr, dataPtr, uint8.length);
        wasm._BLAKE3_Final_Ex(digestPtr, ctxPtr);

        // 获取 Chain Value (CV)
        const cv = new Uint32Array(wasm.HEAPU8.buffer, digestPtr, 8).slice();
        postMessage({ id, cv }, [cv.buffer]);
    } finally {
        wasm._free(ctxPtr);
        wasm._free(dataPtr);
        wasm._free(digestPtr);
    }
};
