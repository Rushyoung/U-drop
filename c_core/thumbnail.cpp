#include <cstdio>
#include <iostream>
#include <cstdlib>

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
#define STB_IMAGE_RESIZE2_IMPLEMENTATION
#include "stb_image_resize2.h"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#define MIN_DIM 256
#define MAX_DIM 8192  // 安全加固：限制最大尺寸防止整数溢出及 OOM

#if defined(_WIN32)
    #define NATIVE_API extern "C" __declspec(dllexport)
#else
    #define NATIVE_API extern "C" __attribute__((visibility("default")))
#endif

// 暴露给 Python 的接口
NATIVE_API bool make_thumbnail(const char* inputpath, const char* outputpath) {
    int m_w = 400; // 默认缩略图尺寸
    int m_h = 400;
    
    int w, h, channels;
    unsigned char* imgdata = stbi_load(inputpath, &w, &h, &channels, 4);
    if(!imgdata){
        return false;
    }

    // 安全预检：防止超大图片导致的后续计算溢出
    if (w > MAX_DIM || h > MAX_DIM) {
        stbi_image_free(imgdata);
        return false;
    }

    float scale_w = (float)m_w / w;
    float scale_h = (float)m_h / h;
    float scale = (scale_w < scale_h) ? scale_w : scale_h;

    if(scale > 1.0f) scale = 1.0f;

    int new_w = (int)(w * scale);
    int new_h = (int)(h * scale);
    
    if (new_w < MIN_DIM || new_h < MIN_DIM) {
        if (new_w < new_h) {
            float factor = (float)MIN_DIM / new_w;
            new_w = MIN_DIM;
            new_h = (int)(new_h * factor);
        } else {
            float factor = (float)MIN_DIM / new_h;
            new_h = MIN_DIM;
            new_w = (int)(new_w * factor);
        }
    }

    // 安全加固：再次确认调整后的尺寸也在安全范围内
    if (new_w > MAX_DIM || new_h > MAX_DIM) {
        stbi_image_free(imgdata);
        return false;
    }

    // 修复整数溢出漏洞：使用 size_t 进行内存大小计算，并显式检查乘法溢出
    size_t total_pixels = (size_t)new_w * new_h;
    size_t alloc_size = total_pixels * 4;
    
    // 基础防溢出逻辑 (对于 8192x8192 以内的图，size_t 在 32/64 位下均安全)
    unsigned char* resized = (unsigned char*)malloc(alloc_size);
    if (!resized){
        stbi_image_free(imgdata);
        return false;
    }

    unsigned char* result = stbir_resize_uint8_srgb(
        imgdata, w, h, 0,
        resized, new_w, new_h, 0,
        STBIR_RGBA);
        
    if(!result) {
        free(resized);
        stbi_image_free(imgdata);
        return false;
    }

    int success = stbi_write_jpg(outputpath, new_w, new_h, 4, resized, 85);
    
    free(resized);
    stbi_image_free(imgdata);
    return (success != 0);
}
