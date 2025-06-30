#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/anishlaha/Documents/GitHub/BraillifyAI')

from app import create_app, db
from app.models import Upload
from app.services import TextOptimizationService
from datetime import datetime

def reoptimize_all_uploads():
    """Re-optimize all uploads that don't have optimized text or have poor optimization"""
    app = create_app()
    
    with app.app_context():
        uploads = Upload.query.all()
        optimization_service = TextOptimizationService()
        
        print(f"Found {len(uploads)} uploads to check for re-optimization")
        print("=" * 80)
        
        for upload in uploads:
            print(f"\nProcessing Upload ID: {upload.id} - {upload.filename}")
            
            # Check if we need to re-optimize
            needs_optimization = (
                not upload.optimized_text or  # No optimized text
                not upload.is_optimized or    # Not marked as optimized
                len(upload.optimized_text) < 100  # Very short optimized text (likely failed)
            )
            
            if needs_optimization and upload.text_content:
                print("  → Needs optimization, processing...")
                
                try:
                    # Determine document type from filename
                    doc_type = "textbook"
                    if "personal" in upload.filename.lower() or "statement" in upload.filename.lower():
                        doc_type = "personal_statement"
                    elif "physics" in upload.filename.lower():
                        doc_type = "physics"
                    
                    # Optimize the text
                    result = optimization_service.optimize_extracted_text(
                        upload.text_content, 
                        document_type=doc_type
                    )
                    
                    # Save results
                    upload.optimized_text = result.get('optimized_text')
                    upload.is_optimized = True
                    upload.optimization_date = datetime.utcnow()
                    upload.optimization_model = result.get('model_used', 'unknown')
                    upload.optimization_notes = result.get('improvement_notes', '')
                    
                    db.session.commit()
                    
                    print(f"  ✅ Optimized! {len(upload.text_content)} → {len(upload.optimized_text)} chars")
                    print(f"     Model: {upload.optimization_model}")
                    
                except Exception as e:
                    print(f"  ❌ Error: {e}")
            
            else:
                print("  ✓ Already optimized or no text content")

if __name__ == "__main__":
    reoptimize_all_uploads()

