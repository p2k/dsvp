#!/usr/bin/env python3
#
#  interpolate.py
#  dSVP
#
#  Created by p2k on 23.03.18.
#  Copyright (c) 2018 Patrick "p2k" Schneider
#
#  Licensed under the EUPL
#

import sys, json

def printj(v):
    print(json.dumps(v, separators=(',',':')))

def merge(source, dest):
    for key, value in source.items():
        dest[key] = merge(value, dest.get(key, {})) if isinstance(value, dict) else value
    return dest

def resolve_profile(profiles, profile_name, override=None):
    result = merge(profiles['default'], {})
    if profile_name != 'default':
        merge(profiles[profile_name], result)
    if override is not None:
        merge(override, result)
    return result

def load_profiles():
    import yaml
    with open('profiles.yaml', 'rb') as f:
        return yaml.safe_load(f)

def load_vapoursynth():
    import vapoursynth as vs

    core = vs.core
    core.num_threads = 0

    assert hasattr(vs.core, 'ffms2')
    assert hasattr(vs.core, 'svp1')
    assert hasattr(vs.core, 'svp2')

    return vs, core

def main(config):
    import os, re

    if '' not in sys.path: # Hack for portable python
        sys.path.insert(0, '')

    from subprocess import PIPE
    from lib import ProcessFollower, vspipe, ffprobe, ffvcodecs, ffmpeg, parse_progress

    try:
        info = ffprobe(config.input_file)
    except:
        printj({'e': 'invalid_file'})
        sys.exit(1)

    info['nft'] = int(info['d'] * 60 + 0.5)

    h264_encoders = ffvcodecs()['h264'][1]
    if config.gpu and 'h264_nvenc' in h264_encoders:
        nvenc = True
    elif 'libx264' in h264_encoders:
        nvenc = False
    else:
        printj({'e': 'no_encoder'})
        sys.exit(1)

    NUL = open(os.devnull, 'w')
    p1 = vspipe(config, stdout=PIPE, stderr=NUL)
    p2 = ffmpeg(config.input_file, config.output_file, config.profile, config.logo, config.subtitles, nvenc, stdin=p1.stdout, stdout=PIPE, stderr=PIPE)
    p1.stdout.close()

    progress = None

    last_lines = []
    try:
        last = None
        for stderr, data in ProcessFollower(p2):
            if last is not None and data == last:
                continue
            last = data
            last_lines.append(data)
            if len(last_lines) == 6:
                del last_lines[0]

            progress = parse_progress(data)
            if progress is not None:
                info.update(progress)
                printj(info)
    except:
        p2.terminate()
        p2.wait()
        raise

    if p2.returncode != 0:
        printj({'e': 'fail', 'c': p2.returncode, 'm': [l.decode('utf-8') for l in last_lines]})
    return p2.returncode

def cpuinfo():
    if sys.platform.startswith('linux'):
        import re
        return re.search(r'^model name\s*:\s*(.+)$', open('/proc/cpuinfo', 'rb').read(), re.M).group(1).decode('utf-8')
    elif sys.platform == 'darwin' or sys.platform.startswith('freebsd'):
        import subprocess
        return subprocess.check_output(['/usr/sbin/sysctl', '-n', 'machdep.cpu.brand_string']).decode('utf-8').strip()
    else:
        import platform
        return platform.processor()

if __name__ == '__vapoursynth__':
    g = globals()

    gpu = g.get('gpu') == '1'

    analyse_config = g.get('analyse')
    smooth_config = g.get('smooth')
    if analyse_config is None or smooth_config is None:
        from lib import build_svp_config
        profile = resolve_profile(load_profiles(), g.get('profile', 'default'))
        if analyse_config is None:
            analyse_config = build_svp_config(profile['analyse'])
        if smooth_config is None:
            smooth_config = build_svp_config(profile['smooth'])

    vs, core = load_vapoursynth()

    clip = core.ffms2.Source(source=g['source'])
    clip = clip.resize.Bicubic(format=vs.YUV420P8)

    svp_super = core.svp1.Super(clip, '{gpu:1}' if gpu else '{gpu:0}')
    svp_vectors = core.svp1.Analyse(svp_super['clip'], svp_super['data'], clip, analyse_config)
    svp_smooth = core.svp2.SmoothFps(clip, svp_super['clip'], svp_super['data'], svp_vectors['clip'], svp_vectors['data'], smooth_config)
    svp_smooth = core.std.AssumeFPS(svp_smooth, fpsnum=svp_smooth.fps_num, fpsden=svp_smooth.fps_den)

    svp_smooth.set_output()

elif __name__ == '__main__':
    import argparse, os

    try:
        profiles = load_profiles()
    except:
        printj({'e': 'profiles'})
        sys.exit(1)

    if '--version' in sys.argv:
        import re, platform
        from lib import ffversion
        try:
            vs, core = load_vapoursynth()
            v = {
                'p': sys.platform,
                'ff': ffversion(),
                'vs': re.search(r'^Core (.+)$', core.version(), re.M).group(1),
                'c': cpuinfo(),
                't': os.cpu_count()
            }
        except:
            v = {'e': 'invalid_config'}
        printj(v)
        sys.exit()
    elif '--list-profiles' in sys.argv: 
        printj({'p': list(profiles.keys())})
        sys.exit()

    class StoreExistingPath(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            if not os.path.exists(values):
                raise ValueError('File not found: %s' % (values))
            setattr(namespace, self.dest, values)

    class StoreJSON(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, json.loads(values))

    parser = argparse.ArgumentParser(description='video interpolation utility for smooth FPS')
    parser.add_argument('input_file', action=StoreExistingPath, help='path to the input file to be processed')
    parser.add_argument('output_file', help='path to the output file; the extension determines the container format')

    parser.add_argument('-s', '--subtitles', action=StoreExistingPath, help='read and render subtitles from the given file')
    parser.add_argument('-S', '--inline-subtitles', action='store_true', default=False, help='read and render subtitles from the input file (overrides -s)')

    parser.add_argument('-l', '--logo', action=StoreExistingPath, help='overlay image to be rendered on the bottom left')

    parser.add_argument('-G', '--gpu', action='store_true', default=False, help='use GPU acceleration')

    parser.add_argument('-p', '--profile', default='default', help='use specific encoding profile')
    parser.add_argument('-o', '--override', action=StoreJSON, help='override encoding profile (JSON format)')

    parser.add_argument('--version', action='store_true', default=False, help='output version and platform information and exit')
    parser.add_argument('--list-profiles', action='store_true', default=False, help='list built-in profiles and exit')

    args = parser.parse_args()
    if args.inline_subtitles:
        args.subtitles = args.input_file

    args.profile = resolve_profile(profiles, args.profile, args.override)

    sys.exit(main(args))
