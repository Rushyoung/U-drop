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

#ifdef _WIN32
  #define API_EXPORT extern "C" __declspec(dllexport)
#else
  #define API_EXPORT extern "C"
#endif

API_EXPORT int thumbnail(const char* inputpath, const char* outputpath, int m_w, int m_h){
    int w, h, channels;
    unsigned char* imgdata = stbi_load(inputpath, &w, &h, &channels, 4);
    if(!imgdata){
        return 1;

    }

    float scale_w = (float)m_w / w;
    float scale_h = (float)m_h / h;
    float scale = (scale_w < scale_h)?scale_w : scale_h;

    if(scale > 1.0f) scale = 1.0f;

    int new_w = (float)(w * scale);
    int new_h = (float)(h * scale);
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

    unsigned char* resized = (unsigned char*)malloc(new_w * new_h * 4);
    if (!resized){
        stbi_image_free(imgdata);
        return 2;
    }

    unsigned char* result = stbir_resize_uint8_srgb(
        imgdata, w, h, 0,
        resized, new_w, new_h, 0,
        STBIR_RGBA);
    if(!result) {
        free(resized);
        stbi_image_free(imgdata);
        return 3;
    }

    int success = stbi_write_jpg(outputpath, new_w, new_h, 4, resized, 85);
    if (!success) {
        free(resized);
        stbi_image_free(imgdata);
        return 4;
    }

    free(resized);
    stbi_image_free(imgdata);
    return 0;
}

// int main(int argc, char* argv[]){


//     const char* inputFile = argv[1];
//     const char* outputFile = argv[2];


//     int ret = thumbnail(inputFile, outputFile);
//     printf("%d", ret);
//     return ret;
// }


