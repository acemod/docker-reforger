FROM debian:trixie-slim

LABEL maintainer="ACE Team - https://github.com/acemod"
LABEL org.opencontainers.image.source=https://github.com/acemod/docker-reforger

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update \
    && \
    apt-get install -y --no-install-recommends --no-install-suggests \
        ca-certificates \
        lib32gcc-s1 \
        lib32stdc++6 \
        libterm-readline-perl-perl \
        libcurl4 \
        libssl3 \
        net-tools \
        python3 \
        wamerican \
        wget \
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

ENV STEAM_USER=""
ENV STEAM_PASSWORD=""
ENV STEAM_APPID="1874900"
ENV STEAM_BRANCH="public"
ENV STEAM_BRANCH_PASSWORD=""

ENV ARMA_CONFIG=docker_generated
ENV ARMA_PROFILE=/home/profile
ENV ARMA_BINARY="./ArmaReforgerServer"
ENV ARMA_PARAMS=""
ENV ARMA_MAX_FPS=120
ENV ARMA_WORKSHOP_DIR=/reforger/workshop

ENV SERVER_BIND_ADDRESS="0.0.0.0"
ENV SERVER_BIND_PORT=2001
ENV SERVER_PUBLIC_ADDRESS=""
ENV SERVER_PUBLIC_PORT=2001
ENV SERVER_A2S_ADDRESS="0.0.0.0"
ENV SERVER_A2S_PORT=17777

ENV RCON_ADDRESS="0.0.0.0"
ENV RCON_PORT=19999
ENV RCON_PASSWORD=""
ENV RCON_PERMISSION="admin"

ENV GAME_NAME="Arma Reforger Docker Server"
ENV GAME_PASSWORD=""
ENV GAME_PASSWORD_ADMIN=""
# GAME_ADMINS - comma-delimited list of identityIds and/or steamIds
ENV GAME_ADMINS=""
ENV GAME_SCENARIO_ID="{ECC61978EDCC2B5A}Missions/23_Campaign.conf"
ENV GAME_MAX_PLAYERS=32
ENV GAME_VISIBLE=true
ENV GAME_SUPPORTED_PLATFORMS=PLATFORM_PC,PLATFORM_XBL,PLATFORM_PSN
ENV GAME_PROPS_BATTLEYE=true
ENV GAME_PROPS_DISABLE_THIRD_PERSON=false
ENV GAME_PROPS_FAST_VALIDATION=true
ENV GAME_PROPS_SERVER_MAX_VIEW_DISTANCE=2500
ENV GAME_PROPS_SERVER_MIN_GRASS_DISTANCE=50
ENV GAME_PROPS_NETWORK_VIEW_DISTANCE=1000
ENV GAME_MODS_IDS_LIST=""
ENV GAME_MODS_JSON_FILE_PATH=""
ENV GAME_PROPS_VON_DISABLE_UI=false
ENV GAME_PROPS_VON_DISABLE_DIRECT_SPEECH_UI=false
ENV GAME_PROPS_VON_CAN_TRANSMIT_CROSS_FACTION=false

ENV SKIP_INSTALL=false

WORKDIR /reforger

VOLUME /home/profile
VOLUME /reforger
VOLUME /reforger/Configs
VOLUME /reforger/workshop
VOLUME /steamcmd

EXPOSE 2001/udp
EXPOSE 17777/udp

STOPSIGNAL SIGINT

COPY *.py /
COPY docker_default.json /

CMD ["python3","/launch.py"]
