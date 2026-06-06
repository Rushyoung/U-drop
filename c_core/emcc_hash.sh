#!/bin/bash

# U-Drop WASM 编译脚本 (v1.0.0 Monorepo 版)
# 修正：同步包含官方 BLAKE3 模块以适配统一后的 MD5.c

if ! command -v emcc &> /dev/null; then
    echo "错误: 未找到 emcc。请先安装 Emscripten 并 source emsdk_env.sh"
    exit 1
fi

SOURCE_DIR="."
BLAKE3_DIR="./blake3"
OUT_DIR="../lib/wasm"
mkdir -p $OUT_DIR

echo "--- 开始编译全能哈希 WASM (MD5 + BLAKE3) ---"

# 参数解释：
# -O3: 极致优化
# -s WASM=1: 生成 wasm 字节码
# -s MODULARIZE=1: 生成可导入的模块
# -s EXPORT_ES6=1: 支持 ES6 模块导入模式
# -s ALLOW_MEMORY_GROWTH=1: 允许内存根据大文件需求自动增长
emcc $SOURCE_DIR/MD5.c \
     $BLAKE3_DIR/blake3.c \
     $BLAKE3_DIR/blake3_portable.c \
     $BLAKE3_DIR/blake3_dispatch.c \
     -I$SOURCE_DIR \
     -O3 \
     -s WASM=1 \
     -s MODULARIZE=1 \
     -s EXPORT_ES6=1 \
     -s ALLOW_MEMORY_GROWTH=1 \
     -s FORCE_FILESYSTEM=1 \
     -s EXPORTED_RUNTIME_METHODS='["cwrap", "ccall", "getValue", "setValue", "FS"]' \
     -s EXPORTED_FUNCTIONS='["_malloc", "_free", "_CalculateFastFileMD5", "_get_blake3_hasher_size", "_BLAKE3_Init_Ex", "_BLAKE3_Update_Ex", "_BLAKE3_Final_Ex"]' \
     -o $OUT_DIR/hash.js

if [ $? -eq 0 ]; then
    echo -e "\n\033[32m✅ WASM 编译成功: $OUT_DIR/hash.js\033[0m"
    ls -lh $OUT_DIR
else
    echo -e "\n\033[31m❌ WASM 编译失败\033[0m"
    exit 1
fi
