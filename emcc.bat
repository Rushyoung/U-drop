@echo off
rem ------------------------------------------------------------
rem Simple wrapper for emcc (Emscripten) in an emsdk-activated shell.
rem Usage:
rem   emcc.bat           (builds test/md5.js from source/cpp/MD5.c)
rem   emcc.bat clean     (removes test/md5.js and test/md5.wasm)
rem   emcc.bat help      (prints this help)
rem ------------------------------------------------------------

if "%~1"=="" goto :build
if /I "%~1"=="help" goto :usage
if /I "%~1"=="/?" goto :usage
if /I "%~1"=="clean" goto :clean






















n:usage
necho Usage:
necho   emcc.bat           - build test/md5.js
necho   emcc.bat clean     - remove output files
necho   emcc.bat help      - show this message
ngoto :eofgoto :eof
n:clean
necho Cleaning output...
ndel /q /f "test\md5.js" 2>nul
ndel /q /f "test\md5.wasm" 2>nul
necho Clean complete.goto :eof
necho Build finished.  -o "%OUT%"  -s EXPORTED_RUNTIME_METHODS='["cwrap","UTF8ToString","HEAPU8","HEAPU32"]' ^  -s EXPORTED_FUNCTIONS="['_MD5_Init_Ex','_MD5_Update_Ex','_MD5_Final_Ex','_SHA256_Init_Ex','_SHA256_Update_Ex','_SHA256_Final_Ex','_BLAKE3_Init_Ex','_BLAKE3_Update_Ex','_BLAKE3_Final_Ex','_BLAKE3_Compress_Parent_Ex','_malloc','_free','_CalculateFastFileMD5','_CalculateFileMD5']" ^  -s WASM=1 -s MODULARIZE=1 -s EXPORT_NAME="MD5Module" ^emcc "%SRC%" -O3 -msimd128 ^
necho Building WASM module to %OUT%...set "OUT=test\md5.js"set "SRC=source\cpp\MD5.c"
n:build)    goto :eof    echo Please run this from an activated emsdk environment (emsdk_env.bat).    echo ERROR: emcc not found in PATH.where.exe emcc >nul 2>&1
nif errorlevel 1 (nrem Ensure emcc is available