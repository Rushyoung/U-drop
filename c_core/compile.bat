@echo off
rem U-Drop Native Core 编译脚本 (Windows MSVC 版)
rem 需在 "x64 Native Tools Command Prompt for VS 2022" 中运行

chcp 65001 >nul
setlocal enabledelayedexpansion

if /I "%~1"=="clean" goto :clean
if /I "%~1"=="-h" goto :usage
if /I "%~1"=="--help" goto :usage
if /I "%~1"=="/?" goto :usage

rem ---------------------------------------------------------------------------
rem 检查架构 (防止 WinError 193)
rem ---------------------------------------------------------------------------
if /I not "%VSCMD_ARG_TGT_ARCH%"=="x64" (
    echo WARNING: You are NOT in a 64-bit tools environment.
    echo Current Arch: %VSCMD_ARG_TGT_ARCH%
    echo This will likely cause 'WinError 193' in 64-bit Python.
    echo Please use: "x64 Native Tools Command Prompt for VS 2022"
    echo.
    set /p "choice=Continue anyway? (y/N): "
    if /I not "!choice!"=="y" exit /b 1
)

rem ---------------------------------------------------------------------------
rem 检查 cl.exe 是否可用
rem ---------------------------------------------------------------------------
where.exe cl >nul 2>&1
if errorlevel 1 (
    echo ERROR: cl.exe not found in PATH.
    echo Please run this script from a Visual Studio Developer Command Prompt.
    exit /b 1
)

rem ---------------------------------------------------------------------------
rem 路径配置
rem ---------------------------------------------------------------------------
set "SRC_DIR=%~dp0"
set "BLAKE3_DIR=%SRC_DIR%blake3"
set "OUTPUT_DIR=%~dp0..\lib"
set "TMP_DIR=%TEMP%\udrop_compile_tmp"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%"

rem 增加 /utf-8 解决 C4819 警告，增加 /LD 确保链接为 DLL
set "FLAGS=/nologo /O2 /EHsc /D_CRT_SECURE_NO_WARNINGS /utf-8"

echo --- 开始编译 U-Drop Native Core (Windows %VSCMD_ARG_TGT_ARCH% MSVC) ---

rem ---------------------------------------------------------------------------
rem 1. 编译 BLAKE3 模块
rem ---------------------------------------------------------------------------
echo [1/3] Compiling BLAKE3...

cl %FLAGS% /c "%BLAKE3_DIR%\blake3.c" /Fo"%TMP_DIR%\blake3.obj"
if errorlevel 1 goto :fail
cl %FLAGS% /c "%BLAKE3_DIR%\blake3_portable.c" /Fo"%TMP_DIR%\blake3_portable.obj"
if errorlevel 1 goto :fail
cl %FLAGS% /c "%BLAKE3_DIR%\blake3_dispatch.c" /Fo"%TMP_DIR%\blake3_dispatch.obj"
if errorlevel 1 goto :fail
cl %FLAGS% /c "%BLAKE3_DIR%\blake3_sse2.c" /Fo"%TMP_DIR%\blake3_sse2.obj"
if errorlevel 1 goto :fail
cl %FLAGS% /c "%BLAKE3_DIR%\blake3_sse41.c" /Fo"%TMP_DIR%\blake3_sse41.obj"
if errorlevel 1 goto :fail
cl %FLAGS% /c "%BLAKE3_DIR%\blake3_avx2.c" /Fo"%TMP_DIR%\blake3_avx2.obj"
if errorlevel 1 goto :fail
cl %FLAGS% /c "%BLAKE3_DIR%\blake3_avx512.c" /Fo"%TMP_DIR%\blake3_avx512.obj"
if errorlevel 1 goto :fail

rem ---------------------------------------------------------------------------
rem 2. 编译 MD5 + 缩略图模块
rem ---------------------------------------------------------------------------
echo [2/3] Compiling MD5 + Thumbnail...

cl %FLAGS% /c "%SRC_DIR%MD5.c" /Fo"%TMP_DIR%\MD5.obj"
if errorlevel 1 goto :fail
cl %FLAGS% /c "%SRC_DIR%thumbnail.cpp" /Fo"%TMP_DIR%\thumbnail.obj"
if errorlevel 1 goto :fail

rem ---------------------------------------------------------------------------
rem 3. 链接为 DLL
rem ---------------------------------------------------------------------------
echo [3/3] Linking thumbnail.dll...

link /nologo /DLL /OUT:"%OUTPUT_DIR%\thumbnail.dll" ^
    "%TMP_DIR%\blake3.obj" ^
    "%TMP_DIR%\blake3_portable.obj" ^
    "%TMP_DIR%\blake3_dispatch.obj" ^
    "%TMP_DIR%\blake3_sse2.obj" ^
    "%TMP_DIR%\blake3_sse41.obj" ^
    "%TMP_DIR%\blake3_avx2.obj" ^
    "%TMP_DIR%\blake3_avx512.obj" ^
    "%TMP_DIR%\MD5.obj" ^
    "%TMP_DIR%\thumbnail.obj"

if errorlevel 1 goto :fail

rem ---------------------------------------------------------------------------
rem 清理临时文件
rem ---------------------------------------------------------------------------
rmdir /s /q "%TMP_DIR%"

echo.
echo [OK] 编译成功: %OUTPUT_DIR%\thumbnail.dll
exit /b 0

:fail
rmdir /s /q "%TMP_DIR%" 2>nul
echo.
echo [FAIL] 编译失败，请检查错误信息。
exit /b 1

:clean
echo Cleaning build artifacts...
if exist "%~dp0..\lib\thumbnail.dll" del /f /q "%~dp0..\lib\thumbnail.dll"
if exist "%~dp0..\lib\thumbnail.lib" del /f /q "%~dp0..\lib\thumbnail.lib"
if exist "%~dp0..\lib\thumbnail.exp" del /f /q "%~dp0..\lib\thumbnail.exp"
if exist "%TEMP%\udrop_compile_tmp" rmdir /s /q "%TEMP%\udrop_compile_tmp"
echo Clean complete.
exit /b 0

:usage
echo Usage:
echo   compile.bat          - Build thumbnail.dll
echo   compile.bat clean    - Remove build artifacts
exit /b 0
