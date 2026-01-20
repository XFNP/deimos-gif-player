import picoease
import time
import os

# ============================================================
# LCD CONSTANTS
# ============================================================

BUFFER_BASE = 0xF800
SELECT_ADDR = 0xF037

ROW_STRIDE  = 32
VISIBLE_B   = 24
HEIGHT      = 63
PLANE_SIZE  = ROW_STRIDE * HEIGHT

FRAME_DIR = "/remote/frames"

# ============================================================
# FRAMEBUFFERS
# ============================================================

buf0 = bytearray(PLANE_SIZE)
buf4 = bytearray(PLANE_SIZE)

# ============================================================
# LOW-LEVEL LCD WRITE (FAST PATH)
# ============================================================

def select_plane(plane):
    picoease.run(0x0000, plane)
    picoease.run(0x9011, SELECT_ADDR)

def write_byte(addr, value):
    picoease.run(0x0000, value)
    picoease.run(0x9011, addr)

# ============================================================
# CLEAR LCD (ALL PLANES)
# ============================================================

def clear_lcd():
    for plane in (0, 4):
        select_plane(plane)
        for addr in range(0xF800, 0x10000):
            write_byte(addr, 0)

# ============================================================
# LOAD FULL FRAME
# ============================================================

def load_keyframe(path):
    with open(path, "rb") as f:
        data = f.read()

    buf0[:] = data[:PLANE_SIZE]
    buf4[:] = data[PLANE_SIZE:PLANE_SIZE * 2]

    for plane, buf in ((0, buf0), (4, buf4)):
        select_plane(plane)
        for y in range(HEIGHT):
            base = BUFFER_BASE + y * ROW_STRIDE
            row  = y * ROW_STRIDE
            for x in range(VISIBLE_B):
                write_byte(base + x, buf[row + x])

# ============================================================
# APPLY DELTA + DRAW (INTERLACED)
# ============================================================

def apply_delta(buf, delta, plane):
    select_plane(plane)

    i = 0
    p = 0
    n = len(delta)

    while p < n and i < PLANE_SIZE:
        skip = delta[p]
        p += 1
        i += skip

        if p >= n or i >= PLANE_SIZE:
            break

        count = delta[p]
        p += 1

        for _ in range(count):
            v = delta[p]
            p += 1
            buf[i] = v

            y = i // ROW_STRIDE
            x = i & 31

            if x < VISIBLE_B:
                write_byte(BUFFER_BASE + y * ROW_STRIDE + x, v)

            i += 1

def apply_delta_rows(buf, delta, plane, parity):
    select_plane(plane)

    i = 0
    p = 0
    n = len(delta)

    while p < n and i < PLANE_SIZE:
        skip = delta[p]
        p += 1
        i += skip

        if p >= n or i >= PLANE_SIZE:
            break

        count = delta[p]
        p += 1

        for _ in range(count):
            v = delta[p]
            p += 1
            buf[i] = v

            y = i // ROW_STRIDE
            x = i & 31

            if (y & 1) == parity and x < VISIBLE_B:
                write_byte(BUFFER_BASE + y * ROW_STRIDE + x, v)

            i += 1

# ============================================================
# PLAYER
# ============================================================

def play():
    picoease.connect()
    clear_lcd()

    # Load delays
    with open(f"{FRAME_DIR}/frames.txt") as f:
        delays = [int(x.strip()) for x in f]

    # Keyframe
    load_keyframe(f"{FRAME_DIR}/frame000.bin")
    time.sleep(delays[0] / 1000)

    frame = 1

    while True:
        for frame in range(1, len(delays)):
            parity = frame & 1

            with open(f"{FRAME_DIR}/frame{frame:03}.d0", "rb") as f:
                d0 = f.read()
            with open(f"{FRAME_DIR}/frame{frame:03}.d4", "rb") as f:
                d4 = f.read()

            # PASS 1: even rows
            apply_delta_rows(buf0, d0, 0, parity=0)
            apply_delta_rows(buf4, d4, 4, parity=0)

            # PASS 2: odd rows
            apply_delta_rows(buf0, d0, 0, parity=1)
            apply_delta_rows(buf4, d4, 4, parity=1)


            time.sleep(delays[frame] / 1000)

# ============================================================
# ENTRY
# ============================================================

play()
