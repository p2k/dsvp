#
#  ffmpeg_helper.py
#  dSVP
#
#  Created by p2k on 25.03.18.
#  Copyright (c) 2018 Patrick "p2k" Schneider
#
#  Licensed under the EUPL
#

import os, re, subprocess

__all__ = ['ffmpeg', 'ffhwaccels', 'ffprobe', 'ffversion', 'ffvcodecs', 'parse_progress']

ASCII_LINESEP = os.linesep.encode('ascii')

RE_FILTER_ESCAPE1 = re.compile(r'[:\\\']')
RE_FILTER_ESCAPE2 = re.compile(r'[\[\],;\\\']')
FN_FILTER_ESCAPE = lambda m: '\\' + m.group()
def escape_filter_param(param):
    return RE_FILTER_ESCAPE2.sub(FN_FILTER_ESCAPE, RE_FILTER_ESCAPE1.sub(FN_FILTER_ESCAPE, param))

def build_filter(overlay, subtitles):
    chain = []
    if overlay is not None:
        chain.append('[2:v]overlay=20:H-h-20:format=rgb')
    if subtitles is not None:
        chain.append('subtitles=' + escape_filter_param(subtitles))
    if len(chain) > 0:
        chain[0] = '[0:v]' + chain[0]
        chain.append('format=yuv420p[out]')
        return ['-filter_complex', ','.join(chain)]
    else:
        return []

def conv_param_value(v):
    if isinstance(v, str):
        return v
    elif v == True:
        return 'true'
    elif v == False:
        return 'false'
    else:
        return str(v)

def build_x264_params(params):
    return ['-x264-params', ':'.join('%s=%s' % (k, conv_param_value(v)) for k, v in params.items())]

def build_nvenc_params(params):
    return [x for y in (('-%s' % k, conv_param_value(v)) for k, v in params.items()) for x in y]

def build_bitrates(r):
    return ['-b:v', '%dk' % r, '-maxrate', '%dk' % (r*2), '-bufsize', '%dk' % (r*1.5)]

def ffmpeg(input_file, output_file, config, logo=None, subtitles=None, nvenc=False, **kwargs):
    cmd = ['ffmpeg', '-y', '-v', 'info', '-thread_queue_size', '16', '-i', 'pipe:', '-i', input_file]

    if logo is not None:
        cmd.append('-i')
        cmd.append(logo)

    f = build_filter(logo, subtitles)
    if len(f) == 0:
        cmd.extend(['-map', '0:v'])
    else:
        cmd.extend(f)
        cmd.extend(['-map', '[out]'])

    cmd.extend(['-map', '1:a', '-pix_fmt', 'yuv420p', '-c:v', 'h264_nvenc' if nvenc else 'libx264'])

    cmd.extend(build_bitrates(config['v_bitrate']))
    cmd.extend(['-profile:v', 'high', '-level', '4.2'])

    if nvenc:
        cmd.extend(build_nvenc_params(config['nvenc']))
    else:
        cmd.extend(build_x264_params(config['x264']))

    cmd.extend(['-c:a', 'aac', '-b:a', '%dk' % config['a_bitrate']])
    cmd.append(output_file)

    return subprocess.Popen(cmd, **kwargs)

RE_DURATION_VALUE = re.compile(b'^(\d+\.\d+)|(\d+):(\d\d):(\d\d)(.\d+)$')
def parse_duration(duration):
    m = RE_DURATION_VALUE.match(duration)
    if m is None:
        return None
    if m.group(1) is not None:
        return float(m.group(1))
    else:
        return int(m.group(2), 10) * 3600 + int(m.group(3), 10) * 60 + int(m.group(4), 10) + float(m.group(5))

def ffhwaccels():
    accels = []
    for info in subprocess.check_output(['ffmpeg', '-v', 'error', '-hwaccels']).split(ASCII_LINESEP):
        info = info.strip()
        if not len(info) == 0 and not info.startswith(b'Hardware '):
            accels.append(info)
    return accels

RE_VCODEC = re.compile(b'^\s\SEV\S\S\S\s+(\S+)\s+([^(]|\((?!decoders|encoders))*(\(decoders: ([^)]*)\)\s*)?(\(encoders: ([^)]*)\))?$')
def ffvcodecs():
    vcodecs = {}
    for info in subprocess.check_output(['ffmpeg', '-v', 'error', '-codecs']).split(ASCII_LINESEP):
        m = RE_VCODEC.match(info)
        if m is not None:
            vcodecs[m.group(1).decode('ascii')] = (
                [dec.decode('ascii') for dec in m.group(4).strip().split(b' ')] if m.group(4) is not None else [],
                [enc.decode('ascii') for enc in m.group(6).strip().split(b' ')] if m.group(6) is not None else []
            )
    return vcodecs

RE_DURATION = re.compile(b'^(TAG:DURATION|duration)=(\d+\.\d+|\d+:\d\d:\d\d.\d+)$')
RE_FRAMERATE = re.compile(b'^r_frame_rate=(\d+)/(\d+)$')
RE_N_FRAMES = re.compile(b'^(TAG:NUMBER_OF_FRAMES|nb_frames)=(\d+)$')
def ffprobe(input_file):
    n_frames = None
    framerate = None
    duration = None
    for info in subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_streams', input_file]).split(ASCII_LINESEP):
        m = RE_N_FRAMES.match(info)
        if m is not None:
            n_frames = int(m.group(2), 10)
            continue
        m = RE_FRAMERATE.match(info)
        if m is not None:
            framerate = [int(m.group(1), 10), int(m.group(2), 10)]
            continue
        m = RE_DURATION.match(info)
        if m is not None:
            duration = parse_duration(m.group(2))
    if n_frames is None and framerate is not None:
        n_frames = duration * framerate[0] / framerate[1]
    return {'nf': n_frames, 'r': framerate, 'd': duration}

RE_VERSION = re.compile(b'^ffmpeg version (\S+)')
def ffversion():
    version = None
    for info in subprocess.check_output(['ffmpeg', '-version']).split(ASCII_LINESEP):
        m = RE_VERSION.match(info)
        if m is not None:
            version = m.group(1).decode('ascii')
            break
    return version

RE_PROGRESS = re.compile(b'^frame=\s*(\S+)\s*fps=\s*(\S+)\s*q=\s*(\S+)\s*size=\s*(\S+)\s*time=\s*(\S+)\s*bitrate=\s*(\S+)\s*speed=\s*(\S+)\s*$')
def parse_progress(data):
    m = RE_PROGRESS.match(data)
    if m is not None:
        return {
            'f': int(m.group(1), 10),
            'fps': float(m.group(2)),
            'q': float(m.group(3)),
            'sz': m.group(4).decode('ascii'),
            't': parse_duration(m.group(5)),
            'br': m.group(6).decode('ascii'),
            'spd': m.group(7).decode('ascii')
        }
    else:
        return None
