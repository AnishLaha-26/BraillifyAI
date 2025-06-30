#!/usr/bin/env python3
"""
Test the complete BraillifyAI pipeline
"""

import sys
import os
import tempfile
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_full_pipeline():
    print("🚀 Testing Complete BraillifyAI Pipeline")
    print("=" * 50)
    
    try:
        # Test sample text
        sample_text = """Welcome to BraillifyAI Testing

This is a sample document that will be processed through our complete pipeline. The text contains multiple paragraphs and demonstrates various formatting scenarios.

Key Features:
- Text extraction and preprocessing
- AI-powered text optimization 
- Braille conversion with proper formatting

The system should handle this text properly, applying correct Braille formatting rules including 40-character line limits and proper paragraph indentation."""

        print(f"📝 Sample text: {len(sample_text)} characters")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(sample_text)
            temp_path = temp_file.name
        
        print(f"💾 Temporary file: {temp_path}")
        
        # Test DocumentProcessingService
        print("\n🔧 Testing DocumentProcessingService...")
        from app.services import DocumentProcessingService
        
        processor = DocumentProcessingService()
        print("✅ DocumentProcessingService initialized")
        
        # Run pipeline
        print("\n🚀 Running full pipeline...")
        result = processor.process_document_full_pipeline(
            file_path=temp_path,
            file_type='txt',
            optimize_text=True,
            braille_grade=2
        )
        
        # Clean up
        os.unlink(temp_path)
        
        # Display results
        print(f"\n📊 Pipeline Results:")
        print(f"Status: {result.get('status')}")
        print(f"Steps completed: {result.get('steps_completed', [])}")
        print(f"Errors: {result.get('errors', [])}")
        
        # Check each step
        if 'extracted_text' in result:
            print(f"\n📄 Extracted text: {len(result['extracted_text'])} chars")
            print(f"Preview: {result['extracted_text'][:100]}...")
        
        if 'optimized_text' in result:
            print(f"\n🤖 Optimized text: {len(result['optimized_text'])} chars")
            print(f"Method: {result.get('optimization_method', 'unknown')}")
            print(f"Preview: {result['optimized_text'][:100]}...")
        
        if 'braille_result' in result:
            braille = result['braille_result']
            print(f"\n⠿ Braille conversion:")
            print(f"Status: {braille.get('status')}")
            print(f"Grade: {braille.get('grade')}")
            
            if braille.get('status') == 'success':
                print(f"Braille text length: {len(braille.get('braille_text', ''))}")
                print(f"Pagination: {braille.get('pagination', {})}")
                print(f"Braille preview: {braille.get('braille_text', '')[:50]}...")
            else:
                print(f"❌ Braille error: {braille.get('error')}")
        
        # Test individual Braille service
        print(f"\n🔍 Testing BrailleConversionService directly...")
        from app.services import BrailleConversionService
        
        braille_service = BrailleConversionService()
        direct_result = braille_service.convert_to_braille("Hello World! This is a test.", grade=2)
        
        print(f"Direct conversion status: {direct_result.get('status')}")
        if direct_result.get('status') == 'success':
            print(f"Direct Braille: {direct_result.get('braille_text', '')}")
        else:
            print(f"Direct error: {direct_result.get('error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_full_pipeline()
