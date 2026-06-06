/*
 * U-Drop Unified Hash Core (v1.0.0 Monorepo 版)
 * 整合：
 * 1. 后端原生接口 (CalculateFileBLAKE3, CalculateFastFileMD5)
 * 2. 前端 WASM 流式接口 (BLAKE3_Init_Ex, BLAKE3_Update_Ex, BLAKE3_Final_Ex, etc.)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "blake3/blake3.h"

// 宏隔离与跨平台大文件支持
#ifndef __EMSCRIPTEN__
    #ifdef _WIN32
        #include <windows.h>
        #define FSEEK _fseeki64
        #define FTELL _ftelli64
        #define OFF_T int64_t
    #else
        #define _FILE_OFFSET_BITS 64
        #include <unistd.h>
        #define FSEEK fseeko
        #define FTELL ftello
        #define OFF_T int64_t
    #endif
#else
    #include <emscripten/emscripten.h>
    #define FSEEK fseek
    #define FTELL ftell
    #define OFF_T long
#endif

#ifdef __cplusplus
extern "C" {
#endif

// 统一导出宏：确保在 Windows 下不发生名称粉碎 (Name Mangling)
#if defined(__EMSCRIPTEN__)
    #define NATIVE_API EMSCRIPTEN_KEEPALIVE
#elif defined(_WIN32)
    #define NATIVE_API __declspec(dllexport)
#else
    #define NATIVE_API __attribute__((visibility("default")))
#endif

// --- MD5 Implementation ---
typedef struct {
    uint32_t state[4];
    uint32_t count[2];
    unsigned char buffer[64];
} MD5_CTX;

#define ROTATE_LEFT(x, n) (((x) << (n)) | ((x) >> (32 - (n))))

static const uint32_t T[] = {
    0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee, 0xf57c0faf, 0x4787c62a, 0xa8304613, 0xfd469501,
    0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be, 0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821,
    0xf61e2562, 0xc040b340, 0x265e5a51, 0xe9b6c7aa, 0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
    0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed, 0xa9e3e905, 0xfcefa3f8, 0x676f02d9, 0x8d2a4c8a,
    0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c, 0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70,
    0x289b7ec6, 0xeaa127fa, 0xd4ef3085, 0x04881d05, 0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
    0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039, 0x655b59c3, 0x8f0ccc92, 0xffeff47d, 0x85845dd1,
    0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1, 0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391
};

static const int s_md5[] = {
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
    5,  9, 14, 20, 5,  9, 14, 20, 5,  9, 14, 20, 5,  9, 14, 20,
    4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
    6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21
};

static void MD5_Transform(uint32_t state[4], const unsigned char block[64]) {
    uint32_t a = state[0], b = state[1], c = state[2], d = state[3], x[16];
    for (int i = 0; i < 16; i++) x[i] = (uint32_t)block[i*4] | ((uint32_t)block[i*4+1] << 8) | ((uint32_t)block[i*4+2] << 16) | ((uint32_t)block[i*4+3] << 24);
    for (int i = 0; i < 64; i++) {
        uint32_t f, g;
        if (i < 16) { f = (b & c) | ((~b) & d); g = i; }
        else if (i < 32) { f = (d & b) | ((~d) & c); g = (5*i + 1) % 16; }
        else if (i < 48) { f = b ^ c ^ d; g = (3*i + 5) % 16; }
        else { f = c ^ (b | (~d)); g = (7*i) % 16; }
        uint32_t temp = d; d = c; c = b;
        b = b + ROTATE_LEFT((a + f + T[i] + x[g]), s_md5[i]);
        a = temp;
    }
    state[0] += a; state[1] += b; state[2] += c; state[3] += d;
}

void MD5_Init(MD5_CTX *ctx) {
    ctx->count[0] = ctx->count[1] = 0;
    ctx->state[0] = 0x67452301; ctx->state[1] = 0xefcdab89; ctx->state[2] = 0x98badcfe; ctx->state[3] = 0x10325476;
}

void MD5_Update(MD5_CTX *ctx, const unsigned char *input, size_t input_len) {
    uint32_t i, index, part_len; index = (uint32_t)((ctx->count[0] >> 3) & 0x3F);
    if ((ctx->count[0] += ((uint32_t)input_len << 3)) < ((uint32_t)input_len << 3)) ctx->count[1]++;
    ctx->count[1] += ((uint32_t)input_len >> 29);
    part_len = 64 - index;
    if (input_len >= part_len) { memcpy(&ctx->buffer[index], input, part_len); MD5_Transform(ctx->state, ctx->buffer); for (i = part_len; i + 63 < input_len; i += 64) MD5_Transform(ctx->state, &input[i]); index = 0; }
    else i = 0; memcpy(&ctx->buffer[index], &input[i], input_len - i);
}

void MD5_Final(unsigned char digest[16], MD5_CTX *ctx) {
    unsigned char padding[64] = {0x80}; uint32_t index, pad_len; unsigned char bits[8];
    bits[0] = (unsigned char)(ctx->count[0] & 0xFF); bits[1] = (unsigned char)((ctx->count[0] >> 8) & 0xFF);
    bits[2] = (unsigned char)((ctx->count[0] >> 16) & 0xFF); bits[3] = (unsigned char)((ctx->count[0] >> 24) & 0xFF);
    bits[4] = (unsigned char)(ctx->count[1] & 0xFF); bits[5] = (unsigned char)((ctx->count[1] >> 8) & 0xFF);
    bits[6] = (unsigned char)((ctx->count[1] >> 16) & 0xFF); bits[7] = (unsigned char)((ctx->count[1] >> 24) & 0xFF);
    index = (uint32_t)((ctx->count[0] >> 3) & 0x3F); pad_len = (index < 56) ? (56 - index) : (120 - index);
    MD5_Update(ctx, padding, pad_len); MD5_Update(ctx, bits, 8);
    for (int i = 0; i < 4; i++) { digest[i*4] = (unsigned char)(ctx->state[i] & 0xFF); digest[i*4+1] = (unsigned char)((ctx->state[i] >> 8) & 0xFF); digest[i*4+2] = (unsigned char)((ctx->state[i] >> 16) & 0xFF); digest[i*4+3] = (unsigned char)((ctx->state[i] >> 24) & 0xFF); }
}

NATIVE_API void MD5_Init_Ex(MD5_CTX *ctx) { MD5_Init(ctx); }
NATIVE_API void MD5_Update_Ex(MD5_CTX *ctx, const unsigned char *input, size_t input_len) { MD5_Update(ctx, input, input_len); }
NATIVE_API void MD5_Final_Ex(unsigned char digest[16], MD5_CTX *ctx) { MD5_Final(digest, ctx); }

static void DigestToHex(const unsigned char *digest, int len, char *result) {
    for (int i = 0; i < len; i++) sprintf(&result[i*2], "%02x", digest[i]);
    result[len*2] = '\0';
}

// --- 通用哈希计算核心接口 (支持后端与前端 WASM) ---

NATIVE_API int CalculateFastFileMD5(const char *filePath, char *md5Result) {
    if (filePath == NULL || md5Result == NULL) return -1;
    FILE *file = fopen(filePath, "rb"); if (file == NULL) return -1;
    
    FSEEK(file, 0, SEEK_END);
    OFF_T fileSize = FTELL(file);
    const OFF_T blockSize = 4096;

    MD5_CTX ctx; MD5_Init(&ctx); 
    unsigned char buffer[4096]; 
    size_t bytesRead;
    
    if (fileSize <= blockSize * 3) {
        rewind(file);
        while ((bytesRead = fread(buffer, 1, sizeof(buffer), file)) > 0) MD5_Update(&ctx, buffer, bytesRead);
    } else {
        // 头
        FSEEK(file, 0, SEEK_SET); 
        bytesRead = fread(buffer, 1, (size_t)blockSize, file); 
        MD5_Update(&ctx, buffer, bytesRead);
        // 中
        FSEEK(file, (fileSize - blockSize) / 2, SEEK_SET); 
        bytesRead = fread(buffer, 1, (size_t)blockSize, file); 
        MD5_Update(&ctx, buffer, bytesRead);
        // 尾
        FSEEK(file, fileSize - blockSize, SEEK_SET); 
        bytesRead = fread(buffer, 1, (size_t)blockSize, file); 
        MD5_Update(&ctx, buffer, bytesRead);
    }
    
    unsigned char digest[16]; MD5_Final(digest, &ctx); 
    fclose(file); 
    DigestToHex(digest, 16, md5Result); 
    return 0;
}

// --- 仅后端专用：全量大文件哈希 (WASM 环境通常在 JS 侧分片调用) ---
#ifndef __EMSCRIPTEN__

NATIVE_API int CalculateFileBLAKE3(const char *filePath, char *hexResult) {
    if (filePath == NULL || hexResult == NULL) return -1;
    FILE *file = fopen(filePath, "rb"); if (file == NULL) return -1;
    blake3_hasher hasher; blake3_hasher_init(&hasher);
    unsigned char buffer[65536]; size_t bytes;
    while ((bytes = fread(buffer, 1, sizeof(buffer), file)) > 0) blake3_hasher_update(&hasher, buffer, bytes);
    uint8_t digest[32]; blake3_hasher_finalize(&hasher, digest, 32);
    fclose(file); DigestToHex(digest, 32, hexResult); return 0;
}

#endif

// --- 前端/流式：细粒度接口 (WASM 必备) ---

NATIVE_API int get_blake3_hasher_size() { return sizeof(blake3_hasher); }
NATIVE_API void BLAKE3_Init_Ex(blake3_hasher *ctx) { blake3_hasher_init(ctx); }
NATIVE_API void BLAKE3_Update_Ex(blake3_hasher *ctx, const uint8_t *data, size_t len) { blake3_hasher_update(ctx, data, len); }
NATIVE_API void BLAKE3_Final_Ex(uint8_t *digest, blake3_hasher *ctx) { blake3_hasher_finalize(ctx, digest, 32); }

#ifdef __cplusplus
}
#endif
