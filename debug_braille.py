#!/usr/bin/env python3
"""
Debug script to test Braille conversion specifically
"""

import os
import sys

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_braille_conversion():
    """Test Braille conversion directly"""
    print("🔍 Testing Braille Conversion")
    print("=" * 40)
    
    try:
        # Test liblouis import
        print("1. Testing liblouis import...")
        import louis
        print("✅ liblouis imported successfully")
        
        # Test basic conversion
        print("\n2. Testing basic Braille conversion...")
        sample_text = "Hello World! This is a test."
        
        # Try Grade 1 conversion
        try:
            braille_g1 = louis.translateString(["en-us-g1.ctb"], sample_text)
            print(f"✅ Grade 1 conversion successful: {braille_g1}")
        except Exception as e:
            print(f"❌ Grade 1 conversion failed: {e}")
        
        # Try Grade 2 conversion
        try:
            braille_g2 = louis.translateString(["en-us-g2.ctb"], sample_text)
            print(f"✅ Grade 2 conversion successful: {braille_g2}")
        except Exception as e:
            print(f"❌ Grade 2 conversion failed: {e}")
        
        print("\n3. Testing BrailleConversionService...")
        from app.services import BrailleConversionService
        
        braille_service = BrailleConversionService()
        print("✅ BrailleConversionService initialized")
        
        # Test conversion through service
        result = braille_service.convert_to_braille(sample_text, grade=2)
        print(f"Service result status: {result.get('status')}")
        
        if result.get('status') == 'success':
            print(f"✅ Service conversion successful!")
            print(f"Braille text: {result.get('braille_text', '')[:50]}...")
            print(f"Grade: {result.get('grade')}")
            print(f"Table used: {result.get('table_used')}")
            
            # Test pagination
            pagination = result.get('pagination', {})
            print(f"Pages: {pagination.get('total_pages', 0)}")
            print(f"Lines per page: {pagination.get('lines_per_page', 0)}")
            print(f"Chars per line: {pagination.get('chars_per_line', 0)}")
        else:
            print(f"❌ Service conversion failed: {result.get('error', 'Unknown error')}")
        
        print("\n4. Testing longer text...")
        long_text = """This is a longer text sample that will test the pagination and formatting features of the Braille conversion system. It contains multiple sentences and should demonstrate how the system handles line wrapping and page breaks according to standard Braille formatting rules."""
        
        long_result = braille_service.convert_to_braille(long_text, grade=2)
        if long_result.get('status') == 'success':
            print(f"✅ Long text conversion successful!")
            pagination = long_result.get('pagination', {})
            print(f"Pages: {pagination.get('total_pages', 0)}")
            print(f"Total lines: {pagination.get('total_lines', 0)}")
        else:
            print(f"❌ Long text conversion failed: {long_result.get('error')}")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure liblouis is properly installed and accessible")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_braille_conversion()

