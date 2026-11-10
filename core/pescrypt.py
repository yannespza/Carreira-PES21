"""Leitura e gravação dos saves do PES 2021 (port em Python do pesXdecrypter, domínio público)."""
import struct
import numpy as np

MASTER_KEY_PES21 = bytes([
    0x90, 0x61, 0xD8, 0x66, 0x43, 0x77, 0x24, 0xF8, 0x92, 0xBA, 0xB8, 0x71, 0x21, 0xC7, 0x60, 0x63,
    0xF0, 0x91, 0x9A, 0x7D, 0xED, 0x47, 0x80, 0xDE, 0x51, 0xF5, 0xDD, 0xD1, 0x08, 0xFE, 0x32, 0x84,
    0xF5, 0x09, 0x92, 0x00, 0xB2, 0x3E, 0x88, 0x9F, 0xEB, 0x24, 0x43, 0x05, 0x58, 0x76, 0x00, 0x22,
    0x9B, 0xFE, 0xEC, 0xF6, 0x50, 0x00, 0x29, 0xD3, 0x42, 0x75, 0x50, 0xB9, 0xEC, 0xD2, 0xF6, 0x75,
])
ENC_HEADER = 320
FILE_HEADER = 208


def _mt_stream(key64: bytes, n: int) -> np.ndarray:
    key = np.frombuffer(key64, '<u4').astype(np.uint32)
    try:
        bg = np.random.MT19937(0)
        bg._legacy_seeding(key)
        return bg.random_raw(n).astype(np.uint32)
    except AttributeError:
        # alternativa: o MT19937 do próprio Python (init_by_array com a chave em palavras de 32 bits)
        import random
        if key[-1] == 0:
            raise
        r = random.Random(int.from_bytes(key64, 'little'))
        return np.fromiter((r.getrandbits(32) for _ in range(n)), np.uint32, n)


def _rol(a, s):
    return ((a << np.uint32(s)) | (a >> np.uint32(32 - s))).astype(np.uint32)


def _ror(a, s):
    return ((a >> np.uint32(s)) | (a << np.uint32(32 - s))).astype(np.uint32)


def crypt_stream(key64: bytes, data: bytes) -> bytes:
    n = len(data)
    nw = n // 4
    rest = n & 3
    m = _mt_stream(key64, nw + 4 + (1 if rest else 0))
    total = nw + (1 if rest else 0)
    # c3_i, c2_i, c1_i, c0_i for every step i (see cryptStream in crypt.c)
    c3 = np.empty(total, np.uint32); c2 = np.empty(total, np.uint32)
    c1 = np.empty(total, np.uint32); c0 = np.empty(total, np.uint32)
    c3[0] = m[3]
    if total > 1:
        c3[1:] = _ror(m[4:4 + total - 1], 13)
    c2[0] = m[2]
    if total > 1:
        c2[1:] = _rol(c3[:-1], 7)
    c1[0] = m[1]
    if total > 1:
        c1[1:] = _rol(c2[:-1], 11)
    c0[0] = m[0]
    if total > 1:
        c0[1:] = _ror(c1[:-1], 15)
    ks = m[4:4 + total] ^ c3 ^ c2 ^ c1 ^ c0
    buf = bytearray(data) + bytes(4 - rest if rest else 0)
    words = np.frombuffer(bytes(buf), '<u4') ^ ks
    return words.astype('<u4').tobytes()[:n]


def _reverse_longs(b: bytes) -> bytes:
    return b''.join(b[i * 8:i * 8 + 8][::-1] for i in range(8))


def _xor_repeat(out: bytearray, inp: bytes):
    for i, v in enumerate(inp):
        out[i & 63] ^= v


def _xor_long(inp: bytes, param: int) -> bytes:
    p = struct.pack('<Q', param)
    return bytes(inp[i] ^ p[i & 7] for i in range(64))


def _crypt_header(inp: bytes, key: bytes) -> bytes:
    hk = bytearray(inp[256:320])
    _xor_repeat(hk, _reverse_longs(key))
    out = bytearray(crypt_stream(bytes(hk), inp[:ENC_HEADER]))
    out[256:320] = inp[256:320]
    return bytes(out)


class SaveFile:
    def __init__(self, enc_header, file_header, description, logo, data, serial):
        self.enc_header = enc_header
        self.file_header = bytearray(file_header)
        self.description = description
        self.logo = logo
        self.data = bytearray(data)
        self.serial = serial

    @property
    def title(self):
        return self.description.split(b'\0')[0].decode('utf-8', 'replace')

    @property
    def subtitle(self):
        parts = [p for p in self.description.split(b'\0') if p]
        return [p.decode('utf-8', 'replace') for p in parts]


def _rolling(enc_header: bytes) -> bytes:
    rk = bytearray(enc_header[:64])
    _xor_repeat(rk, enc_header[64:320])
    return bytes(rk)


def decrypt(raw: bytes, key: bytes = MASTER_KEY_PES21) -> SaveFile:
    eh = _crypt_header(raw[:ENC_HEADER], key)
    rk = _rolling(eh)
    p = ENC_HEADER
    fh = crypt_stream(_xor_long(rk, FILE_HEADER), raw[p:p + FILE_HEADER]); p += FILE_HEADER
    data_size, logo_size, desc_size, serial_len = struct.unpack_from('<4I', fh, 64)
    desc = crypt_stream(_xor_long(rk, 0), raw[p:p + desc_size]); p += desc_size
    logo = crypt_stream(_xor_long(rk, 1), raw[p:p + logo_size]); p += logo_size
    data = crypt_stream(_xor_long(rk, 2), raw[p:p + data_size]); p += data_size
    serial = crypt_stream(_xor_long(rk, 3), raw[p:p + serial_len * 2])
    return SaveFile(eh, fh, desc, logo, data, serial)


def encrypt(sf: SaveFile, key: bytes = MASTER_KEY_PES21) -> bytes:
    fh = bytearray(sf.file_header)
    struct.pack_into('<4I', fh, 64, len(sf.data), len(sf.logo), len(sf.description), len(sf.serial) // 2)
    rk = _rolling(sf.enc_header)
    out = [_crypt_header(sf.enc_header, key),
           crypt_stream(_xor_long(rk, FILE_HEADER), bytes(fh)),
           crypt_stream(_xor_long(rk, 0), sf.description),
           crypt_stream(_xor_long(rk, 1), sf.logo),
           crypt_stream(_xor_long(rk, 2), bytes(sf.data)),
           crypt_stream(_xor_long(rk, 3), sf.serial)]
    return b''.join(out)
