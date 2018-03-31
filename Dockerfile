#
#  Dockerfile
#  dSVP
#
#  Created by p2k on 22.03.18.
#  Copyright (c) 2018 Patrick "p2k" Schneider
#
#  Licensed under the EUPL
#

FROM debian:stretch

# Packages
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y --no-install-recommends apt-transport-https gnupg unzip curl ca-certificates ffmpeg python3 python3-yaml libpython3.5 libffms2-4 \
    && curl -sSL "https://deb.nodesource.com/gpgkey/nodesource.gpg.key" | apt-key add - \
    && echo "deb https://deb.nodesource.com/node_8.x stretch main" > /etc/apt/sources.list.d/nodesource.list \
    && echo "deb-src https://deb.nodesource.com/node_8.x stretch main" >> /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Setup VapourSynth
RUN export DEBIAN_FRONTEND=noninteractive \
    && set -x \
    && apt-get update \
    && DEV_TOOLS="python3-pip python3-setuptools python3-dev git build-essential nasm cython3 autoconf automake libtool libavcodec-dev libavformat-dev libavutil-dev libass-dev libtesseract-dev" \
    && apt-get install -y --no-install-recommends $DEV_TOOLS \
    && cd /tmp \
    && curl -o nasm_2.13.02-0.1_amd64.deb -SsL http://ftp.de.debian.org/debian/pool/main/n/nasm/nasm_2.13.02-0.1_amd64.deb \
    && dpkg -i nasm_2.13.02-0.1_amd64.deb \
    && rm nasm_2.13.02-0.1_amd64.deb \
    && git clone https://github.com/sekrit-twc/zimg.git --branch v2.7 --single-branch \
    && cd zimg && ./autogen.sh && ./configure --prefix=/usr --libdir=/usr/lib/x86_64-linux-gnu && make install && cd .. \
    && rm -r zimg \
    && git clone https://github.com/vapoursynth/vapoursynth.git \
    && cd vapoursynth && ./autogen.sh && ./configure --prefix=/usr --libdir=/usr/lib/x86_64-linux-gnu && make install && cd .. \
    && rm -r vapoursynth \
    && pip3 install VapourSynth \
    && apt-get purge -y --auto-remove $DEV_TOOLS \
    && rm -rf /var/lib/apt/lists/*

ENV SVPFLOW_VERSION 4.2.0.142

WORKDIR /app

RUN set -x \
    && curl -o svpflow-${SVPFLOW_VERSION}.zip -sSL "http://www.svp-team.com/files/gpl/svpflow-${SVPFLOW_VERSION}.zip" \
    && unzip svpflow-${SVPFLOW_VERSION}.zip \
    && mkdir -p /root/.config/vapoursynth && mkdir vslib \
    && echo -e "UserPluginDir=/app/vslib\n" > /root/.config/vapoursynth/vapoursynth.conf \
    && mv svpflow-${SVPFLOW_VERSION}/lib-linux/libsvpflow1_vs64.so vslib/libsvpflow1.so \
    && mv svpflow-${SVPFLOW_VERSION}/lib-linux/libsvpflow2_vs64.so vslib/libsvpflow2.so \
    && ln -s /usr/lib/libffms2.so vslib/libffms2.so \
    && rm -r svpflow-${SVPFLOW_VERSION}.zip

#COPY package.json ./

#RUN npm install

#COPY . .

COPY interpolate.py proc_follow.py ffmpeg_helper.py ./

#CMD ["npm", "start"]

#vspipe --arg "source=$SOURCE" --y4m interpolate.py - |ffmpeg -i pipe: -i logo.png -filter_complex "overlay=20:H-h-20:format=rgb,format=yuv420p" -c:v libx264 -b:v 4992k -maxrate 9984k -bufsize 7488k -preset veryfast -tune animation -profile:v high -level 4.2 -x264-params keyint=720:ref=4 -f m4v $DEST.m4v
