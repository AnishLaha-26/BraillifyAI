#!/usr/bin/env python3
"""
Test script for Braille API
"""

import requests
import json

def test_braille_api():
    """Test the Braille API server"""
    
    print("🧪 Testing Braille API Server")
    print("=" * 50)
    
    # Test health endpoint
    try:
        print("1. Testing health endpoint...")
        response = requests.get("http://localhost:5001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        print("💡 Make sure to start the API server first: python braille_api.py")
        return False
    
    # Test conversion endpoint
    try:
        print("\n2. Testing Braille conversion...")
        
        test_text = "Hello world! This is a test of the Braille system."
        payload = {
            "text": test_text,
            "grade": 2
        }
        
        response = requests.post("http://localhost:5001/convert", json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('status') == 'success':
                print("✅ Braille conversion successful!")
                print(f"   Original: {test_text}")
                print(f"   Braille:  {result.get('braille_text', '')}")
                print(f"   Grade:    {result.get('grade')}")
                
                pagination = result.get('pagination', {})
                print(f"   Pages:    {pagination.get('total_pages', 0)}")
                print(f"   Lines:    {pagination.get('total_lines', 0)}")
                
                # Check if we got actual Unicode Braille
                braille_text = result.get('braille_text', '')
                if any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in braille_text):
                    print("✅ Unicode Braille dots detected!")
                else:
                    print("⚠️  No Unicode Braille dots found")
                
                return True
            else:
                print(f"❌ Conversion failed: {result.get('error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Conversion test error: {e}")
        return False

def test_sample_texts():
    """Test various sample texts"""
    
    print("\n3. Testing various text samples...")
    
    samples = [
        "The quick brown fox jumps over the lazy dog.",
        "Numbers: 1234567890",
        "Punctuation: Hello, world! How are you?",
        "Contractions: and for the with of",
        "  This is an indented paragraph with proper formatting."
    ]
    
    for i, sample in enumerate(samples, 1):
        try:
            payload = {"text": sample, "grade": 2}
            response = requests.post("http://localhost:5001/convert", json=payload, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    braille = result.get('braille_text', '')
                    print(f"   Sample {i}: ✅ ({len(braille)} chars)")
                    print(f"      Text:    {sample}")
                    print(f"      Braille: {braille}")
                else:
                    print(f"   Sample {i}: ❌ {result.get('error')}")
            else:
                print(f"   Sample {i}: ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   Sample {i}: ❌ {e}")

if __name__ == "__main__":
    print("🔤 Braille API Test Suite")
    print("Make sure the API server is running: python braille_api.py")
    print()
    
    success = test_braille_api()
    
    if success:
        test_sample_texts()
        print("\n🎉 All tests completed!")
        print("💡 You can now use the API in your main application")
    else:
        print("\n❌ Tests failed. Please check the API server.")
        print("💡 Start the API server with: python braille_api.py")
