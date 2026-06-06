# U-Drop

极简的个人内容寻址云存储系统。

## **项目目前仍然处于测试阶段，极不稳定**

---

## ✨ 核心特性

- **Monorepo 架构**：FastAPI 后端 + Vue 3 前端 + C 哈希核心（支持 Native/WASM）。
- **极致传输**：支持 Proof of Possession (PoP) 秒传校验，分片上传与哈希计算并发执行。
- **安全加固**：逻辑 ID 寻址（防 IDOR 越权）、基于 IP 的认证限流、滑动窗口 Session 续期。
- **智能存储**：基于 Blake3 的内容寻址存储 (CAS)，物理去重，内置大文件分析工具。
- **UI 设计**：遵循工业新拟态 (Industrial Neumorphism) 审美。

---

## 🛠️ 技术栈

- **后端**：Python 3.11 / FastAPI / SQLite (WAL)
- **前端**：Vue 3 / Vite / Tailwind CSS
- **底层**：C++ / BLAKE3 (SIMD 优化) / Emscripten (WASM)
- **托管**：FastAPI 直接托管前端产物，支持单端口部署。

---

## 📂 目录结构

```text
udrop/
├── backend/            # 后端源码与 SQL 迁移
├── c_core/             # C 哈希核心及编译脚本
├── frontend/           # Vue 3 前端源码
├── deploy/             # Docker 部署配置
├── lib/                # 编译生成的 .so / .wasm
└── run_backend.sh      # 一键启动脚本
```

---

## 🚀 快速开始

1. **编译 C 核心**：`cd c_core && ./compile.sh`
2. **构建前端**：`cd frontend && npm install && npm run build`
3. **启动后端**：`./run_backend.sh`

访问 `http://localhost:8000` 即可使用。系统未初始化时会自动引导创建管理员。

---


