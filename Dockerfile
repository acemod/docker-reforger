FROM debian:bullseye-slim

LABEL maintainer="ACE Team - https://github.com/acemod"
LABEL org.opencontainers.image.source=https://github.com/acemod/docker-reforger

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update \
    && \
    apt-get install -y --no-install-recommends --no-install-suggests \
        python3 \
        lib32stdc++6 \
        lib32gcc-s1 \
        wget \
        ca-certificates \
        libcurl4 \
        net-tools \
        libssl1.1 \
        wamerican \
    && \
    apt-get remove --purge -y \
    && \
    apt-get clean autoclean \
    && \
    apt-get autoremove -y \
    && \
    rm -rf /var/lib/apt/lists/* \
    && \
    mkdir -p /steamcmd \
    && \
    wget -qO- 'https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz' | tar zxf - -C /steamcmd

ENV TRACY_NO_INVARIANT_CHECK=1

ENV STEAM_USER=""
ENV STEAM_PASSWORD=""
ENV STEAM_BRANCH="public"
ENV STEAM_BRANCH_PASSWORD=""

ENV ARMA_CONFIG=docker_generated
ENV ARMA_PROFILE=/home/profile
ENV ARMA_BINARY="./ArmaReforgerServer"
ENV ARMA_PARAMS=""
ENV ARMA_MAX_FPS=120

ENV SERVER_BIND_ADDRESS="0.0.0.0"
ENV SERVER_BIND_PORT=2001
ENV SERVER_PUBLIC_ADDRESS=""
ENV SERVER_PUBLIC_PORT=2001
ENV SERVER_A2S_ADDRESS=""
ENV SERVER_A2S_PORT=""

ENV GAME_NAME="Arma Reforger Docker Server"
ENV GAME_PASSWORD=""
ENV GAME_PASSWORD_ADMIN=""
ENV GAME_SCENARIO_ID="{ECC61978EDCC2B5A}Missions/23_Campaign.conf"
ENV GAME_MAX_PLAYERS=32
ENV GAME_VISIBLE=true
ENV GAME_SUPPORTED_PLATFORMS=PLATFORM_PC,PLATFORM_XBL
ENV GAME_PROPS_BATTLEYE=true
ENV GAME_PROPS_DISABLE_THIRD_PERSON=false
ENV GAME_PROPS_FAST_VALIDATION=true
ENV GAME_PROPS_SERVER_MAX_VIEW_DISTANCE=2500
ENV GAME_PROPS_SERVER_MIN_GRASS_DISTANCE=50
ENV GAME_PROPS_NETWORK_VIEW_DISTANCE=1000

ENV SKIP_INSTALL=false

WORKDIR /reforger

VOLUME /steamcmd
VOLUME /home/profile
VOLUME /reforger/Configs

EXPOSE 2001/udp
EXPOSE 17777/udp

STOPSIGNAL SIGINT

COPY *.py /
COPY docker_default.json /

CMD ["python3","/launch.py"]
