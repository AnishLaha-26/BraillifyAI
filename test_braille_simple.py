#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_braille_conversion():
    """Test Braille conversion with the updated service"""
    try:
        from app.services import BrailleConversionService
        
        print("🧪 Testing Braille Conversion Service")
        print("=" * 50)
        
        # Create service
        braille_service = BrailleConversionService()
        
        # Test simple text
        test_text = "Hello world. This is a test."
        print(f"Input text: {test_text}")
        print()
        
        # Test conversion
        result = braille_service.convert_to_braille(test_text, grade=2)
        
        print(f"Status: {result.get('status')}")
        print(f"Error: {result.get('error', 'None')}")
        print(f"Braille text length: {len(result.get('braille_text', ''))}")
        print(f"Braille text: {repr(result.get('braille_text', ''))}")
        print(f"Pagination: {result.get('pagination', {})}")
        
        if result.get('braille_text'):
            print("\n📄 Braille Output:")
            print(result.get('braille_text'))
        
        return result.get('status') == 'success'
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_liblouis_direct():
    """Test liblouis directly"""
    try:
        print("\n🔧 Testing liblouis directly")
        print("=" * 50)
        
        import louis
        
        # Test basic translation
        text = "Hello world"
        table = "en-us-g2.ctb"
        
        print(f"Input: {text}")
        print(f"Table: {table}")
        
        # Basic translation
        braille_ascii = louis.translateString([table], text)
        print(f"ASCII Braille: {braille_ascii}")
        
        # Try dots mode
        try:
            braille_dots = louis.translateString([table], text, mode=louis.dotsIO)
            print(f"Dots mode: {braille_dots}")
        except Exception as e:
            print(f"Dots mode failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ liblouis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Braille Conversion Debug Tests")
    print()
    
    # Test liblouis first
    liblouis_ok = test_liblouis_direct()
    
    # Test our service
    service_ok = test_braille_conversion()
    
    print("\n📊 Test Results:")
    print(f"liblouis direct: {'✅ PASS' if liblouis_ok else '❌ FAIL'}")
    print(f"BrailleConversionService: {'✅ PASS' if service_ok else '❌ FAIL'}")
