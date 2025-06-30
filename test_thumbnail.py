#!/usr/bin/env python3

import os
import sys
sys.path.append('/Users/anishlaha/Documents/GitHub/BraillifyAI')

# Test thumbnail generation
def test_thumbnail_generation():
    # Test if PyMuPDF works
    try:
        import fitz
        print("✅ PyMuPDF (fitz) is available")
        
        # Test with an actual PDF
        pdf_path = '/Users/anishlaha/Documents/GitHub/BraillifyAI/uploads/How_International_Students_Can_Secure_Research_Positions_at_Stanford.pdf'
        
        if os.path.exists(pdf_path):
            print(f"✅ PDF file exists: {pdf_path}")
            
            try:
                doc = fitz.open(pdf_path)
                print(f"✅ PDF opened successfully, pages: {len(doc)}")
                
                if len(doc) > 0:
                    page = doc[0]
                    mat = fitz.Matrix(150/72, 150/72)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Create thumbnails directory
                    os.makedirs('uploads/thumbnails', exist_ok=True)
                    
                    # Save thumbnail
                    thumbnail_path = 'uploads/thumbnails/test_thumb.png'
                    pix.save(thumbnail_path)
                    doc.close()
                    
                    print(f"✅ Thumbnail generated: {thumbnail_path}")
                    print(f"✅ File size: {os.path.getsize(thumbnail_path)} bytes")
                    
                else:
                    print("❌ PDF has no pages")
                    
            except Exception as e:
                print(f"❌ Error processing PDF: {e}")
                
        else:
            print(f"❌ PDF file not found: {pdf_path}")
            
    except ImportError as e:
        print(f"❌ PyMuPDF not available: {e}")

if __name__ == "__main__":
    test_thumbnail_generation()
