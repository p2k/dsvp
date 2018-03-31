#
#  vspipe_helper.py
#  dSVP
#
#  Created by p2k on 31.03.18.
#  Copyright (c) 2018 Patrick "p2k" Schneider
#
#  Licensed under the EUPL
#

import subprocess

__all__ = ['vspipe', 'build_svp_config']

def build_svp_config(config):
    if isinstance(config, dict):
        return '{' + ','.join('%s:%s' % (k, build_svp_config(v)) for k, v in config.items()) + '}'
    elif isinstance(config, list):
        return '[' + ','.join(build_svp_config(v) for v in config) + ']'
    elif isinstance(config, str):
        return config
    elif config == True:
        return 'true'
    elif config == False:
        return 'false'
    else:
        return str(config)

def vspipe(config, **kwargs):
    cmd = ['vspipe', '--arg', 'source=' + config.input_file]

    cmd.extend(['--arg', 'analyse=' + build_svp_config(config.profile['analyse'])])
    cmd.extend(['--arg', 'smooth=' + build_svp_config(config.profile['smooth'])])
    if config.gpu:
        cmd.extend(['--arg', 'gpu=1'])
    cmd.extend(['--y4m', 'interpolate.py', '-'])

    return subprocess.Popen(cmd, **kwargs)
