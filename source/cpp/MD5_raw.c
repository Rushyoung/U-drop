#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <windows.h> // Windows下DLL必需；Linux需替换为gcc的导出属性

// ==================== 关键修改1：定义动态库导出宏（跨平台兼容） ====================
// 原因：动态库需要明确标记哪些函数对外暴露（导出），不同系统的导出语法不同
#ifdef _WIN32
    // Windows下的导出宏（__declspec(dllexport)）
    #define MD5_API __declspec(dllexport)
#else
    // Linux/Mac下的导出宏（gcc的visibility属性）
    #define MD5_API __attribute__((visibility("default")))
#endif

// MD5上下文结构体（保留，算法核心依赖）
typedef struct {
    uint32_t state[4];
    uint32_t count[2];
    unsigned char buffer[64];
} MD5_CTX;

// 循环左移宏（保留）
#define ROTATE_LEFT(x, n) (((x) << (n)) | ((x) >> (32 - (n))))

// MD5常量、位移量（保留，算法核心）
static const uint32_t T[] = {
    0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee,
    0xf57c0faf, 0x4787c62a, 0xa8304613, 0xfd469501,
    0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be,
    0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821,
    0xf61e2562, 0xc040b340, 0x265e5a51, 0xe9b6c7aa,
    0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
    0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed,
    0xa9e3e905, 0xfcefa3f8, 0x676f02d9, 0x8d2a4c8a,
    0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c,
    0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70,
    0x289b7ec6, 0xeaa127fa, 0xd4ef3085, 0x04881d05,
    0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
    0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039,
    0x655b59c3, 0x8f0ccc92, 0xffeff47d, 0x85845dd1,
    0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1,
    0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391
};

static const int s[] = {
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
    5,  9, 14, 20, 5,  9, 14, 20, 5,  9, 14, 20, 5,  9, 14, 20,
    4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
    6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21
};

// MD5核心函数（保留，static改为全局，或保持static但被导出函数调用）
void MD5_Init(MD5_CTX *ctx) {
    ctx->count[0] = ctx->count[1] = 0;
    ctx->state[0] = 0x67452301;
    ctx->state[1] = 0xefcdab89;
    ctx->state[2] = 0x98badcfe;
    ctx->state[3] = 0x10325476;
}

static void MD5_Transform(uint32_t state[4], const unsigned char block[64]) {
    uint32_t a = state[0], b = state[1], c = state[2], d = state[3];
    uint32_t x[16];
    int i;

    for (i = 0; i < 16; i++) {
        x[i] = (uint32_t)block[i*4] | ((uint32_t)block[i*4+1] << 8) |
               ((uint32_t)block[i*4+2] << 16) | ((uint32_t)block[i*4+3] << 24);
    }

    for (i = 0; i < 16; i++) {
        uint32_t f = (b & c) | ((~b) & d);
        uint32_t g = i;
        uint32_t temp = d;
        d = c;
        c = b;
        b = b + ROTATE_LEFT((a + f + T[i] + x[g]), s[i]);
        a = temp;
    }
    for (i = 16; i < 32; i++) {
        uint32_t f = (d & b) | ((~d) & c);
        uint32_t g = (5*i + 1) % 16;
        uint32_t temp = d;
        d = c;
        c = b;
        b = b + ROTATE_LEFT((a + f + T[i] + x[g]), s[i]);
        a = temp;
    }
    for (i = 32; i < 48; i++) {
        uint32_t f = b ^ c ^ d;
        uint32_t g = (3*i + 5) % 16;
        uint32_t temp = d;
        d = c;
        c = b;
        b = b + ROTATE_LEFT((a + f + T[i] + x[g]), s[i]);
        a = temp;
    }
    for (i = 48; i < 64; i++) {
        uint32_t f = c ^ (b | (~d));
        uint32_t g = (7*i) % 16;
        uint32_t temp = d;
        d = c;
        c = b;
        b = b + ROTATE_LEFT((a + f + T[i] + x[g]), s[i]);
        a = temp;
    }

    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
}

