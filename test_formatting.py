#!/usr/bin/env python3
"""
Test script to check the new Braille formatting
"""

import sys
import os
sys.path.append('/Users/anishlaha/Documents/GitHub/BraillifyAI')

from app import create_app, db
from app.models import Upload

def test_formatting():
    """Test the new Braille formatting on a sample document"""
    app = create_app()
    
    with app.app_context():
        # Get the first upload to test
        upload = Upload.query.first()
        
        if not upload:
            print("No uploads found to test")
            return
        
        print(f"Testing document: {upload.filename}")
        print(f"=" * 50)
        
        if upload.optimized_text:
            print("OPTIMIZED TEXT (first 20 lines):")
            print("-" * 30)
            lines = upload.optimized_text.split('\n')
            for i, line in enumerate(lines[:20], 1):
                char_count = len(line)
                status = "✓" if char_count <= 40 else f"✗ ({char_count} chars)"
                print(f"{i:2d}: '{line}' {status}")
            
            print(f"\nLine length analysis:")
            print(f"Total lines: {len(lines)}")
            long_lines = [line for line in lines if len(line) > 40]
            print(f"Lines > 40 chars: {len(long_lines)}")
            
            if long_lines:
                print("Examples of long lines:")
                for line in long_lines[:3]:
                    print(f"  '{line}' ({len(line)} chars)")
        else:
            print("No optimized text found")

if __name__ == '__main__':
    test_formatting()
