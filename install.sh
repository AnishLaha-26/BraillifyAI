#!/bin/bash

# BraillifyAI Installation Script for macOS
# This script automates the setup process for the enhanced BraillifyAI system

set -e  # Exit on any error

echo "🎯 BraillifyAI Enhanced Setup Script"
echo "===================================="
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is designed for macOS. Please follow the manual setup guide for other systems."
    exit 1
fi

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew is required but not installed."
    echo "Please install Homebrew first: https://brew.sh/"
    exit 1
fi

echo "✅ Homebrew found"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [[ $(echo "$python_version >= $required_version" | bc -l) -eq 0 ]]; then
    echo "❌ Python 3.8+ is required. Found: Python $python_version"
    exit 1
fi

echo "✅ Python $python_version found"

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."

# Install Tesseract OCR
if ! command -v tesseract &> /dev/null; then
    echo "Installing Tesseract OCR..."
    brew install tesseract
else
    echo "✅ Tesseract already installed"
fi

# Install liblouis
if ! brew list liblouis &> /dev/null; then
    echo "Installing liblouis..."
    brew install liblouis
else
    echo "✅ liblouis already installed"
fi

# Install poppler
if ! brew list poppler &> /dev/null; then
    echo "Installing poppler..."
    brew install poppler
else
    echo "✅ poppler already installed"
fi

# Install Python dependencies
echo ""
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# Set up database
echo ""
echo "🗄️ Setting up database..."

# Check if Flask is available
if ! python3 -c "import flask" &> /dev/null; then
    echo "❌ Flask not found. Please check your Python dependencies installation."
    exit 1
fi

# Create migration
echo "Creating database migration..."
export FLASK_APP=run.py
python3 -m flask db migrate -m "Add AI optimization, OCR, and braille conversion fields" || echo "Migration may already exist"

# Apply migration
echo "Applying database migration..."
python3 -m flask db upgrade

# Create uploads directory
echo ""
echo "📁 Creating uploads directory..."
mkdir -p uploads

# Test installations
echo ""
echo "🧪 Testing installations..."

# Test Tesseract
if tesseract --version &> /dev/null; then
    echo "✅ Tesseract OCR working"
else
    echo "❌ Tesseract test failed"
fi

# Test liblouis
if python3 -c "import louis; print('✅ liblouis working')" 2>/dev/null; then
    echo "✅ liblouis working"
else
    echo "❌ liblouis test failed"
fi

# Test pdf2image
if python3 -c "from pdf2image import convert_from_path; print('✅ pdf2image working')" 2>/dev/null; then
    echo "✅ pdf2image working"
else
    echo "❌ pdf2image test failed"
fi

# Test Hack Club AI
echo "Testing Hack Club AI connection..."
if curl -s -X POST https://ai.hackclub.com/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "Hello!"}]}' > /dev/null; then
    echo "✅ Hack Club AI accessible"
else
    echo "⚠️  Hack Club AI test failed (may be network issue)"
fi

echo ""
echo "🎉 Setup Complete!"
echo "==================="
echo ""
echo "To start the application:"
echo "  python3 run.py"
echo ""
echo "Then visit: http://localhost:5000"
echo ""
echo "Features available:"
echo "  🤖 AI Text Optimization (via Hack Club AI)"
echo "  👁️  OCR Processing (images & scanned PDFs)"
echo "  ⠃  Braille Conversion (Grade 1 & 2)"
echo "  📄 Full Processing Pipeline"
echo ""
echo "For troubleshooting, see SETUP.md"
echo ""
echo "Happy braille converting! 🎯"
