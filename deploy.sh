#!/bin/bash
set -e
# Deploy Tidemark to a Raspberry Pi: sync, build, install/refresh the systemd
# timer, and leave the panel on a clean full refresh.
#
# Configure your Pi (env vars, or a local deploy.env that this sources):
#   TIDEMARK_PI          user@host of the Pi   (e.g. pi@raspberrypi.local)
#   TIDEMARK_REMOTE_DIR  install dir on the Pi (default: tidemark, under $HOME)
#
# Prerequisite on the Pi: the bcm2835 library must be installed (the IT8951
# driver links against it). See the README.

[ -f deploy.env ] && . ./deploy.env
PI="${TIDEMARK_PI:?set TIDEMARK_PI=user@host, e.g. pi@raspberrypi.local}"
REMOTE_DIR="${TIDEMARK_REMOTE_DIR:-tidemark}"

# The IT8951 panel corrupts if two processes hit the SPI bus at once, so never
# run ./tidemark manually while the timer is live. Sequence below: stop the
# timer and any in-flight run -> sync -> install deps -> build -> one clean
# full-clear baseline -> (re)install the units -> start the timer.

# 1. Stop the timer AND any in-flight service run; confirm no tidemark process
#    is left holding the SPI bus before we run the manual baseline below.
ssh "$PI" 'sudo systemctl stop tidemark.timer tidemark.service 2>/dev/null
    sudo pkill -9 -x tidemark 2>/dev/null
    sleep 1
    if pgrep -x tidemark >/dev/null; then
        echo "A tidemark process is still running — aborting to avoid SPI collision"
        exit 1
    fi' || { echo "Failed to stop timer/service cleanly"; exit 1; }

# 2. Sync the working tree (skip build artifacts and the local venv). Note we DO
#    copy location.json so the Pi shows the location you set up locally.
#    __pycache__ is excluded: the service runs as root and its root-owned .pyc
#    dirs would block rsync; Python regenerates them anyway.
rsync -av --exclude '.git' --exclude '*.o' --exclude 'tidemark' \
    --exclude 'tidemark_sim' --exclude 'venv' --exclude '__pycache__' \
    ./ "$PI":"$REMOTE_DIR"/ \
    || { echo "Sync failed"; exit 1; }

# 3. On the Pi: venv (Pillow only), install systemd units with the real install
#    path substituted in, build, run a guarded clean baseline, start the timer.
ssh "$PI" "set -e
    cd \"$REMOTE_DIR\"
    HOME_ABS=\$(pwd)
    sudo apt-get update -qq && sudo apt-get install -y python3-venv >/dev/null
    [ -d venv ] || python3 -m venv venv
    ./venv/bin/pip install -q --upgrade pip pillow
    sed \"s#__TIDEMARK_HOME__#\$HOME_ABS#g\" deploy/tidemark.service \
        | sudo tee /etc/systemd/system/tidemark.service >/dev/null
    sudo cp deploy/tidemark.timer /etc/systemd/system/tidemark.timer
    sudo systemctl daemon-reload
    cd build && make clean && make
    # One clean full-clear baseline. timeout guards against a stuck SPI bus.
    # Then clear the partial-refresh token so the first timer fire is a full
    # repaint (a partial right after deploy once left the panel showing a sliver).
    sudo env TIDEMARK_HOME=\$HOME_ABS TIDEMARK_FULL_CLEAR=1 timeout 150 ./tidemark
    sudo rm -f /run/tidemark.state
    sudo systemctl enable --now tidemark.timer
    echo \"timer=\$(systemctl is-active tidemark.timer)\"" \
    || { echo "Remote install/build/baseline failed"; exit 1; }

echo "Deployed to $PI:$REMOTE_DIR. The timer refreshes the panel every 5 minutes."
