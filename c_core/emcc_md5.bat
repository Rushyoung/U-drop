@echo off
rem U-Drop WASM 编译脚本 (Windows 版 - 仅 MD5)
rem 需在已激活 emsdk 的环境中运行 (emsdk_env.bat)
rem 用法:
rem   emcc_md5.bat          (编译 lib/wasm/md5.js + md5.wasm)
rem   emcc_md5.bat clean    (清理构建产物)

chcp 65001 >nul

if /I "%~1"=="clean" goto :clean
if /I "%~1"=="-h" goto :usage
if /I "%~1"=="--help" goto :usage
if /I "%~1"=="/?" goto :usage

rem ---------------------------------------------------------------------------
rem 检查 emcc 是否可用
rem ---------------------------------------------------------------------------
where.exe emcc >nul 2>&1
if errorlevel 1 (
    echo ERROR: emcc not found in PATH.
    echo Please activate emsdk first: emsdk_env.bat
    exit /b 1
)

rem ---------------------------------------------------------------------------
rem 路径配置
rem ---------------------------------------------------------------------------
set "SRC_DIR=%~dp0."
set "OUT_DIR=%~dp0..\lib\wasm"

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo --- 开始编译 MD5 WASM ---

emcc "%SRC_DIR%\MD5.c" ^
     "-I%SRC_DIR%" ^
     -O3 ^
     -s WASM=1 ^
     -s MODULARIZE=1 ^
     -s EXPORT_ES6=1 ^
     -s ALLOW_MEMORY_GROWTH=1 ^
     -s EXPORTED_RUNTIME_METHODS="[\"cwrap\",\"ccall\",\"getValue\",\"setValue\"]" ^
     -o "%OUT_DIR%\md5.js"

if errorlevel 1 goto :fail

echo.
echo [OK] MD5 WASM 编译成功: %OUT_DIR%\md5.js
dir /b "%OUT_DIR%\md5.*"
exit /b 0

:fail
echo.
echo [FAIL] WASM 编译失败。
exit /b 1

:clean
echo Cleaning MD5 WASM build artifacts...
if exist "%~dp0..\lib\wasm\md5.js" del /f /q "%~dp0..\lib\wasm\md5.js"
if exist "%~dp0..\lib\wasm\md5.wasm" del /f /q "%~dp0..\lib\wasm\md5.wasm"
echo Clean complete.
exit /b 0

:usage
echo Usage:
echo   emcc_md5.bat          - Build md5.js + md5.wasm (MD5 only)
echo   emcc_md5.bat clean    - Remove build artifacts
exit /b 0
