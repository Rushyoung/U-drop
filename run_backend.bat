@echo off
rem U-Drop Backend 启动脚本 (Windows 版)

rem 1. 确定项目根目录并切换
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

rem 2. 注入环境变量 (让 Python 能找到 backend 目录下的模块)
set "PYTHONPATH=%PROJECT_ROOT%backend"

rem 3. 检查虚拟环境
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

echo --- U-Drop 后端启动中 (Monorepo 模式) ---
echo Project Root: %PROJECT_ROOT%
echo PYTHONPATH: %PYTHONPATH%

rem 4. 运行 (Windows 下 python3 通常为 python)
python backend/main.py
