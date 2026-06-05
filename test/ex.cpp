#include <stdio.h>
#if defined(_WIN32) || defined(_WIN64)
    #define DLL_EXPORT __declspec(dllexport)
#else
    #define DLL_EXPORT
#endif

extern "C" {
    DLL_EXPORT int add(int a, int b){
        return a+b;
    }
    DLL_EXPORT void hello(){
        printf("hello world");
    }
}