#!/bin/bash

# ARIA - Adaptive Responsive Intelligence Assistant Installation Script

set -e

echo "🤖 Installing ARIA - Adaptive Responsive Intelligence Assistant..."

# Get the current directory
INSTALL_DIR="$(pwd)"
SERVICE_NAME="aria"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root. Please run as your regular user."
   exit 1
fi

# Check if Python 3.8+ is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "❌ Python 3.8+ is required. Found version: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION found"

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install --upgrade pip3
pip3 install -r requirements.txt

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama is not installed. Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    echo "✅ Ollama installed"
else
    echo "✅ Ollama is already installed"
fi

# Start Ollama service if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "🚀 Starting Ollama service..."
    ollama serve &
    sleep 3
fi

# Pull the default model
echo "🧠 Pulling AI model (this may take a while)..."
ollama pull llama2:7b

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating configuration file..."
    cat > .env << EOF
# ARIA - Adaptive Responsive Intelligence Assistant Configuration
DEBUG=false
HOST=127.0.0.1
PORT=8000

# AI Model Settings
OLLAMA_HOST=http://localhost:11434
MODEL_NAME=llama2:7b

# Speech Settings
TTS_ENABLED=true
TTS_RATE=150
TTS_VOLUME=0.8
TTS_FESTIVAL_VOICE=cmu_us_slt_cg

# Boot Monitoring
BOOT_CHECK_INTERVAL=5
BOOT_TIMEOUT=300
EOF
    echo "✅ ARIA configuration file created at .env"
fi

# Update service file with correct paths
echo "⚙️  Configuring systemd service..."
sed -i "s|/home/shelemiah/Personal/aria_ai|$INSTALL_DIR|g" aria.service

# Install systemd service
SERVICE_FILE="$HOME/.config/systemd/user/$SERVICE_NAME.service"
mkdir -p "$HOME/.config/systemd/user"
cp aria.service "$SERVICE_FILE"

# Enable and start the service
echo "🚀 Installing systemd service..."
systemctl --user daemon-reload
systemctl --user enable $SERVICE_NAME.service

# Enable lingering so service starts at boot
sudo loginctl enable-linger $USER

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Start the service: systemctl --user start $SERVICE_NAME"
echo "   2. Check status: systemctl --user status $SERVICE_NAME"
echo "   3. View logs: journalctl --user -u $SERVICE_NAME -f"
echo "   4. Test manually: python main.py"
echo ""
echo "🔧 Configuration:"
echo "   - Edit .env file to customize settings"
echo "   - Service will auto-start on next boot"
echo "   - API available at http://localhost:8000"
echo ""
echo "🧪 Test the greeting:"
echo "   curl -X POST http://localhost:8000/api/v1/greeting/deliver"
echo ""
echo "🔊 Audio Requirements:"
echo "   If you don't hear speech, install audio packages:"
echo "   sudo pacman -S espeak-ng alsa-utils  # Arch/Manjaro"
echo "   sudo apt install espeak-ng alsa-utils  # Ubuntu/Debian"
echo ""
echo "📋 Troubleshooting: See TROUBLESHOOTING.md for detailed help"
echo ""

deactivate
