#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/anishlaha/Documents/GitHub/BraillifyAI')

from app import create_app, db
from app.models import Upload

def check_uploads():
    """Check what's in the database"""
    app = create_app()
    
    with app.app_context():
        uploads = Upload.query.all()
        
        print(f"Found {len(uploads)} uploads in database:")
        print("=" * 80)
        
        for upload in uploads:
            print(f"\nUpload ID: {upload.id}")
            print(f"Filename: {upload.filename}")
            print(f"Status: {upload.status}")
            print(f"Has optimized text: {bool(upload.optimized_text)}")
            print(f"Is optimized: {upload.is_optimized}")
            print(f"Original text length: {len(upload.text_content) if upload.text_content else 0}")
            print(f"Optimized text length: {len(upload.optimized_text) if upload.optimized_text else 0}")
            
            if upload.text_content:
                print(f"Original text preview: {upload.text_content[:100]}...")
            
            if upload.optimized_text:
                print(f"Optimized text preview: {upload.optimized_text[:100]}...")
            else:
                print("No optimized text found!")
            
            print("-" * 40)

if __name__ == "__main__":
    check_uploads()
