@echo off
rem U-Drop Backend 启动脚本 (Windows 版)

rem 1. 确定项目根目录并切换
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

rem 2. 检查前端产物
set "INDEX_FILE=%PROJECT_ROOT%frontend\dist\index.html"
if not exist "%INDEX_FILE%" (
    echo Error: 前端未编译！
    echo 请先在 frontend 目录下执行: npm install ^&^& npm run build
    pause
    exit /b 1
)
for %%I in ("%INDEX_FILE%") do if %%~zI == 0 (
    echo Error: 前端 index.html 为空！
    echo 请重新执行构建。
    pause
    exit /b 1
)

rem 3. 注入环境变量 (让 Python 能找到 backend 模块)
set "PYTHONPATH=%PROJECT_ROOT%backend"

rem 4. 检查虚拟环境
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

echo --- U-Drop 后端启动中 (Monorepo 模式) ---
echo Project Root: %PROJECT_ROOT%
echo PYTHONPATH: %PYTHONPATH%

rem 5. 运行 (Windows 下 python3 通常为 python)
python backend/main.py
