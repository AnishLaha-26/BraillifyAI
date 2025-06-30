#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/anishlaha/Documents/GitHub/BraillifyAI')

from app import create_app, db
from app.models import Upload
from app.services import TextOptimizationService
from datetime import datetime

def force_reoptimize():
    """Force re-optimization of existing uploads to use the new content-preserving prompt"""
    app = create_app()
    
    with app.app_context():
        uploads = Upload.query.all()
        optimization_service = TextOptimizationService()
        
        print(f"Force re-optimizing {len(uploads)} uploads with improved prompt")
        print("=" * 80)
        
        for upload in uploads:
            print(f"\nForce Re-optimizing Upload ID: {upload.id} - {upload.filename}")
            
            if upload.text_content:
                try:
                    # Determine document type from filename
                    doc_type = "textbook"
                    if "personal" in upload.filename.lower() or "statement" in upload.filename.lower():
                        doc_type = "personal_statement"
                    elif "physics" in upload.filename.lower():
                        doc_type = "physics"
                    
                    print(f"  → Original text length: {len(upload.text_content)} chars")
                    
                    # Force re-optimization with the new prompt
                    result = optimization_service.optimize_extracted_text(
                        upload.text_content, 
                        document_type=doc_type
                    )
                    
                    # Save results
                    upload.optimized_text = result.get('optimized_text')
                    upload.is_optimized = True
                    upload.optimization_date = datetime.utcnow()
                    upload.optimization_model = result.get('model_used', 'unknown')
                    upload.optimization_notes = result.get('improvement_notes', '') + " (Re-optimized to preserve all content)"
                    
                    # Clear braille conversion to force re-conversion with new text
                    upload.braille_text = None
                    upload.is_braille_converted = False
                    upload.braille_conversion_date = None
                    
                    db.session.commit()
                    
                    print(f"  ✅ Re-optimized! {len(upload.text_content)} → {len(upload.optimized_text)} chars")
                    print(f"     Model: {upload.optimization_model}")
                    print(f"     Preview: {upload.optimized_text[:100]}...")
                    
                except Exception as e:
                    print(f"  ❌ Error: {e}")
            
            else:
                print("  ⚠️  No text content to optimize")

if __name__ == "__main__":
    force_reoptimize()
