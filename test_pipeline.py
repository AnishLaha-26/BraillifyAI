#!/usr/bin/env python3
"""
Test script for BraillifyAI complete pipeline
Tests the 5-step document processing workflow
"""

import os
import sys
import tempfile
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_text_pipeline():
    """Test the pipeline with simple text input"""
    print("🧪 Testing BraillifyAI Pipeline")
    print("=" * 50)
    
    try:
        from app.services import DocumentProcessingService
        
        # Initialize the service
        processor = DocumentProcessingService()
        print("✅ DocumentProcessingService initialized")
        
        # Create sample text
        sample_text = """Welcome to BraillifyAI Testing

This is a sample document that will be processed through our complete pipeline. The text contains multiple paragraphs and demonstrates various formatting scenarios.

Key Features:
- Text extraction and preprocessing
- AI-powered text optimization 
- Braille conversion with proper formatting
- PDF generation for embossing

The system should handle this text properly, applying correct Braille formatting rules including 40-character line limits and proper paragraph indentation.

This test validates that all 5 steps work correctly together."""

        print(f"📝 Sample text created: {len(sample_text)} characters")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(sample_text)
            temp_path = temp_file.name
        print(f"💾 Temporary file created: {temp_path}")
        
        # Run the complete pipeline
        print("\n🚀 Starting pipeline processing...")
        result = processor.process_document_full_pipeline(
            file_path=temp_path,
            file_type='txt',
            optimize_text=True,
            braille_grade=2
        )
        
        # Clean up temp file
        os.unlink(temp_path)
        print(f"🗑️ Cleaned up temporary file")
        
        # Display results
        print(f"\n📊 Pipeline Results:")
        print(f"Status: {result['status']}")
        print(f"Steps completed: {result.get('steps_completed', [])}")
        
        if result.get('errors'):
            print(f"⚠️ Errors encountered: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  - {error}")
        
        # Show extracted text sample
        if 'extracted_text' in result:
            extracted = result['extracted_text']
            print(f"\n📄 Extracted text: {len(extracted)} chars")
            print(f"Preview: {extracted[:100]}...")
        
        # Show optimized text sample
        if 'optimized_text' in result:
            optimized = result['optimized_text']
            print(f"\n🤖 Optimized text: {len(optimized)} chars")
            print(f"Method: {result.get('optimization_method', 'unknown')}")
            print(f"Preview: {optimized[:100]}...")
        
        # Show Braille results
        if 'braille_result' in result:
            braille = result['braille_result']
            if braille.get('conversion_successful'):
                print(f"\n⠿ Braille conversion successful!")
                print(f"Pages: {braille.get('page_count', 0)}")
                print(f"Grade: {braille.get('grade', 'unknown')}")
                print(f"Unicode sample: {braille.get('braille_text', '')[:50]}...")
                print(f"ASCII sample: {braille.get('braille_ascii', '')[:50]}...")
            else:
                print(f"\n❌ Braille conversion failed: {braille.get('error_message', 'Unknown')}")
        
        # Show PDF results
        if 'pdf_result' in result:
            pdf = result['pdf_result']
            if pdf.get('success'):
                print(f"\n📄 PDF generation successful!")
                print(f"Output path: {pdf.get('output_path', 'unknown')}")
                print(f"File size: {pdf.get('file_size_bytes', 0)} bytes")
            else:
                print(f"\n❌ PDF generation failed: {pdf.get('error', 'Unknown')}")
        
        if 'preview_pdf' in result:
            preview = result['preview_pdf']
            if preview.get('success'):
                print(f"📋 Preview PDF: {preview.get('output_path', 'unknown')}")
        
        # Overall assessment
        total_steps = 5  # extraction, optimization, braille, pdf, preview
        completed_steps = len(result.get('steps_completed', []))
        success_rate = (completed_steps / total_steps) * 100
        
        print(f"\n🎯 Pipeline Assessment:")
        print(f"Completion rate: {completed_steps}/{total_steps} steps ({success_rate:.1f}%)")
        
        if result['status'] == 'completed':
            print("🎉 PIPELINE TEST PASSED! All steps completed successfully.")
        elif result['status'] in ['partial_success', 'success']:
            print("⚠️ PIPELINE TEST PARTIALLY PASSED with some issues.")
        else:
            print("❌ PIPELINE TEST FAILED.")
        
        return result
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the BraillifyAI root directory")
        return None
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_individual_services():
    """Test individual services separately"""
    print("\n🔧 Testing Individual Services")
    print("=" * 50)
    
    try:
        # Test TextOptimizationService
        from app.services import TextOptimizationService
        optimizer = TextOptimizationService()
        
        sample_text = "This is a test. Social media links like @username and URLs like https://example.com should be filtered out."
        result = optimizer.optimize_extracted_text(sample_text, "general")
        print(f"✅ TextOptimizationService: {result['status']}")
        
        # Test BrailleConversionService
        from app.services import BrailleConversionService
        braille_service = BrailleConversionService()
        
        formatted_text = "  This is properly formatted text for Braille.\n  Each line should be under 40 characters."
        braille_result = braille_service.convert_to_braille(formatted_text, grade=2)
        print(f"✅ BrailleConversionService: {'success' if braille_result['conversion_successful'] else 'failed'}")
        
        # Test BraillePDFGeneratorService
        from app.services import BraillePDFGeneratorService
        pdf_service = BraillePDFGeneratorService()
        
        if braille_result['conversion_successful']:
            pdf_data = braille_service.prepare_for_pdf(braille_result, "Test Document")
            if pdf_data['ready']:
                print("✅ BraillePDFGeneratorService: ready for PDF generation")
            else:
                print("❌ BraillePDFGeneratorService: PDF preparation failed")
        
        print("🎉 Individual service tests completed!")
        
    except Exception as e:
        print(f"❌ Individual service test failed: {e}")

if __name__ == "__main__":
    print(f"🕐 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run the complete pipeline test
    pipeline_result = test_text_pipeline()
    
    # Run individual service tests
    test_individual_services()
    
    print(f"\n🕐 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if pipeline_result and pipeline_result['status'] in ['completed', 'success', 'partial_success']:
        print("✅ Overall test result: PASSED")
        sys.exit(0)
    else:
        print("❌ Overall test result: FAILED")
        sys.exit(1)
