#!/bin/bash

# U-Drop Backend 启动脚本 (Monorepo v1.0.0)

# 1. 确定项目根目录
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

# 2. 注入环境变量 (关键：让 Python 能找到 backend 目录下的模块)
export PYTHONPATH=$PROJECT_ROOT/backend

# 3. 检查虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "--- U-Drop 后端启动中 (Monorepo 模式) ---"
echo "Project Root: $PROJECT_ROOT"
echo "PYTHONPATH: $PYTHONPATH"

# 4. 运行
# 使用 python backend/main.py 启动，
# 内部代码中的 Path(__file__).resolve().parents[2] 会正确找到根目录
python3 backend/main.py
