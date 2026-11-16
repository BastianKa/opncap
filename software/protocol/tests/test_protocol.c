/* SPDX-License-Identifier: Apache-2.0 */
/* Host-side test of the generated C header against the shared vectors. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "opncap_protocol.h"

static int hex_to_bytes(const char *hex, uint8_t *out, size_t n) {
    if (strlen(hex) != n * 2) return -1;
    for (size_t i = 0; i < n; i++) {
        unsigned v;
        if (sscanf(hex + 2 * i, "%2x", &v) != 1) return -1;
        out[i] = (uint8_t)v;
    }
    return 0;
}

static int error_code(const char *name) {
    if (!strcmp(name, "magic")) return OPNCAP_ERR_MAGIC;
    if (!strcmp(name, "crc")) return OPNCAP_ERR_CRC;
    if (!strcmp(name, "version")) return OPNCAP_ERR_VERSION;
    if (!strcmp(name, "length")) return OPNCAP_ERR_LENGTH;
    if (!strcmp(name, "padding")) return OPNCAP_ERR_PADDING;
    return 1;
}

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: %s vectors.txt\n", argv[0]); return 2; }
    int failures = 0, checked = 0;

    if (opncap_crc16((const uint8_t *)"123456789", 9) != 0x29B1) { puts("FAIL crc check value"); failures++; }

    FILE *fp = fopen(argv[1], "r");
    if (!fp) { perror("vectors"); return 2; }
    char line[512];
    while (fgets(line, sizeof line, fp)) {
        char kind[16], a[64], b[16], hex[128];
        uint8_t raw[OPNCAP_FRAME_SIZE], again[OPNCAP_FRAME_SIZE];
        opncap_frame_t f;
        if (line[0] == '#' || line[0] == '\n') continue;
        if (sscanf(line, "%15s", kind) != 1) continue;
        if (!strcmp(kind, "valid")) {
            if (sscanf(line, "%*s %63s %15s %127s", a, b, hex) != 3 || hex_to_bytes(hex, raw, sizeof raw)) { puts("FAIL parse"); failures++; continue; }
            if (opncap_frame_decode(raw, &f) != OPNCAP_OK || f.seq != atoi(b)
                || opncap_frame_encode(&f, again) != 0 || memcmp(raw, again, sizeof raw)) {
                printf("FAIL valid %s\n", a); failures++;
            }
        } else {
            if (sscanf(line, "%*s %63s %127s", a, hex) != 2 || hex_to_bytes(hex, raw, sizeof raw)) { puts("FAIL parse"); failures++; continue; }
            if (opncap_frame_decode(raw, &f) != error_code(a)) { printf("FAIL invalid %s\n", a); failures++; }
        }
        checked++;
    }
    fclose(fp);
    printf("%d vectors checked, %d failures\n", checked, failures);
    return failures ? 1 : 0;
}
