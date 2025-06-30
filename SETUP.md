# BraillifyAI Setup Guide

This guide will help you set up the enhanced BraillifyAI system with AI text optimization, OCR, and braille conversion capabilities.

## Prerequisites

- Python 3.8 or higher
- macOS, Linux, or Windows
- Internet connection (for Hack Club AI)

## 1. System Dependencies

### macOS
```bash
# Install Tesseract OCR
brew install tesseract

# Install liblouis for braille conversion
brew install liblouis

# Install poppler for PDF to image conversion
brew install poppler
```

### Ubuntu/Debian
```bash
# Install Tesseract OCR
sudo apt-get update
sudo apt-get install tesseract-ocr

# Install liblouis for braille conversion
sudo apt-get install liblouis-dev liblouis-data

# Install poppler for PDF to image conversion
sudo apt-get install poppler-utils
```

### Windows
```bash
# Install using chocolatey
choco install tesseract
choco install poppler

# Or download manually:
# Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
# Poppler: https://blog.alivate.com.au/poppler-windows/
```

## 2. Python Dependencies

```bash
# Navigate to project directory
cd /path/to/BraillifyAI

# Install Python dependencies
pip install -r requirements.txt
```

## 3. Database Setup

```bash
# Create new migration for enhanced features
flask db migrate -m "Add AI optimization, OCR, and braille conversion fields"

# Apply migrations
flask db upgrade
```

## 4. Configuration

### Environment Variables (Optional)
Create a `.env` file in the project root:

```env
# Flask configuration
FLASK_APP=run.py
FLASK_ENV=development

# Database
DATABASE_URL=sqlite:///braillify.db

# File upload settings
MAX_CONTENT_LENGTH=16777216  # 16MB in bytes
UPLOAD_FOLDER=uploads
```

### Tesseract Configuration (if needed)
If Tesseract is not in your PATH, update `app/services.py`:

```python
# In OCRService.__init__()
pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract'  # macOS
# or
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows
```

## 5. Verify Installation

### Test Tesseract OCR
```bash
tesseract --version
```

### Test liblouis
```bash
python -c "import louis; print('liblouis working!')"
```

### Test PDF conversion
```bash
python -c "from pdf2image import convert_from_path; print('pdf2image working!')"
```

### Test Hack Club AI
```bash
curl -X POST https://ai.hackclub.com/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

## 6. Run the Application

```bash
# Start the Flask development server
python run.py

# Or using Flask CLI
flask run
```

The application will be available at `http://localhost:5000`

## 7. Testing the Pipeline

1. **Upload a PDF document** through the web interface
2. **Check the uploads list** to see processing status
3. **Use the processing buttons**:
   - "Optimize Text" - Uses Hack Club AI to improve text
   - "Convert to Braille" - Converts text to braille format
   - "Process OCR" - Extract text from images/scanned PDFs
   - "Full Pipeline" - Runs all steps automatically

## Features Overview

### 🤖 AI Text Optimization
- Uses Hack Club AI (no API key required!)
- Fixes OCR errors and formatting issues
- Optimizes text structure for braille conversion
- Fallback to basic cleanup if AI unavailable

### 👁️ OCR Processing
- Extract text from images (JPG, PNG, etc.)
- Process scanned PDF documents
- Confidence scoring for OCR results
- Support for multiple languages

### ⠃ Braille Conversion
- Grade 1 and Grade 2 braille support
- Automatic pagination for printing
- Configurable page dimensions
- Page-by-page viewing

### 📄 Document Processing Pipeline
- PDF text extraction
- Multi-step processing workflow
- Progress tracking and status updates
- Database storage of all processing steps

## Troubleshooting

### Common Issues

**"Tesseract not found"**
- Ensure Tesseract is installed and in PATH
- Update tesseract_cmd path in services.py

**"liblouis import error"**
- Install liblouis system package
- Reinstall python-braille: `pip install --force-reinstall python-braille`

**"pdf2image conversion failed"**
- Install poppler utilities
- Check PDF file permissions

**"Hack Club AI timeout"**
- Check internet connection
- Verify ai.hackclub.com is accessible
- System will fallback to basic text cleanup

### Performance Tips

- **Large PDFs**: Consider splitting into smaller files
- **OCR Processing**: Higher DPI = better accuracy but slower processing
- **Braille Conversion**: Grade 2 braille is more compact than Grade 1

## Development

### Adding New Features
1. Update models in `app/models.py`
2. Create migration: `flask db migrate -m "description"`
3. Apply migration: `flask db upgrade`
4. Add service logic in `app/services.py`
5. Create API routes in `app/routes.py`
6. Update frontend in templates

### API Endpoints
- `POST /upload` - Upload files
- `POST /optimize-text/<id>` - AI text optimization
- `POST /convert-to-braille/<id>` - Braille conversion
- `POST /process-ocr/<id>` - OCR processing
- `POST /full-pipeline/<id>` - Complete pipeline
- `GET /uploads` - List all uploads
- `GET /upload/<id>` - Get upload details
- `GET /get-braille-page/<id>/<page>` - Get braille page

## Support

For issues or questions:
1. Check this setup guide
2. Review error logs in terminal
3. Test individual components (OCR, braille, AI)
4. Ensure all system dependencies are installed

Happy braille converting! 🎉
