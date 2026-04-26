#!/bin/bash

# U-Drop WASM 编译脚本 (仅包含 MD5 逻辑)
# 用途: 供网页端本地计算文件哈希，实现秒传预检。

# 1. 检查 emcc 是否可用
if ! command -v emcc &> /dev/null
then
    echo "错误: 未找到 emcc 命令。请先安装并 source emsdk_env.sh"
    exit 1
fi

# 2. 定义路径
SRC_DIR="source/cpp"
OUT_DIR="lib/wasm"
mkdir -p $OUT_DIR

echo "--- 开始编译 MD5 WASM ---"

# 3. 执行编译
# 我们只包含 MD5_raw.c 和 MD5.c (根据项目文件结构)
# -O3: 极致性能优化
# -s WASM=1: 生成 wasm
# -s MODULARIZE=1: 生成模块化的 JS，方便在 Vue/React 中 import
# -s EXPORT_ES6=1: 生成 ES6 模块格式
# -s EXPORTED_RUNTIME_METHODS: 导出 cwrap，方便 JS 调用
# -s ALLOW_MEMORY_GROWTH=1: 允许内存根据文件大小动态增长
emcc $SRC_DIR/MD5.c \
     -I$SRC_DIR \
     -O3 \
     -s WASM=1 \
     -s MODULARIZE=1 \
     -s EXPORT_ES6=1 \
     -s EXPORTED_RUNTIME_METHODS='["cwrap", "ccall", "getValue", "setValue"]' \
     -s ALLOW_MEMORY_GROWTH=1 \
     -o $OUT_DIR/md5.js

if [ $? -eq 0 ]; then
    echo "--- 编译成功! ---"
    echo "文件已生成在: $OUT_DIR/"
    ls -lh $OUT_DIR
else
    echo "--- 编译失败 ---"
    exit 1
fi
