#!/bin/bash
# Deployment script for Tidemark on Raspberry Pi

# Configuration
PI_USER="pi"
PI_HOST="raspberrypi.local"
PI_DIR="/home/pi/tidemark"
PI_DEPENDENCIES="python3-pip python3-pil python3-numpy"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Tidemark Deployment Script${NC}"
echo "=================================="
echo

# Build locally first
echo -e "${YELLOW}Building Tidemark locally...${NC}"
cd build
make clean
make
if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed! Aborting deployment.${NC}"
    exit 1
fi
cd ..

# Check if Raspberry Pi is reachable
echo -e "${YELLOW}Checking connection to Raspberry Pi...${NC}"
ping -c 1 $PI_HOST > /dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Cannot reach $PI_HOST. Check connection and hostname.${NC}"
    exit 1
fi

# Create directory structure on Pi
echo -e "${YELLOW}Creating directories on Raspberry Pi...${NC}"
ssh $PI_USER@$PI_HOST "mkdir -p $PI_DIR/src/c/display $PI_DIR/src/python/render $PI_DIR/src/python/data $PI_DIR/lib/IT8951 $PI_DIR/build"

# Install dependencies on Pi
echo -e "${YELLOW}Installing dependencies on Raspberry Pi...${NC}"
ssh $PI_USER@$PI_HOST "sudo apt-get update && sudo apt-get install -y $PI_DEPENDENCIES"
ssh $PI_USER@$PI_HOST "pip3 install matplotlib"

# Copy files to Pi
echo -e "${YELLOW}Copying files to Raspberry Pi...${NC}"

# Copy Python files
scp src/python/main.py $PI_USER@$PI_HOST:$PI_DIR/src/python/
scp src/python/render/*.py $PI_USER@$PI_HOST:$PI_DIR/src/python/render/
scp src/python/data/*.py $PI_USER@$PI_HOST:$PI_DIR/src/python/data/

# Copy C files
scp src/c/main.c $PI_USER@$PI_HOST:$PI_DIR/src/c/
scp src/c/display/*.c src/c/display/*.h $PI_USER@$PI_HOST:$PI_DIR/src/c/display/

# Copy library files
scp -r lib/IT8951/* $PI_USER@$PI_HOST:$PI_DIR/lib/IT8951/

# Copy build files
scp build/Makefile $PI_USER@$PI_HOST:$PI_DIR/build/

# Copy README and other files
scp README.md $PI_USER@$PI_HOST:$PI_DIR/
scp CLAUDE.md $PI_USER@$PI_HOST:$PI_DIR/ 2>/dev/null || :  # Optional file

# Make Python scripts executable
ssh $PI_USER@$PI_HOST "chmod +x $PI_DIR/src/python/main.py $PI_DIR/src/python/render/*.py $PI_DIR/src/python/data/*.py"

# Create Python virtual environment on Pi (if needed)
echo -e "${YELLOW}Setting up Python virtual environment on Raspberry Pi...${NC}"
ssh $PI_USER@$PI_HOST "cd $PI_DIR && python3 -m venv venv && . venv/bin/activate && pip3 install pillow numpy matplotlib"

# Create systemd service file
echo -e "${YELLOW}Setting up systemd service...${NC}"
cat > tidemark.service << EOF
[Unit]
Description=Tidemark E-Ink Tide Chart Display
After=network.target

[Service]
Environment=TIDEMARK_DAEMON=1
WorkingDirectory=$PI_DIR/build
ExecStart=$PI_DIR/build/tidemark
Restart=on-failure
User=$PI_USER

[Install]
WantedBy=multi-user.target
EOF

# Copy and enable service
scp tidemark.service $PI_USER@$PI_HOST:/tmp/
ssh $PI_USER@$PI_HOST "sudo mv /tmp/tidemark.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable tidemark.service"

# Build on Pi
echo -e "${YELLOW}Building on Raspberry Pi...${NC}"
ssh $PI_USER@$PI_HOST "cd $PI_DIR/build && make clean && make"

# Start the service
echo -e "${YELLOW}Starting Tidemark service...${NC}"
ssh $PI_USER@$PI_HOST "sudo systemctl restart tidemark.service"

# Create a simple script to update manually
cat > update_tide.sh << EOF
#!/bin/bash
cd $PI_DIR/build
./tidemark
EOF

scp update_tide.sh $PI_USER@$PI_HOST:$PI_DIR/
ssh $PI_USER@$PI_HOST "chmod +x $PI_DIR/update_tide.sh"

echo -e "${GREEN}Deployment complete!${NC}"
echo "You can manually update the display by running: $PI_DIR/update_tide.sh"
echo "To check service status: sudo systemctl status tidemark.service"
echo "To stop service: sudo systemctl stop tidemark.service"
echo "To start service: sudo systemctl start tidemark.service"