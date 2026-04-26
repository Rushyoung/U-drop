#include <stdio.h>
#include <windows.h>

// 定义函数指针类型（严格匹配DLL导出函数的签名）
typedef int (*CalculateFileMD5Func)(const char* filePath, char* md5Result);

int main() {
    char md5Result[33] = {0}; // 存储32位MD5字符串 + 结束符
    HMODULE hDll = NULL;
    CalculateFileMD5Func calculateFunc = NULL;

    // 加载DLL（注意路径：若DLL和exe同目录，直接写文件名即可）
    hDll = LoadLibrary("FileMD5Lib.dll");
    if (hDll == NULL) {
        // 修复点1：DWORD用%lu（无符号长整型）格式化，或强制转为int
        DWORD errorCode = GetLastError();
        printf("加载动态库失败！错误码：%lu\n", errorCode);
        return 1;
    }

    // 核心修复：通过void*过渡转换函数指针（消除类型不兼容警告）
    FARPROC tempProc = GetProcAddress(hDll, "CalculateFileMD5");
    if (tempProc == NULL) {
        // 修复点2：同上，DWORD用%lu格式化
        DWORD errorCode = GetLastError();
        printf("获取函数CalculateFileMD5失败！错误码：%lu\n", errorCode);
        FreeLibrary(hDll);
        return 1;
    }
    // 先转void*，再转目标函数指针（编译器认可的安全转换方式）
    calculateFunc = (CalculateFileMD5Func)(void*)tempProc;

    // 调用DLL函数计算MD5
    int ret = calculateFunc("D:/test.txt", md5Result);
    if (ret == 0) {
        printf("文件MD5值：%s\n", md5Result);
    } else {
        printf("计算MD5失败！错误码：%d\n", ret);
    }

    // 释放DLL资源
    FreeLibrary(hDll);
    return 0;
}