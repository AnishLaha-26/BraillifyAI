#!/usr/bin/env python3
"""
Script to reprocess existing uploads with the new improved Braille formatting prompt
"""

import sys
import os
sys.path.append('/Users/anishlaha/Documents/GitHub/BraillifyAI')

from app import create_app, db
from app.models import Upload
from app.services import TextOptimizationService, BrailleConversionService

def reprocess_documents():
    """Reprocess all documents with the new Braille formatting prompt"""
    app = create_app()
    
    with app.app_context():
        # Initialize services
        text_optimizer = TextOptimizationService()
        braille_service = BrailleConversionService()
        
        # Get all uploads
        uploads = Upload.query.all()
        print(f"Found {len(uploads)} uploads to reprocess")
        
        for i, upload in enumerate(uploads, 1):
            print(f"\n[{i}/{len(uploads)}] Processing: {upload.filename}")
            
            try:
                # Use the original text content for reprocessing
                text_to_optimize = upload.text_content
                if not text_to_optimize:
                    print(f"  No text content found, skipping...")
                    continue
                
                print(f"  Original text length: {len(text_to_optimize)} chars")
                
                # Apply new optimization with improved Braille formatting
                print("  Applying new AI optimization...")
                optimization_result = text_optimizer.optimize_extracted_text(
                    text_to_optimize, 
                    document_type="textbook"
                )
                
                if optimization_result.get("optimized_text"):
                    optimized_text = optimization_result["optimized_text"]
                    print(f"  Optimized text length: {len(optimized_text)} chars")
                    
                    # Show sample of optimized text (first 3 lines)
                    sample_lines = optimized_text.split('\n')[:3]
                    print("  Sample optimized text:")
                    for line in sample_lines:
                        print(f"    '{line[:60]}{'...' if len(line) > 60 else ''}'")
                    
                    # Update the database with new optimized text
                    upload.optimized_text = optimized_text
                    upload.ai_optimization_notes = optimization_result.get("improvement_notes", "")
                    upload.ai_optimization_completed = True
                    
                    # Clear existing Braille conversion to force regeneration
                    upload.braille_text = None
                    upload.braille_conversion_completed = False
                    upload.braille_conversion_notes = None
                    
                    # Apply new Braille formatting
                    print("  Applying Braille conversion...")
                    braille_result = braille_service.convert_to_braille(optimized_text)
                    
                    if braille_result.get("status") == "success":
                        upload.braille_text = braille_result["braille_text"]
                        upload.braille_conversion_completed = True
                        upload.braille_conversion_notes = f"Grade {braille_result['grade']} conversion successful"
                        print(f"  Braille conversion completed")
                    else:
                        print(f"  Braille conversion failed: {braille_result.get('error', 'Unknown error')}")
                    
                    # Commit changes
                    db.session.commit()
                    print(f"  Database updated successfully")
                    
                else:
                    print(f"  Optimization failed: {optimization_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"  Error processing upload: {e}")
                db.session.rollback()
        
        print(f"\n Reprocessing complete! Processed {len(uploads)} documents.")
        print("\nThe documents should now have proper Braille formatting with:")
        print("- 40-character line limits")
        print("- Proper paragraph indentation")
        print("- Consistent spacing and punctuation")
        print("- Standardized list formatting")

if __name__ == '__main__':
    reprocess_documents()
