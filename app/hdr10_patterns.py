#!/usr/bin/env python3
"""Generate an actual PQ (ST 2084), BT.2020, 10-bit HDR10 test video.

No measurement is implied: the encoded PQ values are absolute *signal targets*;
monitor peak and black reproduction require observation/a measurement instrument.
Uses ffmpeg + libx265 only, does not change any display controls.
"""
from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import sys
from array import array
from pathlib import Path

# ST 2084 constants per SMPTE ST 2084: 0..10000 cd/m^2
M1 = 2610 / 16384
M2 = 2523 / 32
C1 = 3424 / 4096
C2 = 2413 / 128
C3 = 2392 / 128
STEPS = (100, 203, 400, 600, 1000, 1600, 2000)
NEAR_BLACK = (0.005, 0.01, 0.05, 0.1, 0.5, 1.0)


def pq_encode(nits: float) -> float:
    """PQ OETF: absolute luminance nits -> normalized 10k-nit signal."""
    if not 0 <= nits <= 10000:
        raise ValueError('ST2084 requires 0..10000 nits')
    t = (nits / 10000.0) ** M1
    return ((C1 + C2 * t) / (1 + C3 * t)) ** M2


def limited10(nits: float) -> int:
    """Limited-range 10-bit BT.2020 luma of neutral gray."""
    return round(64 + 876 * pq_encode(nits))


def fill_rect(buffer: array, width: int, height: int,
              x: int, y: int, w: int, h: int, code: int) -> None:
    x0, x1 = max(0, x), min(width, x + w)
    y0, y1 = max(0, y), min(height, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    run = array('H', [code]) * (x1 - x0)
    for line in range(y0, y1):
        start = line * width + x0
        buffer[start:start + len(run)] = run


def make_frame(width: int, height: int, patch_nits: float) -> bytes:
    """One small PQ-white square plus a black-level comparison bar.

    Frame is 10-bit planar Y'CbCr 4:2:0 BT.2020 nonconstant luminance;
    neutral colors have Cb/Cr exactly 512.
    """
    y = array('H', [limited10(0.0)]) * (width * height)
    patch_w = (width // 4) & ~1
    patch_h = (height // 4) & ~1
    fill_rect(y, width, height, (width-patch_w)//2, (height-patch_h)//2,
              patch_w, patch_h, limited10(patch_nits))
    # Six tiny bottom swatches reveal near-black crushing on HDR video output.
    width_swatch = max(4, (width - 40) // (len(NEAR_BLACK) * 2))
    for i, black_level in enumerate(NEAR_BLACK):
        x = 20 + i * 2 * width_swatch
        fill_rect(y, width, height, x, height - max(28, height//10),
                  width_swatch, max(16, height//20), limited10(black_level))
    # Unchanged center reference at 203 nits in the upper left, allowing a
    # side-by-side comparison while the center patch steps through targets.
    ref_w, ref_h = max(12,width//12), max(12,height//12)
    fill_rect(y,width,height,18,18,ref_w,ref_h,limited10(203))
    # Python's array native endian on x86_64 is little endian; swap on big endian.
    if sys.byteorder != 'little':
        y.byteswap()
    uv_plane = array('H', [512]) * (width * height // 4)
    if sys.byteorder != 'little':
        uv_plane.byteswap()
    return y.tobytes() + uv_plane.tobytes() + uv_plane.tobytes()


def build(output: Path, width: int, height: int, fps: int, seconds: float) -> None:
    if width < 128 or height < 128 or width % 2 or height % 2:
        raise ValueError('Dimensions even and at least 128x128 required')
    if fps < 1 or fps > 120 or seconds <= 0 or seconds > 30:
        raise ValueError('Invalid frame rate or duration')
    if not shutil.which('ffmpeg'):
        raise RuntimeError('ffmpeg missing; on Arch: sudo pacman -S ffmpeg')
    frames = max(1, round(seconds * fps))
    output.parent.mkdir(parents=True, exist_ok=True)
    # BT.2020 mastering primaries, D65, 2000-nit master, HDR10 static metadata.
    x265 = ('pools=2:frame-threads=2:hdr10=1:repeat-headers=1:'
            'colorprim=9:transfer=16:colormatrix=9:range=limited:'
            'master-display=G(8500,39850)B(6550,2300)R(35400,14600)'
            'WP(15635,16450)L(20000000,1):max-cll=2000,203')
    cmd = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
           '-f', 'rawvideo', '-pixel_format', 'yuv420p10le',
           '-video_size', f'{width}x{height}', '-framerate', str(fps), '-i', 'pipe:0',
           '-an', '-c:v', 'libx265', '-preset', 'ultrafast', '-crf', '12',
           '-pix_fmt', 'yuv420p10le', '-color_primaries', 'bt2020',
           '-color_trc', 'smpte2084', '-colorspace', 'bt2020nc',
           '-x265-params', x265, '-movflags', '+faststart', str(output)]
    try:
        with subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            assert proc.stdin is not None and proc.stderr is not None
            try:
                for nits in STEPS:
                    frame = make_frame(width, height, nits)
                    for _ in range(frames):
                        proc.stdin.write(frame)
            except BrokenPipeError:
                pass
            finally:
                proc.stdin.close()
            error = proc.stderr.read().decode('utf-8', 'replace')
            status = proc.wait()
            if status:
                raise RuntimeError(f'ffmpeg failed ({status}): {error[-2200:]}')
    except OSError as exc:
        raise RuntimeError(f'Cannot start ffmpeg: {exc}') from exc
    print('HDR10 test created:', output)
    print('Reference square: 203 nits PQ | main center patch each stage:')
    for index, nits in enumerate(STEPS):
        print(f'  {index * seconds:4.1f}s–{(index+1)*seconds:4.1f}s: {nits:4d} nits PQ')
    print('Black swatches near bottom:', ', '.join(map(str,NEAR_BLACK)), 'nits')
    print('Video is encoded with HDR10 metadata. Actual brightness depends on '
          'player, compositor, display and tone mapping.')


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path.home()/'.cache/sdr-color-studio/hdr10-test.mp4')
    p.add_argument('--width', type=int, default=640)
    p.add_argument('--height', type=int, default=360)
    p.add_argument('--fps', type=int, default=24)
    p.add_argument('--seconds-per-step', type=float, default=1.5)
    a=p.parse_args()
    try:
        build(a.output,a.width,a.height,a.fps,a.seconds_per_step)
    except (ValueError,RuntimeError) as error:
        p.error(str(error))


if __name__=='__main__':
    main()
