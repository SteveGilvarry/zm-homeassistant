#!/bin/bash
# Development environment setup script

set -e

echo "=========================================="
echo "zm-homeassistant development environment setup"
echo "=========================================="
echo

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install Python 3.11+ first"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo
echo "Installing dependencies..."
pip install aiohttp --quiet
echo "✓ Installed aiohttp"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo
    echo "⚠️  IMPORTANT: Edit .env and fill in your ZoneMinder credentials!"
    echo "   File location: $(pwd)/.env"
else
    echo
    echo "✓ .env file already exists"
fi

echo
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo
echo "Next steps:"
echo "  1. Edit .env with your ZoneMinder credentials"
echo "  2. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo "  3. Run the test script:"
echo "     python test_api.py"
echo
