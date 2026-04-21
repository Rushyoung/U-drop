@echo off
rem Use UTF-8 output
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ---------------------------------------------------------------------------
rem Simple MSVC build script.
rem Requires cl.exe in PATH or VCVARSALL to be set to vcvarsall.bat.
rem Usage:
rem   complie.bat [Debug|Release] [x86|x64] [dll|exe]
rem   complie.bat clean
rem ---------------------------------------------------------------------------

if "%~1"=="/?" goto :usage
if "%~1"=="-h" goto :usage
if "%~1"=="--help" goto :usage

set "ACTION=build"
set "CONFIG=Debug"
set "ARCH=x64"
set "OUT_TYPE=dll"

if /I "%~1"=="clean" (
    set "ACTION=clean"
) else (
    if /I "%~1"=="Debug" set "CONFIG=Debug"
    if /I "%~1"=="Release" set "CONFIG=Release"
    if /I "%~2"=="x86" set "ARCH=x86"
    if /I "%~2"=="x64" set "ARCH=x64"
    if /I "%~3"=="dll" set "OUT_TYPE=dll"
    if /I "%~3"=="exe" set "OUT_TYPE=exe"
)

set "SRC_DIR=source\cpp"
set "BIN_DIR=lib"
set "TMP_DIR=%TEMP%\complie_tmp"

if /I "%ACTION%"=="clean" (
    echo Cleaning output directories...
    if exist "%BIN_DIR%" rmdir /s /q "%BIN_DIR%"
    if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
    echo Clean complete.
    goto :eof
)

rem Require Native Tools Prompt (cl.exe must be in PATH)
where.exe cl >nul 2>&1
if errorlevel 1 (
    echo ERROR: cl.exe not found in PATH.
    echo Please run this script from a Visual Studio Native Tools Command Prompt.
    goto :fail
)

set "FLAGS=/nologo /EHsc"
if /I "%OUT_TYPE%"=="dll" (
    set "FLAGS=%FLAGS% /LD"
) else (
    set "FLAGS=%FLAGS% /Fe"
)

if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

rem Use a temp directory for intermediate objects and delete it afterward.
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%"

echo Building (config=%CONFIG%, arch=%ARCH%, type=%OUT_TYPE%)...

for %%f in ("%SRC_DIR%\*.cpp") do (
    echo Compiling: %%f
    set "OUTFILE=%BIN_DIR%\%%~nf.%OUT_TYPE%"
    set "OBJFILE=%TMP_DIR%\%%~nf.obj"

    cl %FLAGS% /Fe"!OUTFILE!" /Fo"!OBJFILE!" "%%f"

    if !errorlevel! equ 0 (
        echo [ok] %%~nf.%OUT_TYPE%
    ) else (
        echo [fail] %%f
    )
)

rem Clean up intermediate objects
if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"

echo Build complete.

pause

goto :eof

:usage
    echo Usage:
    echo   complie.bat [Debug^|Release] [x86^|x64] [dll^|exe]
    echo   complie.bat clean
    pause
    goto :eof

:fail
    echo ERROR: MSVC build environment not configured.
    echo Please run from a Visual Studio Native Tools Command Prompt,
    echo or set VCVARSALL to the full path of vcvarsall.bat.
    pause
    exit /b 1