void MD5_Update(MD5_CTX *ctx, const unsigned char *input, size_t input_len) {
    uint32_t i, index, part_len;

    index = (uint32_t)((ctx->count[0] >> 3) & 0x3F);
    if ((ctx->count[0] += ((uint32_t)input_len << 3)) < ((uint32_t)input_len << 3)) {
        ctx->count[1]++;
    }
    ctx->count[1] += ((uint32_t)input_len >> 29);

    part_len = 64 - index;
    if (input_len >= part_len) {
        memcpy(&ctx->buffer[index], input, part_len);
        MD5_Transform(ctx->state, ctx->buffer);

        for (i = part_len; i + 63 < input_len; i += 64) {
            MD5_Transform(ctx->state, &input[i]);
        }
        index = 0;
    } else {
        i = 0;
    }
    memcpy(&ctx->buffer[index], &input[i], input_len - i);
}

void MD5_Final(unsigned char digest[16], MD5_CTX *ctx) {
    unsigned char padding[64] = {0};
    uint32_t index, pad_len;
    unsigned char bits[8];
    int i;

    bits[0] = (unsigned char)(ctx->count[0] & 0xFF);
    bits[1] = (unsigned char)((ctx->count[0] >> 8) & 0xFF);
    bits[2] = (unsigned char)((ctx->count[0] >> 16) & 0xFF);
    bits[3] = (unsigned char)((ctx->count[0] >> 24) & 0xFF);
    bits[4] = (unsigned char)(ctx->count[1] & 0xFF);
    bits[5] = (unsigned char)((ctx->count[1] >> 8) & 0xFF);
    bits[6] = (unsigned char)((ctx->count[1] >> 16) & 0xFF);
    bits[7] = (unsigned char)((ctx->count[1] >> 24) & 0xFF);

    padding[0] = 0x80;
    index = (uint32_t)((ctx->count[0] >> 3) & 0x3F);
    pad_len = (index < 56) ? (56 - index) : (120 - index);
    MD5_Update(ctx, padding, pad_len);
    MD5_Update(ctx, bits, 8);

    for (i = 0; i < 4; i++) {
        digest[i*4] = (unsigned char)(ctx->state[i] & 0xFF);
        digest[i*4+1] = (unsigned char)((ctx->state[i] >> 8) & 0xFF);
        digest[i*4+2] = (unsigned char)((ctx->state[i] >> 16) & 0xFF);
        digest[i*4+3] = (unsigned char)((ctx->state[i] >> 24) & 0xFF);
    }

    memset(ctx, 0, sizeof(MD5_CTX));
}

// ==================== 关键修改2：重构MD5计算函数为可调用接口 ====================
// 原因：动态库需要提供「输入输出明确」的函数，而非命令行交互；
// 入参：文件路径、输出缓冲区（存储32位MD5字符串）；返回值：0=成功，-1=失败
MD5_API int CalculateFileMD5(const char *filePath, char *md5Result) {
    if (filePath == NULL || md5Result == NULL) {
        return -1; // 入参校验：避免空指针崩溃
    }

    MD5_CTX ctx;
    unsigned char digest[16];
    FILE *file = NULL;
    unsigned char buffer[4096];
    size_t bytes_read;
    int i;

    file = fopen(filePath, "rb");
    if (file == NULL) {
        return -1; // 文件打开失败
    }

    MD5_Init(&ctx);
    while ((bytes_read = fread(buffer, 1, sizeof(buffer), file)) > 0) {
        MD5_Update(&ctx, buffer, bytes_read);
    }

    if (ferror(file)) {
        fclose(file);
        return -1; // 文件读取失败
    }

    MD5_Final(digest, &ctx);
    fclose(file);

    // 转换为32位十六进制字符串
    for (i = 0; i < 16; i++) {
        sprintf(&md5Result[i*2], "%02x", digest[i]);
    }
    md5Result[32] = '\0'; // 确保字符串结束符

    return 0;
}

// ==================== 关键修改3：移除原main函数，新增DLL入口（Windows可选） ====================
// 原因：动态库不需要main函数（命令行入口），Windows下可加DllMain作为初始化/清理入口
#ifdef _WIN32
BOOL APIENTRY DllMain(HMODULE hModule, DWORD  ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
        case DLL_PROCESS_ATTACH: // 库加载时执行
            break;
        case DLL_THREAD_ATTACH:
        case DLL_THREAD_DETACH:
        case DLL_PROCESS_DETACH: // 库卸载时执行
            break;
    }
    return TRUE;
}
#endif