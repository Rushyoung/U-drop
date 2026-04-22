#!/bin/bash
SOURCE_DIR="source/cpp"
OUTPUT_DIR="lib"
mkdir -p $OUTPUT_DIR

echo "开始编译原生核心库 (Linux)..."

# 1. 编译 MD5.c (使用 gcc)
# 使用 -fPIC 生成位置无关代码，这是共享库必须的
gcc -fPIC -c $SOURCE_DIR/MD5.c -o $OUTPUT_DIR/MD5.o -O3

# 2. 编译 thumbnail.cpp (使用 g++)
# -I. 包含当前目录以便找到 stb 相关头文件
g++ -fPIC -c $SOURCE_DIR/thumbnail.cpp -I$SOURCE_DIR -o $OUTPUT_DIR/thumbnail.o -O3

# 3. 链接成共享库
# 必须链接数学库 -lm
g++ -shared $OUTPUT_DIR/MD5.o $OUTPUT_DIR/thumbnail.o -o $OUTPUT_DIR/thumbnail.so -lm

if [ $? -eq 0 ]; then
    echo "✅ 编译成功: $OUTPUT_DIR/thumbnail.so"
    # 清理中间对象文件
    rm $OUTPUT_DIR/MD5.o $OUTPUT_DIR/thumbnail.o
else
    echo "❌ 编译失败"
    exit 1
fi
