#!/usr/bin/env python3
"""
Braille Conversion API Server
Provides reliable text-to-Braille conversion with Unicode dot patterns
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import math

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

class BrailleConverter:
    """Manual Braille converter with Unicode dot patterns"""
    
    def __init__(self):
        # Braille page specifications
        self.CHARS_PER_LINE = 40
        self.LINES_PER_PAGE = 25
        self.CHARS_PER_PAGE = self.CHARS_PER_LINE * self.LINES_PER_PAGE
        
        # Complete Braille character mapping (Grade 1 + common Grade 2 contractions)
        self.braille_map = {
            # Letters (a-z)
            'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑', 'f': '⠋', 'g': '⠛', 'h': '⠓',
            'i': '⠊', 'j': '⠚', 'k': '⠅', 'l': '⠇', 'm': '⠍', 'n': '⠝', 'o': '⠕', 'p': '⠏',
            'q': '⠟', 'r': '⠗', 's': '⠎', 't': '⠞', 'u': '⠥', 'v': '⠧', 'w': '⠺', 'x': '⠭',
            'y': '⠽', 'z': '⠵',
            
            # Numbers (with number prefix ⠼)
            '1': '⠼⠁', '2': '⠼⠃', '3': '⠼⠉', '4': '⠼⠙', '5': '⠼⠑',
            '6': '⠼⠋', '7': '⠼⠛', '8': '⠼⠓', '9': '⠼⠊', '0': '⠼⠚',
            
            # Punctuation
            '.': '⠲', ',': '⠂', '?': '⠦', '!': '⠖', ';': '⠆', ':': '⠒',
            '-': '⠤', '(': '⠐⠣', ')': '⠐⠜', '"': '⠐⠦', "'": '⠄',
            '/': '⠌', '\\': '⠡', '@': '⠈⠁', '#': '⠼', '$': '⠈⠎',
            '%': '⠨⠴', '&': '⠈⠯', '*': '⠈⠔', '+': '⠬', '=': '⠨⠅',
            '<': '⠈⠣', '>': '⠈⠜', '[': '⠪', ']': '⠻', '{': '⠸⠣', '}': '⠸⠜',
            
            # Common Grade 2 contractions
            'and': '⠯', 'for': '⠿', 'of': '⠷', 'the': '⠮', 'with': '⠾',
            'ch': '⠡', 'gh': '⠣', 'sh': '⠩', 'th': '⠹', 'wh': '⠱', 'ed': '⠫',
            'er': '⠻', 'ou': '⠳', 'ow': '⠪', 'st': '⠌', 'ing': '⠬',
            'ar': '⠜', 'en': '⠢', 'in': '⠔',
            
            # Special characters
            ' ': ' ', '\n': '\n', '\t': '⠀⠀'  # Tab as two Braille spaces
        }
        
        # Grade 2 word contractions (whole words only)
        self.word_contractions = {
            'about': '⠁⠃', 'above': '⠁⠃⠧', 'according': '⠁⠉⠉', 'across': '⠁⠉⠗',
            'after': '⠁⠋', 'afternoon': '⠁⠋⠝', 'afterward': '⠁⠋⠺', 'again': '⠁⠛',
            'against': '⠁⠛⠌', 'almost': '⠁⠇⠍', 'already': '⠁⠇⠗', 'also': '⠁⠇',
            'although': '⠁⠇⠹', 'altogether': '⠁⠇⠞', 'always': '⠁⠇⠺', 'because': '⠃⠉',
            'before': '⠃⠋', 'behind': '⠃⠓', 'below': '⠃⠇', 'beneath': '⠃⠢',
            'beside': '⠃⠎', 'between': '⠃⠞', 'beyond': '⠃⠽', 'blind': '⠃⠇',
            'braille': '⠃⠗⠇', 'children': '⠡⠝', 'conceive': '⠒⠉⠧', 'could': '⠉⠙',
            'deceive': '⠙⠉⠧', 'declare': '⠙⠉⠇', 'either': '⠑⠊', 'first': '⠋⠌',
            'friend': '⠋⠗', 'good': '⠛⠙', 'great': '⠛⠗⠞', 'herself': '⠓⠻⠋',
            'himself': '⠓⠍⠋', 'immediate': '⠊⠍⠍', 'its': '⠭', 'itself': '⠭⠋',
            'letter': '⠇⠗', 'little': '⠇⠇', 'much': '⠍⠡', 'must': '⠍⠌',
            'myself': '⠍⠽⠋', 'necessary': '⠝⠑⠉', 'neither': '⠝⠑⠊', 'oneself': '⠕⠝⠋',
            'ourselves': '⠳⠗⠧⠎', 'paid': '⠏⠙', 'perceive': '⠏⠻⠉⠧', 'perhaps': '⠏⠻⠓',
            'quick': '⠟⠅', 'receive': '⠗⠉⠧', 'rejoice': '⠗⠚⠉', 'said': '⠎⠙',
            'should': '⠩⠙', 'such': '⠎⠡', 'themselves': '⠹⠍⠧⠎', 'through': '⠹⠗⠳',
            'today': '⠞⠙', 'together': '⠞⠛⠗', 'tomorrow': '⠞⠍', 'tonight': '⠞⠝',
            'would': '⠺⠙', 'your': '⠽⠗', 'yourself': '⠽⠗⠋', 'yourselves': '⠽⠗⠧⠎'
        }
    
    def convert_text_to_braille(self, text: str, grade: int = 2) -> str:
        """Convert text to Braille with proper formatting"""
        if not text:
            return ""
        
        # Format text for Braille standards
        formatted_text = self._format_for_braille(text)
        
        # Convert to Braille
        if grade == 2:
            braille_text = self._convert_grade2(formatted_text)
        else:
            braille_text = self._convert_grade1(formatted_text)
        
        return braille_text
    
    def _format_for_braille(self, text: str) -> str:
        """Format text according to Braille standards"""
        # Split into lines and process each
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                formatted_lines.append('')
                continue
            
            # Check for titles (all caps, short lines)
            if line.isupper() and len(line) <= 50:
                formatted_lines.append(line)
                continue
            
            # Check for list items
            if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+[\.)]\s+', line):
                formatted_lines.append(line)
                continue
            
            # Regular paragraph - add indent if not already present
            if not line.startswith('  '):
                line = '  ' + line
            
            # Wrap to 40 characters
            wrapped_lines = self._wrap_line(line, 40)
            formatted_lines.extend(wrapped_lines)
        
        return '\n'.join(formatted_lines)
    
    def _wrap_line(self, line: str, max_length: int) -> list:
        """Wrap a line to maximum length"""
        if len(line) <= max_length:
            return [line]
        
        words = line.split()
        wrapped_lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            # Check if adding this word would exceed the limit
            if current_line and current_length + 1 + word_length > max_length:
                # Save current line and start new one
                wrapped_lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
            else:
                # Add word to current line
                if current_line:
                    current_length += 1 + word_length  # +1 for space
                else:
                    current_length = word_length
                current_line.append(word)
        
        # Add the last line
        if current_line:
            wrapped_lines.append(' '.join(current_line))
        
        return wrapped_lines
    
    def _convert_grade1(self, text: str) -> str:
        """Convert to Grade 1 Braille (letter by letter)"""
        result = []
        
        for char in text.lower():
            if char in self.braille_map:
                result.append(self.braille_map[char])
            else:
                # Unknown character - use a placeholder
                result.append('⠿')
        
        return ''.join(result)
    
    def _convert_grade2(self, text: str) -> str:
        """Convert to Grade 2 Braille (with contractions)"""
        # Split into words while preserving spacing
        words = re.split(r'(\s+)', text.lower())
        result = []
        
        for word in words:
            if word.isspace():
                # Preserve whitespace
                result.append(word)
            elif word in self.word_contractions:
                # Use word contraction
                result.append(self.word_contractions[word])
            else:
                # Convert letter by letter, checking for letter contractions
                converted_word = self._convert_word_with_contractions(word)
                result.append(converted_word)
        
        return ''.join(result)
    
    def _convert_word_with_contractions(self, word: str) -> str:
        """Convert a word with letter-level contractions"""
        result = []
        i = 0
        
        while i < len(word):
            # Check for 2-letter contractions first
            if i < len(word) - 1:
                two_char = word[i:i+2]
                if two_char in self.braille_map:
                    result.append(self.braille_map[two_char])
                    i += 2
                    continue
            
            # Single character
            char = word[i]
            if char in self.braille_map:
                result.append(self.braille_map[char])
            else:
                result.append('⠿')  # Unknown character placeholder
            i += 1
        
        return ''.join(result)
    
    def calculate_pagination(self, braille_text: str) -> dict:
        """Calculate pagination for Braille text"""
        lines = braille_text.split('\n')
        total_chars = len(braille_text.replace('\n', ''))
        
        # Break text into pages
        pages = []
        current_page = []
        current_page_chars = 0
        current_page_lines = 0
        
        for line in lines:
            line_length = len(line)
            lines_needed = math.ceil(line_length / self.CHARS_PER_LINE) if line_length > 0 else 1
            
            # Check if line fits on current page
            if (current_page_lines + lines_needed <= self.LINES_PER_PAGE and 
                current_page_chars + line_length <= self.CHARS_PER_PAGE):
                current_page.append(line)
                current_page_chars += line_length
                current_page_lines += lines_needed
            else:
                # Start new page
                if current_page:
                    pages.append({
                        "page_number": len(pages) + 1,
                        "lines": current_page.copy(),
                        "char_count": current_page_chars,
                        "line_count": current_page_lines
                    })
                
                current_page = [line]
                current_page_chars = line_length
                current_page_lines = lines_needed
        
        # Add last page
        if current_page:
            pages.append({
                "page_number": len(pages) + 1,
                "lines": current_page,
                "char_count": current_page_chars,
                "line_count": current_page_lines
            })
        
        return {
            "total_pages": len(pages),
            "total_characters": total_chars,
            "total_lines": len(lines),
            "chars_per_page": self.CHARS_PER_PAGE,
            "lines_per_page": self.LINES_PER_PAGE,
            "chars_per_line": self.CHARS_PER_LINE,
            "pages": pages
        }

# Initialize converter
braille_converter = BrailleConverter()

@app.route('/convert', methods=['POST'])
def convert_to_braille():
    """Convert text to Braille"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text']
        grade = data.get('grade', 2)  # Default to Grade 2
        
        if not text.strip():
            return jsonify({'error': 'Empty text provided'}), 400
        
        # Convert to Braille
        braille_text = braille_converter.convert_text_to_braille(text, grade)
        
        # Calculate pagination
        pagination = braille_converter.calculate_pagination(braille_text)
        
        return jsonify({
            'status': 'success',
            'braille_text': braille_text,
            'original_text': text,
            'grade': grade,
            'pagination': pagination
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Braille Conversion API',
        'version': '1.0.0'
    })

@app.route('/test', methods=['GET'])
def test_conversion():
    """Test endpoint with sample text"""
    sample_text = "Hello world! This is a test of the Braille conversion system."
    
    braille_text = braille_converter.convert_text_to_braille(sample_text, grade=2)
    pagination = braille_converter.calculate_pagination(braille_text)
    
    return jsonify({
        'status': 'success',
        'sample_text': sample_text,
        'braille_text': braille_text,
        'pagination': pagination
    })

if __name__ == '__main__':
    print("🔤 Starting Braille Conversion API Server")
    print("📍 Available endpoints:")
    print("   POST /convert - Convert text to Braille")
    print("   GET  /health  - Health check")
    print("   GET  /test    - Test conversion")
    print("🚀 Server starting on http://localhost:5001")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
