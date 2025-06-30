#!/usr/bin/env python3
"""
Reprocess the current document with the new strict formatting
"""

import sys
import os
sys.path.append('/Users/anishlaha/Documents/GitHub/BraillifyAI')

from app import create_app, db
from app.models import Upload
from app.services import TextOptimizationService, BrailleConversionService

def reprocess_physics_doc():
    """Reprocess the Physics IA document with new formatting"""
    app = create_app()
    
    with app.app_context():
        # Find the Physics IA document
        upload = Upload.query.filter(Upload.filename.like('%Physics%')).first()
        
        if not upload:
            print("Physics document not found")
            return
        
        print(f"Found document: {upload.filename}")
        
        # Initialize services
        text_optimizer = TextOptimizationService()
        braille_service = BrailleConversionService()
        
        # Get original text
        original_text = upload.text_content
        if not original_text:
            print("No original text found")
            return
        
        print(f"Original text length: {len(original_text)} characters")
        print("First 200 chars:", original_text[:200])
        
        # Apply new aggressive optimization
        print("\n🔥 Applying NEW aggressive optimization...")
        optimization_result = text_optimizer.optimize_extracted_text(
            original_text, 
            document_type="academic"
        )
        
        if optimization_result.get("optimized_text"):
            optimized_text = optimization_result["optimized_text"]
            print(f"✅ New optimized text length: {len(optimized_text)} characters")
            
            # Show first few lines
            lines = optimized_text.split('\n')[:15]
            print("\n📝 First 15 lines of optimized text:")
            for i, line in enumerate(lines, 1):
                char_count = len(line)
                status = "✓" if char_count <= 40 else f"✗ ({char_count})"
                print(f"{i:2d}: '{line}' {status}")
            
            # Update database
            upload.optimized_text = optimized_text
            upload.optimization_notes = optimization_result.get("improvement_notes", "")
            
            # Clear and regenerate Braille
            upload.braille_text = None
            upload.braille_conversion_completed = False
            
            # Apply Braille conversion
            print("\n🔤 Applying Braille conversion...")
            braille_result = braille_service.convert_to_braille(optimized_text)
            
            if braille_result.get("status") == "success":
                upload.braille_text = braille_result["braille_text"]
                upload.braille_conversion_completed = True
                print("✅ Braille conversion completed")
            
            # Save to database
            db.session.commit()
            print("💾 Database updated successfully")
            
            # Line length analysis
            all_lines = optimized_text.split('\n')
            long_lines = [line for line in all_lines if len(line) > 40]
            print(f"\n📊 Line Analysis:")
            print(f"Total lines: {len(all_lines)}")
            print(f"Lines > 40 chars: {len(long_lines)}")
            
            if long_lines:
                print("❌ Examples of lines that are too long:")
                for line in long_lines[:5]:
                    print(f"  '{line}' ({len(line)} chars)")
            else:
                print("✅ All lines are 40 characters or less!")
                
        else:
            print("❌ Optimization failed:", optimization_result.get("error"))

if __name__ == '__main__':
    reprocess_physics_doc()
