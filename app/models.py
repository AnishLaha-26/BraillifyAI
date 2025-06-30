from datetime import datetime
from . import db

class Upload(db.Model):
    """Model for tracking uploaded files and their metadata."""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # 'audio', 'image', or 'document'
    mime_type = db.Column(db.String(100))
    file_size = db.Column(db.Integer)  # Size in bytes
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Auto-generated or user-defined title
    title = db.Column(db.String(500))
    
    # For documents (PDF/text files)
    text_content = db.Column(db.Text)
    page_count = db.Column(db.Integer)
    text_file_path = db.Column(db.String(512))  # Path to extracted text file for PDFs
    
    # AI Text Optimization
    optimized_text = db.Column(db.Text)
    optimization_notes = db.Column(db.Text)
    is_optimized = db.Column(db.Boolean, default=False)
    optimization_date = db.Column(db.DateTime)
    optimization_model = db.Column(db.String(100))  # Track which model/method was used
    
    # OCR Results (for images and scanned documents)
    ocr_text = db.Column(db.Text)
    ocr_confidence = db.Column(db.Float)
    ocr_word_count = db.Column(db.Integer)
    is_ocr_processed = db.Column(db.Boolean, default=False)
    ocr_date = db.Column(db.DateTime)
    
    # Braille Conversion
    braille_text = db.Column(db.Text)  # Keep for backward compatibility
    braille_content = db.Column(db.Text)  # New field for Unicode Braille content
    braille_grade = db.Column(db.Integer)  # 1 or 2
    braille_pages = db.Column(db.Integer)
    braille_chars_per_page = db.Column(db.Integer)
    braille_lines_per_page = db.Column(db.Integer)
    is_braille_converted = db.Column(db.Boolean, default=False)
    braille_conversion_date = db.Column(db.DateTime)
    
    # PDF Generation
    pdf_path = db.Column(db.String(512))  # Path to embossable Braille PDF
    preview_pdf_path = db.Column(db.String(512))  # Path to preview PDF for sighted users
    pdf_generation_date = db.Column(db.DateTime)
    
    # Processing status
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, error
    error_message = db.Column(db.Text)
    processing_steps = db.Column(db.Text)  # JSON string of completed steps
    
    def __init__(self, filename, file_path, file_type, mime_type=None, file_size=None):
        self.filename = filename
        self.file_path = file_path
        self.file_type = file_type
        self.mime_type = mime_type
        self.file_size = file_size
        self.status = 'pending'
    
    def to_dict(self):
        """Convert upload record to dictionary for API responses."""
        return {
            'id': self.id,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'upload_date': self.upload_date.isoformat(),
            'status': self.status,
            'page_count': self.page_count if self.page_count else None,
            'text_preview': self.text_content[:200] + '...' if self.text_content and len(self.text_content) > 200 else self.text_content,
            'is_optimized': self.is_optimized,
            'is_ocr_processed': self.is_ocr_processed,
            'is_braille_converted': self.is_braille_converted,
            'braille_pages': self.braille_pages,
            'braille_grade': self.braille_grade,
            'ocr_confidence': self.ocr_confidence
        }
    
    def __repr__(self):
        return f'<Upload {self.filename}>'
