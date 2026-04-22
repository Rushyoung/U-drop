/*
 * MD5/SHA256/BLAKE3 算法实现（纯 C）
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#ifdef _WIN32
    #include <windows.h>
#endif

#if defined(__EMSCRIPTEN__)
    #include <emscripten/emscripten.h>
#endif

#ifdef __cplusplus
extern "C" {
#endif

// 导出宏
#if defined(_WIN32)
    #define MD5_API __declspec(dllexport)
#elif defined(__EMSCRIPTEN__)
    #define MD5_API EMSCRIPTEN_KEEPALIVE
#else
    #define MD5_API __attribute__((visibility("default")))
#endif

typedef struct {
    uint32_t state[4];
    uint32_t count[2];
    unsigned char buffer[64];
} MD5_CTX;

#define ROTATE_LEFT(x, n) (((x) << (n)) | ((x) >> (32 - (n))))
#define ROTR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))

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

static const int s_md5[] = {
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
    5,  9, 14, 20, 5,  9, 14, 20, 5,  9, 14, 20, 5,  9, 14, 20,
    4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
    6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21
};

void MD5_Init(MD5_CTX *ctx) {
    ctx->count[0] = ctx->count[1] = 0;
    ctx->state[0] = 0x67452301; ctx->state[1] = 0xefcdab89; ctx->state[2] = 0x98badcfe; ctx->state[3] = 0x10325476;
}

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

MD5_API void MD5_Init_Ex(MD5_CTX *ctx) { MD5_Init(ctx); }
MD5_API void MD5_Update_Ex(MD5_CTX *ctx, const unsigned char *input, size_t input_len) { MD5_Update(ctx, input, input_len); }
MD5_API void MD5_Final_Ex(unsigned char digest[16], MD5_CTX *ctx) { MD5_Final(digest, ctx); }

static void DigestToHex(const unsigned char digest[16], char *md5Result) {
    for (int i = 0; i < 16; i++) sprintf(&md5Result[i*2], "%02x", digest[i]);
    md5Result[32] = '\0';
}

MD5_API int CalculateFileMD5(const char *filePath, char *md5Result) {
    if (filePath == NULL || md5Result == NULL) return -1;
    FILE *file = fopen(filePath, "rb"); if (file == NULL) return -1;
    MD5_CTX ctx; MD5_Init(&ctx); unsigned char buffer[4096]; size_t bytes_read;
    while ((bytes_read = fread(buffer, 1, sizeof(buffer), file)) > 0) MD5_Update(&ctx, buffer, bytes_read);
    unsigned char digest[16]; MD5_Final(digest, &ctx); fclose(file); DigestToHex(digest, md5Result); return 0;
}

MD5_API int CalculateFastFileMD5(const char *filePath, char *md5Result) {
    if (filePath == NULL || md5Result == NULL) return -1;
    FILE *file = fopen(filePath, "rb"); if (file == NULL) return -1;
#if defined(_WIN32)
    _fseeki64(file, 0, SEEK_END); long long fileSize = _ftelli64(file);
#else
    fseeko(file, 0, SEEK_END); off_t fileSize = ftello(file);
#endif
    MD5_CTX ctx; MD5_Init(&ctx); unsigned char buffer[4096]; size_t bytesRead;
    const long long blockSize = 4096;
    if (fileSize <= blockSize * 3) { rewind(file); while ((bytesRead = fread(buffer, 1, sizeof(buffer), file)) > 0) MD5_Update(&ctx, buffer, bytesRead); }
    else {
#if defined(_WIN32)
        _fseeki64(file, 0, SEEK_SET); bytesRead = fread(buffer, 1, blockSize, file); MD5_Update(&ctx, buffer, bytesRead);
        _fseeki64(file, (fileSize - blockSize) / 2, SEEK_SET); bytesRead = fread(buffer, 1, blockSize, file); MD5_Update(&ctx, buffer, bytesRead);
        _fseeki64(file, fileSize - blockSize, SEEK_SET); bytesRead = fread(buffer, 1, blockSize, file); MD5_Update(&ctx, buffer, bytesRead);
#else
        fseeko(file, 0, SEEK_SET); bytesRead = fread(buffer, 1, blockSize, file); MD5_Update(&ctx, buffer, bytesRead);
        fseeko(file, (fileSize - blockSize) / 2, SEEK_SET); bytesRead = fread(buffer, 1, blockSize, file); MD5_Update(&ctx, buffer, bytesRead);
        fseeko(file, fileSize - blockSize, SEEK_SET); bytesRead = fread(buffer, 1, blockSize, file); MD5_Update(&ctx, buffer, bytesRead);
#endif
    }
    unsigned char digest[16]; MD5_Final(digest, &ctx); fclose(file); DigestToHex(digest, md5Result); return 0;
}

// BLAKE3 Implementation
static const uint32_t IV[] = {0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19};
static const uint8_t MSG_PERMUTATION[] = {2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8};

#define G(s, a, b, c, d, x, y) \
    s[a] += s[b] + x; s[d] = ROTR(s[d] ^ s[a], 16); \
    s[c] += s[d];     s[b] = ROTR(s[b] ^ s[c], 12); \
    s[a] += s[b] + y; s[d] = ROTR(s[d] ^ s[a], 8);  \
    s[c] += s[d];     s[b] = ROTR(s[b] ^ s[c], 7);

typedef struct { uint32_t cv[8]; uint64_t chunk_counter; uint8_t buf[64]; uint8_t buf_len; uint8_t flags; } BLAKE3_CTX;

static void blake3_compress(const uint32_t cv[8], const uint8_t block[64], uint64_t counter, uint8_t block_len, uint8_t flags, uint32_t out[16]) {
    uint32_t s[16] = { cv[0], cv[1], cv[2], cv[3], cv[4], cv[5], cv[6], cv[7], IV[0], IV[1], IV[2], IV[3], (uint32_t)counter, (uint32_t)(counter >> 32), (uint32_t)block_len, (uint32_t)flags };
    uint32_t m[16];
    for (int i = 0; i < 16; i++) m[i] = (uint32_t)block[i*4] | ((uint32_t)block[i*4+1] << 8) | ((uint32_t)block[i*4+2] << 16) | ((uint32_t)block[i*4+3] << 24);
    for (int r = 0; r < 7; r++) {
        G(s, 0, 4, 8, 12, m[0], m[1]);  G(s, 1, 5, 9, 13, m[2], m[3]);  G(s, 2, 6, 10, 14, m[4], m[5]); G(s, 3, 7, 11, 15, m[6], m[7]);
        G(s, 0, 5, 10, 15, m[8], m[9]); G(s, 1, 6, 11, 12, m[10], m[11]); G(s, 2, 7, 8, 13, m[12], m[13]); G(s, 3, 4, 9, 14, m[14], m[15]);
        uint32_t next_m[16]; for (int i = 0; i < 16; i++) next_m[i] = m[MSG_PERMUTATION[i]]; memcpy(m, next_m, sizeof(m));
    }
    for (int i = 0; i < 8; i++) { out[i] = s[i] ^ s[i + 8]; out[i + 8] = s[i + 8] ^ cv[i]; }
}

MD5_API void BLAKE3_Init_Ex(BLAKE3_CTX *ctx) { memcpy(ctx->cv, IV, 32); ctx->chunk_counter = 0; ctx->buf_len = 0; ctx->flags = 0x01; }
MD5_API void BLAKE3_Update_Ex(BLAKE3_CTX *ctx, const uint8_t *input, size_t len) {
    while (len > 0) {
        size_t take = 64 - ctx->buf_len; if (take > len) take = len;
        memcpy(&ctx->buf[ctx->buf_len], input, take); ctx->buf_len += take; input += take; len -= take;
        if (ctx->buf_len == 64 && len > 0) {
            uint32_t out[16]; blake3_compress(ctx->cv, ctx->buf, ctx->chunk_counter, 64, ctx->flags, out);
            memcpy(ctx->cv, out, 32); ctx->buf_len = 0; ctx->flags = 0;
        }
    }
}
MD5_API void BLAKE3_Final_Ex(uint8_t digest[32], BLAKE3_CTX *ctx) {
    uint32_t out[16]; uint8_t flags = ctx->flags | 0x08 | 0x04; // ROOT | CHUNK_END
    blake3_compress(ctx->cv, ctx->buf, ctx->chunk_counter, ctx->buf_len, flags, out); memcpy(digest, out, 32);
}

static void DigestToHex64(const unsigned char digest[32], char *hexResult) {
    for (int i = 0; i < 32; i++) sprintf(&hexResult[i*2], "%02x", digest[i]);
    hexResult[64] = '\0';
}

MD5_API int CalculateFileBLAKE3(const char *filePath, char *hexResult) {
    if (filePath == NULL || hexResult == NULL) return -1;
    FILE *file = fopen(filePath, "rb"); if (file == NULL) return -1;
    BLAKE3_CTX ctx; BLAKE3_Init_Ex(&ctx); unsigned char buffer[8192]; size_t bytes_read;
    while ((bytes_read = fread(buffer, 1, sizeof(buffer), file)) > 0) BLAKE3_Update_Ex(&ctx, (uint8_t*)buffer, bytes_read);
    unsigned char digest[32]; BLAKE3_Final_Ex(digest, &ctx); fclose(file); DigestToHex64(digest, hexResult); return 0;
}

#ifdef _WIN32
BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) { return TRUE; }
#endif
#ifdef __cplusplus
}
#endif
