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
    
    # For documents (PDF/text files)
    text_content = db.Column(db.Text)
    page_count = db.Column(db.Integer)
    text_file_path = db.Column(db.String(512))  # Path to extracted text file for PDFs
    
    # Processing status
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, error
    error_message = db.Column(db.Text)
    
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
            'text_preview': self.text_content[:200] + '...' if self.text_content and len(self.text_content) > 200 else self.text_content
        }
    
    def __repr__(self):
        return f'<Upload {self.filename}>'
