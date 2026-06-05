## ✅ 整体流程（网页端调用 WASM MD5 的完整链路）

### 1) 编译阶段（把 `md5.c` 变成 `md5.js + md5.wasm`）

你需要用 `emcc` 生成一个带 JS 启动器的 WebAssembly 模块，关键点：

- **输出**：md5.js + md5.wasm
- **导出**：`CalculateMD5`（你的 C 接口）、`_malloc/_free`、`cwrap`、`UTF8ToString`（JS 端需要）
- **定位 wasm**：在浏览器里要从 `/static/md5.wasm` 载入，所以需要 `locateFile` 或保持路径一致

推荐命令：

```powershell
emcc source/cpp/MD5.c -O3 -s WASM=1 -s MODULARIZE=1 -s EXPORT_NAME="MD5Module" \
  -s EXPORTED_FUNCTIONS="['_CalculateMD5','_malloc','_free']" \
  -s EXPORTED_RUNTIME_METHODS='["cwrap","UTF8ToString"]' \
  -o test/md5.js
```

---

## ✅ 运行时流程（浏览器端调用流程）

### 1) 页面加载 md5.js（通过 FastAPI 提供静态路径 `/static/md5.js`）

```html
<script src="/static/md5.js"></script>
```

### 2) 初始化 WASM 模块（`MD5Module()`）

```js
const module = await MD5Module({
  locateFile: (path) => `/static/${path}`   // 让 md5.js 能正确找到 md5.wasm
});
```

### 3) 通过 `cwrap` 生成 JS 调用接口

```js
module.calculateMD5 = module.cwrap('CalculateMD5', 'number', ['array', 'number', 'number']);
```

- `array`：会由 Emscripten 自动把 `Uint8Array` 拷贝到 WASM 内存里
- `number`：传长度、结果指针等

### 4) 选择文件 + 读入内容 + 调用 WASM 计算

```js
const bytes = new Uint8Array(await file.arrayBuffer());
const resultPtr = wasmModule._malloc(33);
const ret = wasmModule.calculateMD5(bytes, bytes.length, resultPtr);
const md5 = wasmModule.UTF8ToString(resultPtr);
wasmModule._free(resultPtr);
```

---

## ⚠️ 编译/部署注意事项（常见坑）

### 1) **必须导出 `UTF8ToString`**
否则 `wasmModule.UTF8ToString` 不存在，JS 读不回字符串结果。

### 2) **WASM 文件路径必须正确**
浏览器会自动请求 `md5.wasm`，要么：

- 用 `locateFile` 强制指向 `/static/md5.wasm`（推荐）
- 要么让页面和 `md5.wasm` 在同目录，且路由 `/md5.wasm` 能返回它

### 3) **FastAPI 静态目录配置要对**
你现在是：

```python
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent), name="static")
```

那你浏览器中应该加载：

- `/static/md5.js`
- `/static/md5.wasm`

### 4) **浏览器控制台查错**
关键输出：

- `wasmModule keys:` → 看是否有 `_malloc`、`cwrap`、`UTF8ToString`
- `wasmModule.HEAPU8`（可不用，但可用于检查内存是否存在）

---

## ✅ 最终结果（你的页面在运行时做了什么）

1. 浏览器加载 test.html
2. 加载 md5.js（由 FastAPI `/static/md5.js` 提供）
3. md5.js 自动请求并加载 `/static/md5.wasm`
4. 页面调用 `MD5Module()` 初始化（把 wasm 实例化）
5. 选择文件 → 读取为 `Uint8Array`
6. 调用 `calculateMD5(bytes, bytes.length, resultPtr)` 计算
7. 通过 `UTF8ToString(resultPtr)` 读出 32 字节 MD5 字符串
8. 将结果展示在页面上

---

如果你想进一步优化（比如：避免 JS 里再做 `malloc/free`、使用 worker、支持大文件分块计算），我可以帮你把这套流程升级到更专业的版本。