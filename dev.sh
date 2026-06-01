#!/bin/bash
set -e  # Exit on error

PI=reed@10.10.10.76

# Deploy safely. The IT8951 panel corrupts if two processes hit the SPI bus at
# once, so we must never run ./tidemark manually while tidemark.timer is live.
# Sequence: stop the timer -> sync -> build -> one clean full-clear baseline
# (INIT clear + full GC16, resets ghosting) -> restart the timer.

# 1. Stop the timer so nothing fires mid-deploy or collides on the SPI bus.
ssh "$PI" 'sudo systemctl stop tidemark.timer' || { echo "Failed to stop timer"; exit 1; }

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
ssh "$PI" 'cd ~/tidemark/build && make clean && make \
    && sudo env PWD=$(pwd) TIDEMARK_FULL_CLEAR=1 ./tidemark \
    && sudo systemctl start tidemark.timer \
    && echo "timer=$(systemctl is-active tidemark.timer)"' \
    || { echo "Build, baseline, or timer restart failed"; exit 1; }
