"""Leitura e gravação das texturas .ftex (uniformes) do PES 2021."""
import struct, zlib, io
from PIL import Image

FOURCC = {2: b'DXT1', 3: b'DXT3', 4: b'DXT5'}


def read(path) -> Image.Image:
    f = open(path, 'rb').read()
    pf, w, h, dep, mips = struct.unpack_from('<HHHHB', f, 8)
    off, us, cs, idx, fn, cc = struct.unpack_from('<IIIBBH', f, 0x40)
    out = bytearray()
    for c in range(cc):
        csz, usz, coff = struct.unpack_from('<HHI', f, off + 8 * c)
        coff &= 0x7fffffff
        blk = f[off + coff:off + coff + csz]
        out += blk if csz == usz else zlib.decompress(blk)
    if pf == 11:          # BC7 (números, nome e número do calção)
        hdr = struct.pack('<4sIIIIIII44sII4s5I5I', b'DDS ', 124, 0x81007, h, w, len(out), 0, 1,
                          b'\0' * 44, 32, 4, b'DX10', 0, 0, 0, 0, 0, 0x1000, 0, 0, 0, 0)
        hdr += struct.pack('<5I', 98, 3, 0, 1, 0)
        return Image.open(io.BytesIO(hdr + bytes(out[:w * h]))).convert('RGBA')
    fourcc = FOURCC.get(pf)
    if fourcc is None:
        return Image.frombytes('RGBA', (w, h), bytes(out[:w * h * 4]), 'raw', 'BGRA')
    hdr = struct.pack('<4sIIIIIII44sII4s5I5I', b'DDS ', 124, 0x81007, h, w, len(out), 0, 1,
                      b'\0' * 44, 32, 4, fourcc, 0, 0, 0, 0, 0, 0x1000, 0, 0, 0, 0)
    return Image.open(io.BytesIO(hdr + bytes(out))).convert('RGBA')


def write(img: Image.Image, template_path, out_path):
    import etcpak
    t = open(template_path, 'rb').read()
    pf, w, h, dep, mips = struct.unpack_from('<HHHHB', t, 8)
    hdr = bytearray(t[:0x40])
    bc7 = pf == 11 and hasattr(etcpak, 'compress_bc7')
    struct.pack_into('<H', hdr, 8, 11 if bc7 else 4)  # BC7 quando o original é BC7; senão DXT5
    img = img.convert('RGBA')
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    # cor e transparência são reduzidas separadamente: o canal alfa dos uniformes é 0 e,
    # reduzindo junto, o Pillow escurece a cor (o uniforme ficava preto de longe)
    rgb0 = img.convert('RGB'); a0 = img.getchannel('A')
    base = 0x40 + 16 * mips
    data = bytearray(); entries = []
    for m in range(mips):
        mw, mh = max(1, w >> m), max(1, h >> m)
        if m:
            im = rgb0.resize((mw, mh), Image.LANCZOS).convert('RGBA')
            im.putalpha(a0.resize((mw, mh), Image.LANCZOS))
        else:
            im = img
        pw, ph = max(4, mw), max(4, mh)
        if (pw, ph) != (mw, mh):
            pad = Image.new('RGBA', (pw, ph)); pad.paste(im, (0, 0)); im = pad
        comp = (etcpak.compress_bc7 if bc7 else etcpak.compress_bc3)(im.tobytes(), pw, ph)
        chunks = [comp[i:i + 16384] for i in range(0, len(comp), 16384)]
        ctab = bytearray(); cdata = bytearray(); off = 8 * len(chunks)
        for c in chunks:
            z = zlib.compress(c, 6)
            if len(z) >= len(c):
                z = c
            ctab += struct.pack('<HHI', len(z), len(c), off + len(cdata)); cdata += z
        blob = ctab + cdata
        entries.append(struct.pack('<IIIBBH', base + len(data), len(comp), len(blob), m, 0, len(chunks)))
        data += blob
    tmp = str(out_path) + '.tmp'
    with open(tmp, 'wb') as fo:
        fo.write(bytes(hdr) + b''.join(entries) + bytes(data))
    import os
    os.replace(tmp, out_path)
