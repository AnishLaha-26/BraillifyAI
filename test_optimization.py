#!/usr/bin/env python3
"""
Test script for BraillifyAI text optimization
"""

from fitz import g
from app.services import TextOptimizationService, BrailleConversionService

def test_optimization():
    # Sample messy text (like OCR output)
    sample_text = """
    PERSONAL     STATEMENT
    
    
    My name is John    Doe and I am applying to
    
    your university because    I have always been 
    passionate about learning.    Growing up in a 
    small    town, I learned the
    value of hard work.
    
    
    In high school,  I    participated in many 
    activities including:
    - Math Club
    - Science Fair
    - Volunteer work
    
    
    I believe that    education is the key to
    success.
    """
    
    # Initialize services
    optimizer = TextOptimizationService()
    braille_service = BrailleConversionService()
    
    print("🔤 ORIGINAL TEXT:")
    print("-" * 50)
    print(sample_text)
    print()
    
    # Optimize text
    print("🤖 OPTIMIZING TEXT...")
    result = optimizer.optimize_extracted_text(sample_text, "personal_statement")
    
    print("✅ OPTIMIZED TEXT:")
    print("-" * 50)
    print(result["optimized_text"])
    print()
    
    print("📊 OPTIMIZATION STATS:")
    print(f"- Original length: {result['original_length']} chars")
    print(f"- Optimized length: {result['optimized_length']} chars")
    print(f"- Model used: {result['model_used']}")
    print(f"- Improvements: {result['improvement_notes']}")
    print()
    
    # Convert to braille
    print("⠠⠃⠗⠁⠊⠇⠇⠑ CONVERTING TO BRAILLE...")
    braille_result = braille_service.convert_to_braille(result["optimized_text"])
    
    if braille_result["status"] == "success":
        print("✅ BRAILLE CONVERSION:")
        print("-" * 50)
        print(braille_result["braille_text"][:200] + "..." if len(braille_result["braille_text"]) > 200 else braille_result["braille_text"])
        print()
        print("📄 PAGINATION INFO:")
        print(f"- Total pages: {braille_result['pagination']['total_pages']}")
        print(f"- Characters per page: {braille_result['pagination']['chars_per_page']}")
        print(f"- Lines per page: {braille_result['pagination']['lines_per_page']}")
    else:
        print("❌ Braille conversion failed:", braille_result.get("error", "Unknown error"))

if __name__ == "__main__":
    test_optimization()


