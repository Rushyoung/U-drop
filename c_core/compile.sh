#!/bin/bash

# U-Drop Linux 编译脚本 (v1.0.0 Monorepo 版)
# 修正：适配新目录结构

SOURCE_DIR="."
BLAKE3_DIR="./blake3"
OUTPUT_DIR="../lib"

mkdir -p $OUTPUT_DIR

echo "--- 开始编译 U-Drop 整合原生核心 (Linux x86_64) ---"

# 1. 编译 BLAKE3 官方模块
echo "编译 BLAKE3 指令集优化组件 (x86_64)..."
gcc -fPIC -c $BLAKE3_DIR/blake3.c -o $OUTPUT_DIR/blake3.o -O3
gcc -fPIC -c $BLAKE3_DIR/blake3_portable.c -o $OUTPUT_DIR/blake3_portable.o -O3
gcc -fPIC -c $BLAKE3_DIR/blake3_dispatch.c -o $OUTPUT_DIR/blake3_dispatch.o -O3
gcc -fPIC -c $BLAKE3_DIR/blake3_sse2.c -o $OUTPUT_DIR/blake3_sse2.o -O3 -msse2
gcc -fPIC -c $BLAKE3_DIR/blake3_sse41.c -o $OUTPUT_DIR/blake3_sse41.o -O3 -msse4.1
gcc -fPIC -c $BLAKE3_DIR/blake3_avx2.c -o $OUTPUT_DIR/blake3_avx2.o -O3 -mavx2
gcc -fPIC -c $BLAKE3_DIR/blake3_avx512.c -o $OUTPUT_DIR/blake3_avx512.o -O3 -mavx512f -mavx512vl

# 2. 编译整合包装层 MD5.c
echo "编译业务包装层 (MD5 + BigFile Support)..."
gcc -fPIC -c $SOURCE_DIR/MD5.c -I$SOURCE_DIR -D_FILE_OFFSET_BITS=64 -o $OUTPUT_DIR/MD5.o -O3

# 3. 编译缩略图模块 (C++)
echo "编译缩略图引擎 (stb_image)..."
g++ -fPIC -c $SOURCE_DIR/thumbnail.cpp -I$SOURCE_DIR -o $OUTPUT_DIR/thumbnail.o -O3

# 4. 链接为统一的共享库 .so
echo "正在链接共享库..."
g++ -shared \
    $OUTPUT_DIR/blake3.o $OUTPUT_DIR/blake3_portable.o $OUTPUT_DIR/blake3_dispatch.o \
    $OUTPUT_DIR/blake3_sse2.o $OUTPUT_DIR/blake3_sse41.o $OUTPUT_DIR/blake3_avx2.o \
    $OUTPUT_DIR/blake3_avx512.o \
    $OUTPUT_DIR/MD5.o $OUTPUT_DIR/thumbnail.o \
    -o $OUTPUT_DIR/thumbnail.so -lm

if [ $? -eq 0 ]; then
    echo -e "\n\033[32m✅ 编译成功: $OUTPUT_DIR/thumbnail.so\033[0m"
    rm $OUTPUT_DIR/*.o
else
    echo -e "\n\033[31m❌ 编译失败，请检查 GCC 配置。\033[0m"
    exit 1
fi
