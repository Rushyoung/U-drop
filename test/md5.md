# WASM/DLL 高性能加密工具库总结 (MD5, SHA256, BLAKE3)

本库是一个高度优化的跨平台加密工具集，支持全量哈希、快速分块哈希以及 BLAKE3 的高性能并行哈希。目前已在 Web (WASM) 端实现了 MD5 的 6 倍速性能表现（BLAKE3）。

## 1. 现行架构
- **单文件设计**：核心逻辑集中在 `MD5.c`，零外部库依赖（Portable C 实现）。
- **跨平台导出**：通过 `MD5_API` 宏适配 Windows DLL (`__declspec(dllexport)`) 和 Emscripten WASM (`EMSCRIPTEN_KEEPALIVE`)。
- **流式接口 (`_Ex`)**：所有算法均提供 `Init` / `Update` / `Final` 接口，支持 GB 级大文件的低内存处理。
- **Merkle Tree 并行合并**：专门为 BLAKE3 导出了 `Compress_Parent` 接口，允许主线程合并多 Worker 的中间结果。

## 2. 算法支持
- **MD5**: 经典全量哈希 & 快速分块哈希（头中尾各 4KB）。
- **SHA256**: 全量流式哈希。
- **BLAKE3**: 
  - **Scalar 优化**：循环展开（Round 0-6 完全展开）。
  - **SIMD 128 优化**：支持 Wasm SIMD 指令集。
  - **Parallel 并行**：支持通过 Web Workers 进行多线程分片计算。

## 3. 编译指令 (emcc)
为了释放最高性能，编译时需开启 `-O3`、`-msimd128` 并导出内存视图：

```bash
emcc source/cpp/MD5.c -O3 -msimd128 \
  -s WASM=1 -s MODULARIZE=1 -s EXPORT_NAME="MD5Module" \
  -s EXPORTED_FUNCTIONS="['_MD5_Init_Ex','_MD5_Update_Ex','_MD5_Final_Ex','_SHA256_Init_Ex','_SHA256_Update_Ex','_SHA256_Final_Ex','_BLAKE3_Init_Ex','_BLAKE3_Update_Ex','_BLAKE3_Final_Ex','_BLAKE3_Compress_Parent_Ex','_malloc','_free','_CalculateFastFileMD5','_CalculateFileMD5']" \
  -s EXPORTED_RUNTIME_METHODS='["cwrap","UTF8ToString","HEAPU8","HEAPU32"]' \
  -o test/md5.js
```

## 4. 示例调用 (JavaScript)

### 全量流式 (SHA256 为例)
```javascript
const ctx = wasm._malloc(1024);
wasm._SHA256_Init_Ex(ctx);
// 循环分块读取
wasm.HEAPU8.set(uint8Chunk, dataPtr);
wasm._SHA256_Update_Ex(ctx, dataPtr, uint8Chunk.length);
// 结束
wasm._SHA256_Final_Ex(digestPtr, ctx);
```

### BLAKE3 多线程并行
1. **Worker 层**：计算 `Segment` 的哈希得到 `Chain Value`。
2. **主线程层**：调用 `_BLAKE3_Compress_Parent_Ex` 进行树状合并。

## 5. 对话优化流程记录
1. **基础阶段**：实现基础 MD5 文件计算，解决 `MODULARIZE` 模式下的导出问题。
2. **快速哈希**：引入 `fseek` 定位，实现大文件的“头中尾” 4KB 快速哈希。
3. **WASM 优化**：发现浏览器 `fopen` 性能瓶颈，将文件读取逻辑移至 JS 侧，C 层仅负责流式计算。
4. **扩展算法**：在无外部依赖的情况下手动集成 SHA256 和 BLAKE3 纯 C 实现。
5. **内存修复**：解决 `-O3` 优化下 `HEAPU8` 被隐藏的问题，实现增强型内存视图嗅探逻辑。
6. **性能释放 (SIMD)**：引入 Wasm SIMD 128 指令集，通过寄存器级并行重写 BLAKE3 核心。
7. **性能释放 (多线程)**：重构算法支持树状哈希，编写 Web Worker 池和主线程合并逻辑，性能达到 MD5 的 6 倍。

## 6. 导出为 DLL (Windows)
使用 MSVC 编译：
```cmd
cl MD5.c /LD /O2 /Fe:md5.dll
```
Python `ctypes` 调用正常，接口与 WASM 一致。
