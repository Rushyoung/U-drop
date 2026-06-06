#!/bin/bash

# U-Drop Backend 启动脚本 (Monorepo v1.0.0)

# 1. 确定项目根目录
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

# 2. 检查前端产物
INDEX_FILE="$PROJECT_ROOT/frontend/dist/index.html"
if [ ! -f "$INDEX_FILE" ] || [ ! -s "$INDEX_FILE" ]; then
    echo "Error: 前端未编译或 index.html 为空！"
    echo "请先在 frontend 目录下执行: npm install && npm run build"
    exit 1
fi

# 3. 注入环境变量 (关键：让 Python 能找到 backend 目录下的模块)
export PYTHONPATH=$PROJECT_ROOT/backend

# 4. 检查虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "--- U-Drop 后端启动中 (Monorepo 模式) ---"
echo "Project Root: $PROJECT_ROOT"
echo "PYTHONPATH: $PYTHONPATH"

# 5. 运行
# 使用 python backend/main.py 启动，
# 内部代码中的 Path(__file__).resolve().parents[2] 会正确找到根目录
python3 backend/main.py
