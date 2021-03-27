// Just some helpful code for debugging

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ROTL(a,b) (((a) << (b)) | ((a) >> (32 - (b))))
#define QR(a, b, c, d) (			\
    a += b,  d ^= a,  d = ROTL(d,16),	\
    c += d,  b ^= c,  b = ROTL(b,12),	\
    a += b,  d ^= a,  d = ROTL(d, 8),	\
    c += d,  b ^= c,  b = ROTL(b, 7))
#define ROUNDS 20

void chacha_block(uint32_t out[16], uint32_t const in[16])
{
    int i;
    uint32_t x[16];

    for (i = 0; i < 16; ++i)
        x[i] = in[i];

    for (int i = 0; i < 16; i++) {
        printf("%08x\n", x[i]);
    }

    // 10 loops × 2 rounds/loop = 20 rounds
    for (i = 0; i < ROUNDS; i += 2) {
        printf("----- %d ----- \n", i+1);
        // Odd round
        QR(x[0], x[4], x[ 8], x[12]); // column 0
        QR(x[1], x[5], x[ 9], x[13]); // column 1
        QR(x[2], x[6], x[10], x[14]); // column 2
        QR(x[3], x[7], x[11], x[15]); // column 3

        for (int i = 0; i < 16; i++) {
            printf("%02d %08x\n", i, x[i]);
        }

        printf("----- %d (even) ----- \n", i+2);

        // Even round
        QR(x[0], x[5], x[10], x[15]); // diagonal 1 (main diagonal)
        QR(x[1], x[6], x[11], x[12]); // diagonal 2
        QR(x[2], x[7], x[ 8], x[13]); // diagonal 3
        QR(x[3], x[4], x[ 9], x[14]); // diagonal 4

        for (int i = 0; i < 16; i++) {
            printf("%02d %08x\n", i, x[i]);
        }

    }
    for (i = 0; i < 16; ++i)
        out[i] = x[i] + in[i];
}

int main(void)
{
    uint32_t state[16];
    uint32_t key[8] = {
        0x03020100,
        0x07060504,
        0x0b0a0908,
        0x0f0e0d0c,
        0x13121110,
        0x17161514,
        0x1b1a1918,
        0x1f1e1d1c,
    };

    uint32_t iv[3] = {
        0x33221100,
        0x77665544,
        0xbbaa9988,
    };

    state[0]  = 0x61707865; /* "expa" */
    state[1]  = 0x3320646e; /* "nd 3" */
    state[2]  = 0x79622d32; /* "2-by" */
    state[3]  = 0x6b206574; /* "te k" */
    state[4]  = key[0];
    state[5]  = key[1];
    state[6]  = key[2];
    state[7]  = key[3];
    state[8]  = key[4];
    state[9]  = key[5];
    state[10] = key[6];
    state[11] = key[7];
    state[12] = 0; // counter
    state[13] = iv[0];
    state[14] = iv[1];
    state[15] = iv[2];

    // memset(state, 0, sizeof(state));
    // state[0] = 0x01000000;

    uint32_t out[16] = {0};

    chacha_block(out, state);

    for (int i = 0; i < 16; i++) {
        printf("%08x\n", out[i]);
    }

    uint8_t *out_bytes = (uint8_t *) out;
    for (int i = 0; i < 16*4; i++) {
        printf("%02x ", out_bytes[i]);
        if (i % 8 == 7) printf("\n");
    }

    return 0;
}