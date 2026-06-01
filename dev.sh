#!/bin/bash
set -e  # Exit on error

PI=reed@10.10.10.76

# Deploy safely. The IT8951 panel corrupts if two processes hit the SPI bus at
# once, so we must never run ./tidemark manually while tidemark.timer is live.
# Sequence: stop the timer -> sync -> build -> one clean full-clear baseline
# (INIT clear + full GC16, resets ghosting) -> restart the timer.

# 1. Stop the timer AND any in-flight service run, then make sure no tidemark
#    process is left holding the SPI bus. Stopping only the timer is not enough:
#    a service fire already running keeps going, and the manual baseline below
#    would collide with it and deadlock the bus.
ssh "$PI" 'sudo systemctl stop tidemark.timer tidemark.service 2>/dev/null
    sudo pkill -9 -x tidemark 2>/dev/null
    sleep 1
    if pgrep -x tidemark >/dev/null; then
        echo "A tidemark process is still running — aborting to avoid SPI collision"
        exit 1
    fi' || { echo "Failed to stop timer/service cleanly"; exit 1; }

# 2. Sync files to the Pi.
# Exclude __pycache__: the service runs as root, so its .pyc dirs are root-owned
# and rsync can't write into them — and Python regenerates .pyc on demand anyway.
rsync -av --exclude '.git' --exclude '*.o' --exclude 'tidemark' \
    --exclude 'tidemark_sim' --exclude 'venv' --exclude '__pycache__' \
    ./ "$PI":~/tidemark/ \
    || { echo "Sync failed"; exit 1; }

# 3. Build, run a single clean baseline, then restart the timer.
#    sudo drops $PWD (used to locate the project root), so pass it explicitly.
#    TIDEMARK_FULL_CLEAR forces an INIT clear + full GC16 for a clean slate.
#    timeout guards the baseline: if a render/display ever hangs on the SPI bus,
#    it's killed instead of wedging the bus forever.
ssh "$PI" 'cd ~/tidemark/build && make clean && make \
    && sudo env PWD=$(pwd) TIDEMARK_FULL_CLEAR=1 timeout 150 ./tidemark \
    && sudo systemctl start tidemark.timer \
    && echo "timer=$(systemctl is-active tidemark.timer)"' \
    || { echo "Build, baseline, or timer restart failed"; exit 1; }
