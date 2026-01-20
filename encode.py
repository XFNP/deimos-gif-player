import sys, os
from PIL import Image, ImageSequence

WIDTH = 192
HEIGHT = 63
ROW_STRIDE = 32
PLANE_SIZE = ROW_STRIDE * HEIGHT

OUT_DIR = "frames"
os.makedirs(OUT_DIR, exist_ok=True)

if len(sys.argv) != 2:
    print("Usage: python gif2delta.py <gif>")
    sys.exit(1)

GIF_PATH = sys.argv[1]

# ----------------------------
# DITHER
# ----------------------------

def fs_dither_2bit(pixels, w, h):
    buf = [float(p) for p in pixels]
    out = [0] * (w * h)
    levels = [0, 85, 170, 255]

    for y in range(h):
        for x in range(w):
            i = y * w + x
            old = buf[i]
            q = min(range(4), key=lambda n: abs(old - levels[n]))
            new = levels[q]
            out[i] = q
            err = old - new

            if x + 1 < w:
                buf[i + 1] += err * 7 / 16
            if y + 1 < h:
                if x > 0:
                    buf[i + w - 1] += err * 3 / 16
                buf[i + w] += err * 5 / 16
                if x + 1 < w:
                    buf[i + w + 1] += err * 1 / 16
    return out

# ----------------------------
# DELTA ENCODE
# ----------------------------

def make_delta(prev, curr):
    out = bytearray()
    i = 0
    n = len(curr)

    while i < n:
        skip = 0
        while i < n and curr[i] == prev[i] and skip < 255:
            skip += 1
            i += 1
        out.append(skip)

        if i >= n:
            out.append(0)
            break

        start = i
        count = 0
        while i < n and curr[i] != prev[i] and count < 255:
            i += 1
            count += 1

        out.append(count)
        out.extend(curr[start:start+count])

    return out

# ----------------------------
# PROCESS GIF
# ----------------------------

gif = Image.open(GIF_PATH)
prev0 = bytearray(PLANE_SIZE)
prev4 = bytearray(PLANE_SIZE)
delays = []

for idx, frame in enumerate(ImageSequence.Iterator(gif)):
    delays.append(frame.info.get("duration", 100))

    img = frame.convert("L")
    img.thumbnail((WIDTH, HEIGHT), Image.BOX)

    canvas = Image.new("L", (WIDTH, HEIGHT), 255)
    ox = (WIDTH - img.width) // 2
    oy = (HEIGHT - img.height) // 2
    canvas.paste(img, (ox, oy))

    src = [255 - p for p in canvas.getdata()]
    levels = fs_dither_2bit(src, WIDTH, HEIGHT)

    plane0 = bytearray(PLANE_SIZE)
    plane4 = bytearray(PLANE_SIZE)

    for y in range(HEIGHT):
        row = y * ROW_STRIDE
        for x in range(WIDTH):
            g = levels[y * WIDTH + x]
            b = x >> 3
            bit = 7 - (x & 7)
            mask = 1 << bit
            i = row + b
            if g & 1:
                plane0[i] |= mask
            if g & 2:
                plane4[i] |= mask

    if idx == 0:
        with open(f"{OUT_DIR}/frame000.bin", "wb") as f:
            f.write(plane0)
            f.write(plane4)
    else:
        with open(f"{OUT_DIR}/frame{idx:03}.d0", "wb") as f:
            f.write(make_delta(prev0, plane0))
        with open(f"{OUT_DIR}/frame{idx:03}.d4", "wb") as f:
            f.write(make_delta(prev4, plane4))

    prev0[:] = plane0
    prev4[:] = plane4

with open(f"{OUT_DIR}/frames.txt", "w") as f:
    for d in delays:
        f.write(f"{d}\n")

print("Delta frames exported.")
