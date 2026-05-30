#!/bin/bash
set -e  # Exit on error

# Sync files to Pi
rsync -av --exclude '.git' --exclude '*.o' --exclude 'tidemark' --exclude 'tidemark_sim' --exclude 'venv' ./ reed@10.10.10.76:~/tidemark/ || { echo "Sync failed"; exit 1; }

# Build and run on Pi
# Note: sudo drops $PWD, which tidemark uses to locate the project root, so pass it explicitly.
ssh reed@10.10.10.76 "cd tidemark/build && make clean && make && sudo env PWD=\$(pwd) ./tidemark" || { echo "Build or run failed"; exit 1; }