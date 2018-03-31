
# dSVP

Distributed SmoothVideo Processor

## About

dSVP is a combined VapourSynth and FFmpeg frontend for high quality 60fps
interpolation of videos. It consists of a job distribution server and worker
implementation. The script that prepares and runs the actual processing can also
be used standalone.

## Installation

The processing script requires [Python 3.5 or later](https://www.python.org/downloads/)
and [PyYAML](https://pypi.python.org/pypi/PyYAML) for your respective platform.
It also requires [VapourSynth](http://www.vapoursynth.com/doc/) installed and
pre-configured to [autoload](http://www.vapoursynth.com/doc/autoloading.html)
the three plugins `ffms2`, `svp1` and `svp2`; the latter can be acquired from
the [SmoothVideo Project](https://www.svp-team.com/wiki/Manual:SVPflow).

Instead of the above, you may use the supplied Dockerfile to work with Docker,
although some performance loss might be observed on operating systems other than
Linux.

For the job server and worker, [Node.js 8 or later](https://nodejs.org/) is
required.

## Links

Inspiration for the h.264 settings have come from these sites:

* http://www.lighterra.com/papers/videoencodingh264/
* https://trac.ffmpeg.org/wiki/Encode/H.264
* https://encodingwissen.de/codecs/x264/referenz/

## License

Licensed under the EUPL version 1.2
