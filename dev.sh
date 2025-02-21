#!/bin/bash
# Sync files to Pi
rsync -av --exclude '.git' --exclude '*.o' --exclude 'tidemark' --exclude 'tidemark_sim' ./ reed@10.10.10.76:~/tidemark/

# Build and run the main program
ssh reed@10.10.10.76 "cd tidemark && make clean && PLATFORM=linux make && sudo ./tidemark"
