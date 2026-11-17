"""Draw the castle logo (same paths and pink theme colors as CastleLogo in web/js/components/Icon.js)
into app/assets/brain-castle.ico. Pure standard library: python tools/make_icon.py

Each size is rendered with 4x4 supersampling and stored as a PNG inside the .ico.
"""
import math
import struct
import sys
import zlib
from pathlib import Path

INK, PINK, YELLOW = (0x4A, 0x2A, 0x38), (0xFF, 0xB8, 0xCC), (0xFF, 0xE5, 0x8F)

FLAG = [(16, 7), (16, 2.5), (20.5, 4.1), (16, 5.8)]
BODY = [(4, 29), (4, 12), (8, 12), (8, 8), (10, 8), (10, 12), (14, 12), (14, 6), (18, 6), (18, 12), (22, 12),
        (22, 8), (24, 8), (24, 12), (28, 12), (28, 29)]
# door: left edge up, half circle (center 16,23 radius 3) over the top, right edge down
DOOR = [(13, 29), (13, 23)] + [(16 - 3 * math.cos(math.pi * i / 16), 23 - 3 * math.sin(math.pi * i / 16)) for i in range(1, 16)] + [(19, 23), (19, 29)]
# drawing order and style like the SVG: (points, fill, stroke width, closed outline)
SHAPES = [(FLAG, YELLOW, 1.6), (BODY, PINK, 2.0), (DOOR, YELLOW, 2.0)]


def inside(px, py, pts):
    hit = False
    j = len(pts) - 1
    for i, (xi, yi) in enumerate(pts):
        xj, yj = pts[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def dist_to_outline(px, py, pts):
    best = 1e9
    for i in range(len(pts)):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % len(pts)]
        dx, dy = bx - ax, by - ay
        t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


def render(size):
    """RGBA bytes. The 32x32 logo box fills the icon."""
    scale = size / 32
    ss = 4
    out = bytearray()
    for y in range(size):
        for x in range(size):
            r = g = b = a = 0
            for sy in range(ss):
                for sx in range(ss):
                    px = (x + (sx + .5) / ss) / scale
                    py = (y + (sy + .5) / ss) / scale
                    color = None
                    for pts, fill, sw in SHAPES:
                        if inside(px, py, pts):
                            color = fill
                        if dist_to_outline(px, py, pts) <= sw / 2:
                            color = INK
                    if color:
                        r, g, b, a = r + color[0], g + color[1], b + color[2], a + 1
            n = ss * ss
            if a:
                out += bytes((round(r / a), round(g / a), round(b / a), round(255 * a / n)))
            else:
                out += bytes(4)
    return bytes(out)


def png(size, rgba):
    rows = b"".join(b"\0" + rgba[y * size * 4:(y + 1) * size * 4] for y in range(size))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def main(dest: Path) -> None:
    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [png(s, render(s)) for s in sizes]
    head = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for s, data in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(head + entries + b"".join(images))
    print("wrote", dest, dest.stat().st_size, "bytes")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "assets" / "brain-castle.ico")
