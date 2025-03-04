#!/bin/bash
# Deployment script for Tidemark Bitmap version on Raspberry Pi

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

echo -e "${GREEN}Tidemark Bitmap Deployment Script${NC}"
echo "=================================="
echo

# Build locally first
echo -e "${YELLOW}Building Tidemark Bitmap version locally...${NC}"
cd build
make clean
make bitmap
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

# Create directory on Pi if it doesn't exist
echo -e "${YELLOW}Creating directory on Raspberry Pi...${NC}"
ssh $PI_USER@$PI_HOST "mkdir -p $PI_DIR/src"

# Install dependencies on Pi
echo -e "${YELLOW}Installing dependencies on Raspberry Pi...${NC}"
ssh $PI_USER@$PI_HOST "sudo apt-get update && sudo apt-get install -y $PI_DEPENDENCIES"
ssh $PI_USER@$PI_HOST "pip3 install matplotlib"

# Copy files to Pi
echo -e "${YELLOW}Copying files to Raspberry Pi...${NC}"
# Copy Python script
scp src/sky_display.py $PI_USER@$PI_HOST:$PI_DIR/src/

# Copy executable and library files
scp build/tidemark_bitmap $PI_USER@$PI_HOST:$PI_DIR/
scp -r lib/IT8951 $PI_USER@$PI_HOST:$PI_DIR/lib/

# Copy README
scp README_BITMAP.md $PI_USER@$PI_HOST:$PI_DIR/README.md

# Create systemd service file if it doesn't exist
echo -e "${YELLOW}Setting up systemd service...${NC}"
cat > tidemark.service << EOF
[Unit]
Description=Tidemark E-Ink Tide Chart Display
After=network.target

[Service]
Environment=TIDEMARK_DAEMON=1
WorkingDirectory=$PI_DIR
ExecStart=$PI_DIR/tidemark_bitmap
Restart=on-failure
User=$PI_USER

[Install]
WantedBy=multi-user.target
EOF

# Copy and enable service
scp tidemark.service $PI_USER@$PI_HOST:/tmp/
ssh $PI_USER@$PI_HOST "sudo mv /tmp/tidemark.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable tidemark.service"

# Start the service
echo -e "${YELLOW}Starting Tidemark service...${NC}"
ssh $PI_USER@$PI_HOST "sudo systemctl restart tidemark.service"

# Create a simple script to update tide data manually
cat > update_tides.sh << EOF
#!/bin/bash
cd $PI_DIR
./tidemark_bitmap
EOF

scp update_tides.sh $PI_USER@$PI_HOST:$PI_DIR/
ssh $PI_USER@$PI_HOST "chmod +x $PI_DIR/update_tides.sh"

echo -e "${GREEN}Deployment complete!${NC}"
echo "You can manually update the display by running: $PI_DIR/update_tides.sh"
echo "To check service status: sudo systemctl status tidemark.service"
echo "To stop service: sudo systemctl stop tidemark.service"
echo "To start service: sudo systemctl start tidemark.service"