#!/bin/bash
# Financial Email Agent - Setup Script
# This script automates the setup process for the Financial Email Agent

set -e  # Exit on error

echo "=========================================="
echo "Financial Email Agent - Setup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION found"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION found"
    PYTHON_CMD="python"
else
    print_error "Python not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check if Python version is 3.8 or higher
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    print_error "Python 3.8 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo ""
echo "Step 1: Creating virtual environment..."
if [ -d "venv" ]; then
    print_info "Virtual environment already exists. Skipping creation."
else
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
fi

echo ""
echo "Step 2: Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    source venv/Scripts/activate
    print_success "Virtual environment activated (Windows)"
else
    # Unix-like
    source venv/bin/activate
    print_success "Virtual environment activated (Unix)"
fi

echo ""
echo "Step 3: Upgrading pip..."
pip install --upgrade pip setuptools wheel
print_success "pip upgraded"

echo ""
echo "Step 4: Installing dependencies..."
pip install -r requirements.txt
print_success "Core dependencies installed"

if [ -f "requirements-dev.txt" ]; then
    echo ""
    read -p "Install development dependencies? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install -r requirements-dev.txt
        print_success "Development dependencies installed"
    fi
fi

echo ""
echo "Step 5: Creating necessary directories..."
mkdir -p logs
mkdir -p credentials
mkdir -p data/attachments
mkdir -p data/processed
print_success "Directories created"

echo ""
echo "Step 6: Setting up configuration..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success ".env file created from template"
    print_info "Please edit .env file with your configuration"
else
    print_info ".env file already exists"
fi

if [ ! -f "config/config.yaml" ]; then
    cp config/config.example.yaml config/config.yaml
    print_success "config.yaml created from template"
    print_info "Please edit config/config.yaml with your settings"
else
    print_info "config.yaml already exists"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
print_info "Next steps:"
echo "1. Configure Gmail API:"
echo "   - Visit https://console.cloud.google.com/"
echo "   - Create a new project"
echo "   - Enable Gmail API"
echo "   - Create OAuth 2.0 credentials"
echo "   - Download credentials.json to project root"
echo ""
echo "2. Set up MongoDB:"
echo "   - Install MongoDB locally OR use MongoDB Atlas"
echo "   - Update MONGODB_CONNECTION_STRING in .env"
echo ""
echo "3. Install Ollama:"
echo "   - Visit https://ollama.ai/"
echo "   - Download and install Ollama"
echo "   - Run: ollama pull llama3.1:8b"
echo ""
echo "4. Update configuration:"
echo "   - Edit .env file with your settings"
echo "   - Edit config/config.yaml if needed"
echo ""
echo "5. Test the setup:"
echo "   - Run: python src/main.py"
echo ""
print_success "Happy coding! 🚀"

# Made with Bob
