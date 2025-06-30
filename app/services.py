import os
import re
import math
import requests
from io import BytesIO
from PIL import Image
import pytesseract
from pdf2image import convert_from_path, convert_from_bytes
import louis  # Requires liblouis system library
from typing import List, Dict, Tuple, Optional
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextOptimizationService:
    """Service for AI-powered text optimization and restructuring using Hack Club AI"""
    
    def __init__(self):
        # Hack Club AI endpoint - no API key needed!
        self.api_url = "https://ai.hackclub.com/chat/completions"
        self.model_url = "https://ai.hackclub.com/model"
        
        # Braille formatting constants
        self.MAX_LINE_LENGTH = 40
        self.PARAGRAPH_INDENT = "  "  # 2 spaces
        self.LINES_PER_PAGE = 25
    
    def get_current_model(self) -> str:
        """Get the current model being used by Hack Club AI"""
        try:
            response = requests.get(self.model_url)
            if response.status_code == 200:
                return response.text.strip()
            else:
                return "unknown"
        except Exception as e:
            logger.error(f"Error getting current model: {e}")
            return "unknown"
    
    def optimize_extracted_text(self, text: str, document_type: str = "general") -> Dict[str, str]:
        """
        Complete text optimization pipeline following Braille conversion checklist
        
        Steps:
        1. Text Extraction & Preprocessing
        2. AI Formatting (with fallback)
        3. Line Wrapping for Braille
        4. Final validation
        """
        logger.info(f"Starting text optimization pipeline for {len(text)} characters")
        
        # Step 1: Text Extraction & Preprocessing
        preprocessed_text = self._preprocess_text(text)
        logger.info(f"Preprocessing complete: {len(text)} -> {len(preprocessed_text)} characters")
        
        # Step 2: AI Formatting (Optional but Recommended)
        ai_formatted_text = self._ai_format_text(preprocessed_text, document_type)
        
        # Step 3: Line Wrapping for Braille
        braille_ready_text = self._wrap_for_braille(ai_formatted_text)
        
        # Step 4: Final validation
        validated_text = self._validate_braille_format(braille_ready_text)
        
        logger.info(f"Optimization pipeline complete. Final length: {len(validated_text)} characters")
        
        return {
            "optimized_text": validated_text,
            "original_length": len(text),
            "optimized_length": len(validated_text),
            "preprocessing_applied": True,
            "ai_optimization": ai_formatted_text != preprocessed_text,
            "line_wrapping_applied": True,
            "validation_passed": self._check_line_lengths(validated_text),
            "model_used": self.get_current_model() if ai_formatted_text != preprocessed_text else "fallback"
        }
    
    def _preprocess_text(self, text: str) -> str:
        """
        📤 Step 1: Text Extraction & Preprocessing
        - Strip out junk content (headers, page numbers, footers)
        - Remove unnecessary symbols
        - Normalize punctuation and spacing
        """
        logger.info("Step 1: Preprocessing text")
        
        # Remove URLs and web links
        text = re.sub(r'https?://[^\s]+', '', text)
        text = re.sub(r'www\.[^\s]+', '', text)
        
        # Remove social media handles and hashtags
        text = re.sub(r'@[A-Za-z0-9_]+', '', text)
        text = re.sub(r'#[A-Za-z0-9_]+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        # Remove page numbers and common headers/footers
        text = re.sub(r'Page \d+\s*(?:of\s*\d+)?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)  # Standalone page numbers
        text = re.sub(r'Copyright.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'All rights reserved.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
        
        # Remove unnecessary symbols and formatting artifacts
        text = re.sub(r'[=]{3,}', '', text)  # Remove lines of equals signs
        text = re.sub(r'[-]{3,}', '', text)  # Remove lines of dashes
        text = re.sub(r'[_]{3,}', '', text)  # Remove lines of underscores
        text = re.sub(r'[•·∙◦‣⁃]', '-', text)  # Normalize bullet points
        text = re.sub(r'["""]', '"', text)  # Normalize quotes
        text = re.sub(r'[``]', "'", text)  # Normalize apostrophes
        text = re.sub(r'…', '...', text)  # Normalize ellipsis
    
        # Removed emojis and special Unicode characters
        text = re.sub(r'[^\x00-\x7F\u0080-\u00FF]+', ' ', text)
        # Normalize punctuation and spacing
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([,.!?;:])(?!\s|$)', r'\1 ', text)  # Add space after punctuation
        text = re.sub(r'([.!?])\s*\n', r'\1\n\n', text)  # Double newline after sentences
        
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double newline
        text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)  # Remove leading whitespace
        text = re.sub(r'\s+$', '', text, flags=re.MULTILINE)  # Remove trailing whitespace
        
        return text.strip()
    
    def _ai_format_text(self, text: str, document_type: str) -> str:
        """
        🧠 Step 2: AI Formatting with specific Braille rules
        """
        logger.info("Step 2: AI formatting with Braille rules")
        
        try:
            # Handle large texts by chunking
            if len(text) > 3000:
                return self._ai_format_large_text(text, document_type)
            
            # Create focused prompt for Braille formatting
            prompt = f"""
Format this text for Braille conversion following these EXACT rules:

1. Titles must be in ALL CAPS with blank lines before and after
2. Start each paragraph with exactly 2 spaces (but don't worry about line length)
3. Put blank lines between sections
4. Format lists with dash (-) for bullets
5. Remove any remaining URLs or metadata
6. Keep paragraphs as continuous text (line wrapping will be handled separately)

TEXT TO FORMAT:
{text}

IMPORTANT: Return ONLY the formatted text. No explanations or markdown.
"""
            
            payload = {
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a Braille formatting specialist. Format text exactly according to Braille standards."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.3  # Lower temperature for more consistent formatting
            }
            
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                formatted_text = response_data['choices'][0]['message']['content'].strip()
                logger.info("AI formatting successful")
                return formatted_text
            else:
                logger.warning(f"AI API error: {response.status_code}")
                return self._fallback_format_text(text)
                
        except Exception as e:
            logger.error(f"Error in AI formatting: {e}")
            return self._fallback_format_text(text)
    
    def _ai_format_large_text(self, text: str, document_type: str) -> str:
        """Handle large texts by processing in chunks"""
        chunk_size = 2500
        chunks = []
        
        # Split into semantic chunks
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Process each chunk
        formatted_chunks = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            formatted_chunk = self._ai_format_text(chunk, document_type)
            formatted_chunks.append(formatted_chunk)
        
        return '\n\n'.join(formatted_chunks)
    
    def _fallback_format_text(self, text: str) -> str:
        """Fallback formatting when AI is unavailable"""
        logger.info("Using fallback formatting")
        
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Detect and format titles
            if self._is_likely_title(para):
                formatted_paragraphs.append(f"\n{para.upper()}\n")
            else:
                # Regular paragraph - will be wrapped in next step
                formatted_paragraphs.append(para)
        
        return '\n\n'.join(formatted_paragraphs)
    
    def _is_likely_title(self, text: str) -> bool:
        """Detect if text is likely a title or heading"""
        text = text.strip()
        
        # Check various title indicators
        if len(text) < 80 and not text.endswith('.'):
            # Short text without ending punctuation
            if text.isupper() or text.istitle():
                return True
            # Common title keywords
            title_keywords = ['chapter', 'section', 'introduction', 'conclusion', 
                            'abstract', 'summary', 'contents', 'preface', 'appendix']
            if any(keyword in text.lower() for keyword in title_keywords):
                return True
            # Numbered sections
            if re.match(r'^\d+\.?\s+\w+', text) or re.match(r'^[IVX]+\.?\s+\w+', text):
                return True
        
        return False
    
    def _wrap_for_braille(self, text: str) -> str:
        """
        🧾 Step 3: Line Wrapping for Braille
        - Wrap lines to max 40 characters
        - Add 2-space indent to paragraphs
        - Handle lists properly
        - Reconstruct broken paragraphs (words on individual lines)
        """
        logger.info("Step 3: Line wrapping for Braille")
        
        lines = text.split('\n')
        wrapped_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Empty lines pass through
            if not line:
                wrapped_lines.append('')
                i += 1
                continue
            
            # Check if this is a title (all caps)
            if line.isupper():
                if len(line) <= self.MAX_LINE_LENGTH:
                    wrapped_lines.append(line)
                else:
                    wrapped_lines.extend(self._wrap_text(line, indent=''))
                i += 1
                continue
            
            # Check if this is a list item
            if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+\.\s+', line):
                if len(line) <= self.MAX_LINE_LENGTH:
                    wrapped_lines.append(line)
                else:
                    wrapped_lines.extend(self._wrap_list_item(line))
                i += 1
                continue
            
            # Check if this looks like a broken paragraph (short lines that should be combined)
            if len(line) <= 20 and not line.startswith('  '):  # Short line, not already indented
                # Look ahead to see if we have multiple short lines that should be combined
                paragraph_lines = [line]
                j = i + 1
                
                while j < len(lines):
                    next_line = lines[j].rstrip()
                    
                    # Stop if we hit an empty line, title, or list item
                    if (not next_line or 
                        next_line.isupper() or 
                        re.match(r'^[-•*]\s+', next_line) or 
                        re.match(r'^\d+[\.\)]\s+', next_line) or
                        next_line.startswith('  ')):
                        break
                    
                    # If it's another short line, add it to the paragraph
                    if len(next_line) <= 20:
                        paragraph_lines.append(next_line)
                        j += 1
                    else:
                        # If we hit a long line, include it and stop
                        paragraph_lines.append(next_line)
                        j += 1
                        break
                
                # Reconstruct the paragraph
                reconstructed_paragraph = ' '.join(paragraph_lines)
                
                # Wrap the reconstructed paragraph
                wrapped_lines.extend(self._wrap_text(reconstructed_paragraph, indent=self.PARAGRAPH_INDENT))
                
                # Skip the lines we've processed
                i = j
                continue
            
            # Line is already properly formatted or long enough
            if len(line) <= self.MAX_LINE_LENGTH:
                # If it's not indented, add paragraph indent
                if not line.startswith('  '):
                    wrapped_lines.append(self.PARAGRAPH_INDENT + line)
                else:
                    wrapped_lines.append(line)
            else:
                # Line is too long, needs wrapping
                wrapped_lines.extend(self._wrap_text(line, indent=self.PARAGRAPH_INDENT))
            
            i += 1
        
        # Clean up multiple blank lines
        result = []
        prev_blank = False
        for line in wrapped_lines:
            if line == '':
                if not prev_blank:
                    result.append(line)
                prev_blank = True
            else:
                result.append(line)
                prev_blank = False
        
        return '\n'.join(result)
    
    def _wrap_text(self, text: str, indent: str = '') -> List[str]:
        """Wrap text to fit within line length limit"""
        max_length = self.MAX_LINE_LENGTH - len(indent)
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            # Check if adding this word would exceed the limit
            if current_line and current_length + 1 + word_length > max_length:
                # Save current line and start new one
                lines.append(indent + ' '.join(current_line))
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
            lines.append(indent + ' '.join(current_line))
        
        return lines
    
    def _wrap_list_item(self, text: str) -> List[str]:
        """Wrap list items with hanging indent"""
        # Extract the list marker
        match = re.match(r'^([-•*]\s+|\d+[\.\)]\s+)', text)
        if not match:
            return self._wrap_text(text)
        
        marker = match.group(1)
        content = text[len(marker):]
        
        # First line includes the marker
        first_line_indent = ''
        first_line_max = self.MAX_LINE_LENGTH - len(marker)
        
        # Subsequent lines have hanging indent
        hanging_indent = ' ' * len(marker)
        
        words = content.split()
        lines = []
        current_line = bullet + line
        
        while len(current_line) > self.MAX_LINE_LENGTH:
            # Find last space before line break
            wrap_pos = current_line.rfind(' ', len(bullet), self.MAX_LINE_LENGTH + 1)
            if wrap_pos <= len(bullet):  # No space found in first line
                wrap_pos = current_line.find(' ', len(bullet) + 1)
                if wrap_pos == -1:  # No space at all
                    wrap_pos = min(len(current_line), self.MAX_LINE_LENGTH)
            
            lines.append(current_line[:wrap_pos].rstrip())
            current_line = ' ' * (len(bullet) + 2) + current_line[wrap_pos:].lstrip()
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _validate_braille_format(self, text: str) -> str:
        """
        Step 4: Final validation
        - Confirm every line ≤ 40 chars
        - Fix any formatting issues
        """
        logger.info("Step 4: Validating Braille format")
    
        lines = text.split('\n')
        validated_lines = []
        issues_fixed = 0
        
        for i, line in enumerate(lines):
            if len(line) > self.MAX_LINE_LENGTH:
                logger.warning(f"Line {i+1} exceeds {self.MAX_LINE_LENGTH} chars: {len(line)}")
                # Emergency line breaking
                while len(line) > self.MAX_LINE_LENGTH:
                    break_point = line[:self.MAX_LINE_LENGTH].rfind(' ')
                    if break_point == -1:
                        break_point = self.MAX_LINE_LENGTH
                    validated_lines.append(line[:break_point])
                    line = line[break_point:].lstrip()
                    issues_fixed += 1
                if line:
                    validated_lines.append(line)
            else:
                validated_lines.append(line)
        
        if issues_fixed > 0:
            logger.warning(f"Fixed {issues_fixed} lines that exceeded character limit")
        
        result = '\n'.join(validated_lines)
        
        # Final cleanup
        result = re.sub(r'\n{3,}', '\n\n', result)  # No more than 2 blank lines
        result = result.strip()
        
        return result
    
    def _check_line_lengths(self, text: str) -> bool:
        """Check if all lines are within the character limit"""
        lines = text.split('\n')
        for line in lines:
            if len(line) > self.MAX_LINE_LENGTH:
                return False
        return True

class OCRService:
    """Service for extracting text from images and scanned documents"""
    
    def __init__(self):
        # Configure Tesseract if needed
        # pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract'  # Adjust path as needed
        pass
    
    def extract_text_from_image(self, image_path: str) -> Dict[str, str]:
        """Extract text from image using OCR"""
        try:
            # Open and preprocess image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
           # Extract text using Tesseract
            extracted_text = pytesseract.image_to_string(image, lang='eng')
            
            # Get confidence scores
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "text": extracted_text.strip(),
                "confidence": round(avg_confidence, 2),
                "word_count": len(extracted_text.split()),
                "status": "success"
            }
            
        except Exception as e:
            return {
                "text": "",
                "confidence": 0,
                "word_count": 0,
                "status": "error",
                "error": str(e)
            }
    
    def extract_text_from_pdf_images(self, pdf_path: str) -> Dict[str, any]:
        """Extract text from scanned PDF using OCR"""
        try:
            # Convert PDF pages to images
            pages = convert_from_path(pdf_path, dpi=300)
            
            extracted_texts = []
            total_confidence = 0
            
            for i, page in enumerate(pages):
                # Extract text from each page
                page_text = pytesseract.image_to_string(page, lang='eng')
                
                # Get confidence for this page
                data = pytesseract.image_to_data(page, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                page_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                extracted_texts.append({
                    "page": i + 1,
                    "text": page_text.strip(),
                    "confidence": round(page_confidence, 2)
                })
                
                total_confidence += page_confidence
            
            # Combine all text
            full_text = "\n\n".join([page["text"] for page in extracted_texts if page["text"]])
            avg_confidence = total_confidence / len(pages) if pages else 0
            
            return {
                "text": full_text,
                "pages": extracted_texts,
                "total_pages": len(pages),
                "average_confidence": round(avg_confidence, 2),
                "word_count": len(full_text.split()),
                "status": "success"
            }
            
        except Exception as e:
            return {
                "text": "",
                "pages": [],
                "total_pages": 0,
                "average_confidence": 0,
                "word_count": 0,
                "status": "error",
                "error": str(e)
            }


class BrailleConversionService:
    """Service for converting text to braille and handling pagination"""
    
    def __init__(self):
        # Braille page specifications (standard US braille paper)
        self.BRAILLE_CHARS_PER_LINE = 40  # Standard braille line width
        self.BRAILLE_LINES_PER_PAGE = 25  # Standard braille page height
        self.CHARS_PER_PAGE = self.BRAILLE_CHARS_PER_LINE * self.BRAILLE_LINES_PER_PAGE
    
    def convert_to_braille(self, text: str, grade: int = 2) -> Dict[str, any]:
        """
        Convert text to braille using external Braille API
        
        Args:
            text: Text to convert
            grade: Braille grade (1 or 2)
            
        Returns:
            Dictionary with braille conversion results
        """
        try:
            import requests
            
            # Call external Braille API
            api_url = "http://localhost:5001/convert"
            payload = {
                "text": text,
                "grade": grade
            }
            
            print(f"DEBUG: Calling Braille API with text length: {len(text)}")
            
            response = requests.post(api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status') == 'success':
                    print(f"DEBUG: Braille API success - text length: {len(result.get('braille_text', ''))}")
                    return {
                        "braille_text": result.get('braille_text', ''),
                        "original_text": text,
                        "formatted_text": text,  # API handles formatting internally
                        "grade": grade,
                        "table_used": f"api-grade-{grade}",
                        "pagination": result.get('pagination', {}),
                        "status": "success"
                    }
                else:
                    print(f"DEBUG: Braille API error: {result.get('error')}")
                    return {
                        "braille_text": "",
                        "original_text": text,
                        "formatted_text": "",
                        "grade": grade,
                        "pagination": {},
                        "status": "error",
                        "error": f"API error: {result.get('error', 'Unknown error')}"
                    }
            else:
                print(f"DEBUG: Braille API HTTP error: {response.status_code}")
                return {
                    "braille_text": "",
                    "original_text": text,
                    "formatted_text": "",
                    "grade": grade,
                    "pagination": {},
                    "status": "error",
                    "error": f"API HTTP error: {response.status_code}"
                }
                
        except requests.exceptions.ConnectionError:
            print("DEBUG: Braille API connection failed - API server not running")
            return {
                "braille_text": "",
                "original_text": text,
                "formatted_text": "",
                "grade": grade,
                "pagination": {},
                "status": "error",
                "error": "Braille API server not available. Please start the Braille API server."
            }
        except Exception as e:
            print(f"DEBUG: Braille conversion error: {e}")
            return {
                "braille_text": "",
                "original_text": text,
                "formatted_text": "",
                "grade": grade,
                "pagination": {},
                "status": "error",
                "error": str(e)
            }
    
    def _format_for_braille(self, text: str) -> str:
        """
        Format text according to strict Braille standards before conversion.
        Implements precise Braille formatting rules with strict line length enforcement.
        """
        if not text or not text.strip():
            return text
            
        # Preserve original line breaks for better structure analysis
        lines = text.split('\n')
        formatted_lines = []
        
        # Track context for better formatting decisions
        in_list = False
        prev_line_was_blank = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Handle empty lines (paragraph breaks)
            if not line:
                if not prev_line_was_blank:  # Don't add multiple blank lines
                    formatted_lines.append('')
                    prev_line_was_blank = True
                continue
                
            # Check for list items (various bullet styles and numbers)
            is_list_item = (re.match(r'^\s*[-*•‣⁃]\s+', line) or  # Bullet points
                           re.match(r'^\s*\d+[\.\)]\s+', line))     # Numbered lists
            
            # Check for titles/headers (short, centered, or all-caps lines)
            is_title = (len(line) < 50 and 
                       not any(p in line for p in '.!?') and
                       not is_list_item and
                       (i > 0 and i < len(lines)-1 and not lines[i-1].strip() and not lines[i+1].strip()))
            
            # Add spacing before titles and after list items
            if is_title and formatted_lines and formatted_lines[-1] != '':
                formatted_lines.append('')
            elif is_list_item and not in_list and formatted_lines and formatted_lines[-1] != '':
                formatted_lines.append('')
            
            # Process the line based on its type
            if is_title:
                formatted_lines.append(line.upper())
                formatted_lines.append('')  # Blank line after title
                prev_line_was_blank = True
                in_list = False
            elif is_list_item:
                # Standardize list item formatting
                if re.match(r'^\s*[•‣⁃]', line):
                    line = re.sub(r'^\s*[•‣⁃]\s*', '- ', line)
                formatted_lines.append(line)
                in_list = True
                prev_line_was_blank = False
            else:
                # Regular paragraph - add 2-space indent if not already indented
                if not line.startswith('  '):
                    line = '  ' + line
                formatted_lines.append(line)
                in_list = False
                prev_line_was_blank = False
        
        # Join lines and clean up spacing
        formatted_text = '\n'.join(formatted_lines)
        
        # Apply Braille-specific formatting rules
        formatted_text = re.sub(r'\s+', ' ', formatted_text)  # Single spaces only
        
        # Fix spacing around punctuation
        formatted_text = re.sub(r'\s*([,.!?;:])\s*', r'\1 ', formatted_text)
        formatted_text = re.sub(r'\s+([.!?])\s*$', r'\1', formatted_text, flags=re.MULTILINE)
        
        # Ensure proper capitalization after sentence endings
        formatted_text = re.sub(r'([.!?]\s+)([a-z])', 
                              lambda m: m.group(1) + m.group(2).upper(), 
                              formatted_text)
        
        # Split into lines and process each line individually
        lines = formatted_text.split('\n')
        wrapped_lines = []
        
        for line in lines:
            if not line.strip():
                wrapped_lines.append('')
                continue
                
            # Preserve indentation
            indent = ''
            if line.startswith('  '):
                indent = '  '
                line = line[2:].lstrip()
            
            # Special handling for list items
            is_list_item = line.startswith(('-', '*', '•', '‣', '⁃')) or \
                         re.match(r'^\d+[\.\)]', line)
            
            if is_list_item:
                # Handle list items with hanging indent
                bullet = ''
                if line.startswith('-'):
                    bullet = '- '
                    line = line[1:].lstrip()
                elif re.match(r'^\d+[\.\)]', line):
                    bullet = re.match(r'^(\d+[\.\)]\s*)', line).group(1)
                    line = line[len(bullet):].lstrip()
                
                # Process the list item content with hanging indent
                content_lines = []
                current_line = bullet + line
                
                while len(current_line) > self.BRAILLE_CHARS_PER_LINE:
                    # Find last space before line break
                    wrap_pos = current_line.rfind(' ', len(bullet), self.BRAILLE_CHARS_PER_LINE + 1)
                    if wrap_pos <= len(bullet):  # No space found in first line
                        wrap_pos = current_line.find(' ', len(bullet) + 1)
                        if wrap_pos == -1:  # No space at all
                            wrap_pos = min(len(current_line), self.BRAILLE_CHARS_PER_LINE)
                    
                    content_lines.append(current_line[:wrap_pos].rstrip())
                    current_line = ' ' * (len(bullet) + 2) + current_line[wrap_pos:].lstrip()
                
                if current_line:
                    content_lines.append(current_line)
                
                wrapped_lines.extend(content_lines)
            else:
                # Regular text wrapping
                while len(line) > self.BRAILLE_CHARS_PER_LINE:
                    # Try to break at word boundaries - be more aggressive
                    wrap_pos = line[:self.BRAILLE_CHARS_PER_LINE].rfind(' ')
                    if wrap_pos <= 0:  # No space found, force break
                        wrap_pos = self.BRAILLE_CHARS_PER_LINE - 3  # Leave 3 char margin for safety
                    wrapped_lines.append(indent + line[:wrap_pos].rstrip())
                    line = line[wrap_pos:].lstrip()
                    indent = '  '  # Indent wrapped lines
                
                if line:  # Add the remaining part of the line
                    wrapped_lines.append(indent + line)
        
        # Ensure consistent spacing between sections
        result = []
        for i, line in enumerate(wrapped_lines):
            result.append(line)
            # Add blank line after titles and before new sections
            if i < len(wrapped_lines) - 1:
                is_title = line.isupper()
                is_section_break = line.strip() and not wrapped_lines[i+1].strip()
                is_header = bool(re.match(r'^\s*[A-Z][^.!?]*$', line))
                
                if (is_title or is_section_break or 
                    (is_header and not wrapped_lines[i+1].startswith('  ') and 
                     not wrapped_lines[i+1].startswith(('-', '*', '•', '‣', '⁃'))):
                    result.append('')
        
        return '\n'.join(result).strip()
    
    def _calculate_pagination(self, braille_text: str) -> Dict[str, any]:
        """Calculate pagination for braille text"""
        lines = braille_text.split('\n')
        total_chars = len(braille_text.replace('\n', ''))
        
        # Calculate pages needed
        pages_needed = math.ceil(total_chars / self.CHARS_PER_PAGE)
        
        # Break text into pages
        pages = []
        current_page = []
        current_page_chars = 0
        current_page_lines = 0
        
        for line in lines:
            line_length = len(line)
            lines_needed = math.ceil(line_length / self.BRAILLE_CHARS_PER_LINE) if line_length > 0 else 1
            
            # Check if line fits on current page
            if (current_page_lines + lines_needed <= self.BRAILLE_LINES_PER_PAGE and 
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
            "lines_per_page": self.BRAILLE_LINES_PER_PAGE,
            "chars_per_line": self.BRAILLE_CHARS_PER_LINE,
            "pages": pages
        }
    
    def get_page_content(self, braille_text: str, page_number: int) -> Dict[str, any]:
        """Get content for a specific page"""
        pagination_info = self._calculate_pagination(braille_text)
        
        if page_number < 1 or page_number > pagination_info["total_pages"]:
            return {
                "page_content": "",
                "page_number": page_number,
                "status": "error",
                "error": "Page number out of range"
            }
        
        page_data = pagination_info["pages"][page_number - 1]
        page_content = '\n'.join(page_data["lines"])
        
        return {
            "page_content": page_content,
            "page_number": page_number,
            "char_count": page_data["char_count"],
            "line_count": page_data["line_count"],
            "status": "success"
        }


class GCodeGenerationService:
    """
    G-code generation service for 3D printing Braille text
    Based on BrailleRap implementation
    """
    
    def __init__(self):
        # Braille dimensions (standard values from BrailleRap)
        self.MARGIN_WIDTH = 20.0          # mm
        self.MARGIN_HEIGHT = 20.0         # mm  
        self.PAPER_WIDTH = 170.0          # mm
        self.PAPER_HEIGHT = 125.0         # mm
        self.LETTER_WIDTH = 2.54          # mm
        self.DOT_RADIUS = 1.25            # mm
        self.LETTER_PADDING = 3.75        # mm
        self.LINE_PADDING = 5.3           # mm
        
        # Printer settings
        self.HEAD_DOWN_POSITION = -2.0    # mm (embossing position)
        self.HEAD_UP_POSITION = 10.0      # mm (travel position)
        self.SPEED = 5000                 # mm/min
        
        # Coordinate settings
        self.INVERT_X = False
        self.INVERT_Y = False
        self.MIRROR_X = False
        self.MIRROR_Y = False
        self.DELTA_PRINTER = False
        self.GO_TO_ZERO = False
        
        # Braille dot mapping (6-dot braille)
        # Dots are numbered 1-6 in standard braille pattern:
        # 1 4
        # 2 5  
        # 3 6
        self.DOT_MAP = [
            [1, 2, 3],  # Left column (x=0)
            [4, 5, 6]   # Right column (x=1)
        ]
        
        # Unicode braille to dot pattern mapping
        self.unicode_to_dots = self._create_unicode_dot_mapping()
    
    def _create_unicode_dot_mapping(self):
        """Create mapping from Unicode braille characters to dot patterns"""
        mapping = {}
        
        # Unicode braille pattern starts at U+2800 (⠀)
        # Each bit represents a dot: bit 0=dot 1, bit 1=dot 2, etc.
        for i in range(256):  # 2^8 = 256 possible combinations
            unicode_char = chr(0x2800 + i)
            dots = []
            
            # Convert bit pattern to dot numbers
            if i & 0x01: dots.append(1)  # bit 0 -> dot 1
            if i & 0x02: dots.append(2)  # bit 1 -> dot 2  
            if i & 0x04: dots.append(3)  # bit 2 -> dot 3
            if i & 0x08: dots.append(4)  # bit 3 -> dot 4
            if i & 0x10: dots.append(5)  # bit 4 -> dot 5
            if i & 0x20: dots.append(6)  # bit 5 -> dot 6
            # Ignore bits 6,7 for 6-dot braille
            
            mapping[unicode_char] = dots
            
        return mapping
    
    def _gcode_set_absolute_positioning(self):
        """Set absolute positioning mode"""
        return 'G90;\r\n'
    
    def _gcode_set_speed(self, speed):
        """Set movement speed"""
        return f'G1 F{speed};\r\n'
    
    def _gcode_position(self, x=None, y=None, z=None):
        """Format position coordinates"""
        code = ''
        if x is not None:
            code += f' X{x:.2f}'
        if y is not None:
            code += f' Y{y:.2f}'
        if z is not None:
            code += f' Z{z:.2f}'
        code += ';\r\n'
        return code
    
    def _gcode_move_to(self, x=None, y=None, z=None):
        """Generate G1 move command"""
        return 'G1' + self._gcode_position(x, y, z)
    
    def _gcode_go_to(self, x=None, y=None, z=None):
        """Generate G0 rapid move command"""
        return 'G0' + self._gcode_position(x, y, z)
    
    def generate_gcode(self, braille_text: str, settings: dict = None) -> dict:
        """
        Generate G-code for 3D printing braille text
        
        Args:
            braille_text: Unicode braille text to print
            settings: Optional printer settings override
            
        Returns:
            dict with gcode, dimensions, and metadata
        """
        try:
            # Apply custom settings if provided
            if settings:
                for key, value in settings.items():
                    if hasattr(self, key.upper()):
                        setattr(self, key.upper(), value)
            
            # Initialize G-code
            gcode = self._gcode_set_absolute_positioning()
            gcode += self._gcode_set_speed(self.SPEED)
            
            if self.GO_TO_ZERO:
                gcode += self._gcode_move_to(0, 0, 0)
            
            gcode += self._gcode_move_to(z=self.HEAD_UP_POSITION)
            
            # Initialize position
            current_x = self.MARGIN_WIDTH
            current_y = self.MARGIN_HEIGHT
            
            # Track dimensions
            max_x = current_x
            max_y = current_y
            
            # Process each character
            lines = braille_text.split('\n')
            
            for line in lines:
                current_x = self.MARGIN_WIDTH  # Reset to left margin
                
                for char in line:
                    # Skip non-braille characters
                    if char not in self.unicode_to_dots:
                        if char == ' ':
                            # Space character - just advance position
                            current_x += self.LETTER_WIDTH + self.LETTER_PADDING
                        continue
                    
                    # Get dot pattern for this character
                    dots = self.unicode_to_dots[char]
                    
                    # Convert to printer coordinates
                    gx = self.INVERT_X and -current_x or (self.PAPER_WIDTH - current_x)
                    gy = -current_y  # Canvas Y goes down, printer Y goes up
                    
                    if self.DELTA_PRINTER:
                        gx -= self.PAPER_WIDTH / 2
                        gy += self.PAPER_HEIGHT / 2
                    elif not self.INVERT_Y:
                        gy += self.PAPER_HEIGHT
                    
                    # Move to character position
                    gcode += self._gcode_move_to(
                        self.MIRROR_X and -gx or gx,
                        self.MIRROR_Y and -gy or gy
                    )
                    
                    # Draw each dot
                    for y in range(3):  # 3 rows
                        for x in range(2):  # 2 columns
                            dot_number = self.DOT_MAP[x][y]
                            
                            if dot_number in dots:
                                # Calculate dot position
                                dot_x = current_x + x * self.LETTER_WIDTH
                                dot_y = current_y + y * self.LETTER_WIDTH
                                
                                # Convert to printer coordinates
                                if x > 0 or y > 0:  # Skip first dot move (already positioned)
                                    gx = self.INVERT_X and -dot_x or (self.PAPER_WIDTH - dot_x)
                                    gy = -dot_y
                                    
                                    if self.DELTA_PRINTER:
                                        gx -= self.PAPER_WIDTH / 2
                                        gy += self.PAPER_HEIGHT / 2
                                    elif not self.INVERT_Y:
                                        gy += self.PAPER_HEIGHT
                                    
                                    gcode += self._gcode_move_to(
                                        self.MIRROR_X and -gx or gx,
                                        self.MIRROR_Y and -gy or gy
                                    )
                                
                                # Emboss the dot
                                gcode += self._gcode_move_to(z=self.HEAD_DOWN_POSITION)
                                gcode += self._gcode_move_to(z=self.HEAD_UP_POSITION)
                    
                    # Advance to next character position
                    current_x += self.LETTER_WIDTH + self.LETTER_PADDING
                    max_x = max(max_x, current_x)
                    
                    # Check if we need to wrap to next line
                    if current_x + self.LETTER_WIDTH + self.DOT_RADIUS > self.PAPER_WIDTH - self.MARGIN_WIDTH:
                        break
                
                # Move to next line
                current_y += 3 * self.LETTER_WIDTH + self.LINE_PADDING
                max_y = max(max_y, current_y)
                
                # Check if we're out of paper
                if current_y > self.PAPER_HEIGHT - self.MARGIN_HEIGHT:
                    break
            
            # Finish G-code
            gcode += self._gcode_move_to(z=self.HEAD_UP_POSITION)
            if self.GO_TO_ZERO:
                gcode += self._gcode_move_to(0, 0, 0)
            
            # Calculate dimensions
            width = max_x - self.MARGIN_WIDTH
            height = max_y - self.MARGIN_HEIGHT
            
            return {
                'status': 'success',
                'gcode': gcode,
                'dimensions': {
                    'width': round(width, 1),
                    'height': round(height, 1),
                    'paper_width': self.PAPER_WIDTH,
                    'paper_height': self.PAPER_HEIGHT
                },
                'settings': {
                    'speed': self.SPEED,
                    'head_down': self.HEAD_DOWN_POSITION,
                    'head_up': self.HEAD_UP_POSITION,
                    'letter_width': self.LETTER_WIDTH,
                    'dot_radius': self.DOT_RADIUS
                },
                'stats': {
                    'lines': len(lines),
                    'characters': len([c for c in braille_text if c in self.unicode_to_dots]),
                    'estimated_time_minutes': self._estimate_print_time(gcode)
                }
            }
            
        except Exception as e:
            logger.error(f"G-code generation error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'gcode': '',
                'dimensions': {'width': 0, 'height': 0}
            }
    
    def _estimate_print_time(self, gcode: str) -> int:
        """Rough estimate of print time in minutes"""
        lines = gcode.count('\r\n')
        # Very rough estimate: ~0.1 seconds per G-code line
        return max(1, int(lines * 0.1 / 60))


class DocumentProcessingService:
    """Main service that orchestrates all document processing steps"""
    
    def __init__(self):
        self.text_optimizer = TextOptimizationService()
        self.ocr_service = OCRService()
        self.braille_service = BrailleConversionService()
        self.gcode_service = GCodeGenerationService()
    
    def process_document_full_pipeline(self, file_path: str, file_type: str, 
                                     optimize_text: bool = True, 
                                     braille_grade: int = 2) -> Dict[str, any]:
        """
        Process document through full pipeline: extraction → optimization → braille conversion
        """
        results = {
            "file_path": file_path,
            "file_type": file_type,
            "steps_completed": [],
            "status": "processing",
            "errors": []
        }
        
        
        try:
            # Step 1: Text extraction
            extracted_text = ""
            
            if file_type == "image":
                logger.info("Processing image with OCR")
                ocr_result = self.ocr_service.extract_text_from_image(file_path)
                if ocr_result["status"] == "success":
                    extracted_text = ocr_result["text"]
                    results["ocr_result"] = ocr_result
                    results["steps_completed"].append("ocr_extraction")
                    logger.info(f"OCR successful: {len(extracted_text)} characters extracted")
                else:
                    error_msg = f"OCR failed: {ocr_result.get('error', 'Unknown error')}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
                    # Continue with empty text - might still want to test other steps
            
            elif file_type in ["txt", "text"]:
                logger.info("Reading text file")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        extracted_text = f.read()
                    results["steps_completed"].append("text_extraction")
                    logger.info(f"Text extraction successful: {len(extracted_text)} characters")
                except Exception as e:
                    error_msg = f"Text file reading failed: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            else:
                # For other document types, assume text is already extracted and passed via file
                logger.info(f"Processing document type: {file_type}")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        extracted_text = f.read()
                    results["steps_completed"].append("text_extraction")
                    logger.info(f"Document text extraction: {len(extracted_text)} characters")
                except Exception as e:
                    error_msg = f"Document reading failed: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            results["extracted_text"] = extracted_text
            
            # Step 2: Text optimization (if requested and we have text)
            optimized_text = extracted_text
            if optimize_text and extracted_text.strip():
                logger.info("Starting text optimization")
                try:
                    optimization_result = self.text_optimizer.optimize_extracted_text(
                        extracted_text, "textbook"
                    )
                    if optimization_result.get("status") == "success":
                        optimized_text = optimization_result["optimized_text"]
                        results["optimization_result"] = optimization_result
                        results["optimization_method"] = optimization_result.get("method", "ai")
                        results["steps_completed"].append("text_optimization")
                        logger.info(f"Text optimization successful: {len(optimized_text)} characters")
                    else:
                        error_msg = f"Text optimization failed: {optimization_result.get('error', 'Unknown')}"
                        results["errors"].append(error_msg)
                        logger.warning(error_msg)
                        # Continue with original text
                except Exception as e:
                    error_msg = f"Text optimization error: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            results["optimized_text"] = optimized_text
            
            # Step 3: Braille conversion (if we have text)
            if optimized_text.strip():
                logger.info("Starting Braille conversion")
                try:
                    braille_result = self.braille_service.convert_to_braille(
                        optimized_text, braille_grade
                    )
                    results["braille_result"] = braille_result
                    results["steps_completed"].append("braille_conversion")
                    
                    if braille_result.get("status") == "success":
                        logger.info(f"Braille conversion successful: Grade {braille_grade}")
                    else:
                        error_msg = f"Braille conversion failed: {braille_result.get('error', 'Unknown')}"
                        results["errors"].append(error_msg)
                        logger.warning(error_msg)
                        
                except Exception as e:
                    error_msg = f"Braille conversion error: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
            else:
                results["errors"].append("No text available for Braille conversion")
            
            # Step 4: G-code generation
            if optimized_text.strip():
                logger.info("Starting G-code generation")
                try:
                    gcode_result = self.gcode_service.generate_gcode(
                        braille_result["braille_text"]
                    )
                    results["gcode_result"] = gcode_result
                    results["steps_completed"].append("gcode_generation")
                    
                    if gcode_result.get("status") == "success":
                        logger.info(f"G-code generation successful")
                    else:
                        error_msg = f"G-code generation failed: {gcode_result.get('error', 'Unknown')}"
                        results["errors"].append(error_msg)
                        logger.warning(error_msg)
                        
                except Exception as e:
                    error_msg = f"G-code generation error: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            # Determine final status
            if len(results["steps_completed"]) == 0:
                results["status"] = "failed"
            elif len(results["errors"]) > 0:
                results["status"] = "partial_success"
            else:
                results["status"] = "completed"
                
            logger.info(f"Pipeline completed with status: {results['status']}")
            logger.info(f"Steps completed: {results['steps_completed']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Pipeline critical error: {e}")
            import traceback
            traceback.print_exc()
            results["status"] = "error"
            results["error"] = str(e)
            results["errors"].append(f"Pipeline error: {str(e)}")
            return results

    def process_document_full_pipeline(self, file_path: str, file_type: str, 
                                     optimize_text: bool = True, 
                                     braille_grade: int = 2) -> Dict[str, any]:
        """
        Process document through the complete pipeline:
        1. Extract text
        2. Clean and optimize text for Braille
        3. Convert to Braille with proper formatting
        4. Generate PDF for embossing
        """
        results = {
            "status": "processing",
            "file_path": file_path,
            "file_type": file_type,
            "steps_completed": [],
            "errors": []
        }
        
        try:
            # Step 1: Extract text based on file type
            logger.info(f"📄 Step 1: Starting text extraction for {file_type} file")
            
            if file_type == 'pdf':
                text_result = self.pdf_extractor.extract_text_from_pdf(file_path)
            elif file_type in ['docx', 'doc']:
                text_result = self.text_extractor.extract_text_from_doc(file_path)
            elif file_type == 'txt':
                text_result = self.text_extractor.extract_text_from_txt(file_path)
            elif file_type in ['png', 'jpg', 'jpeg']:
                text_result = self.ocr_service.extract_text_from_image(file_path)
            else:
                results["status"] = "error"
                results["error"] = f"Unsupported file type: {file_type}"
                return results
            
            if text_result["status"] != "success" or not text_result.get("text"):
                results["status"] = "error"
                results["error"] = text_result.get("error", "Text extraction failed")
                results["errors"].append(f"Extraction error: {results['error']}")
                return results
            
            results["extracted_text"] = text_result["text"]
            results["steps_completed"].append("text_extraction")
            logger.info(f"✅ Text extraction complete: {len(text_result['text'])} characters")
            
            # Step 2 & 3: Optimize text with AI formatting and line wrapping
            if optimize_text:
                logger.info("🤖 Step 2-3: Starting text optimization and formatting")
                optimization_result = self.text_optimizer.optimize_extracted_text(
                    text_result["text"], 
                    document_type=file_type
                )
                
                if optimization_result["status"] == "success":
                    results["optimized_text"] = optimization_result["optimized_text"]
                    results["optimization_method"] = optimization_result.get("method", "unknown")
                    results["steps_completed"].append("text_optimization")
                    logger.info(f"✅ Text optimization complete using {results['optimization_method']}")
                else:
                    # Use original text if optimization fails
                    logger.warning("⚠️ Optimization failed, using original text")
                    results["optimized_text"] = text_result["text"]
                    results["errors"].append(f"Optimization warning: {optimization_result.get('error', 'Unknown error')}")
            else:
                results["optimized_text"] = text_result["text"]
            
            # Step 4: Convert to Braille
            logger.info(f"⠿ Step 4: Starting Braille conversion (Grade {braille_grade})")
            braille_result = self.braille_service.convert_to_braille(
                results["optimized_text"], 
                grade=braille_grade
            )
            
            if braille_result["conversion_successful"]:
                results["braille_result"] = braille_result
                results["steps_completed"].append("braille_conversion")
                logger.info(f"✅ Braille conversion complete: {braille_result['page_count']} pages")
                
                # Step 5: Generate Braille PDF
                logger.info("📄 Step 5: Starting Braille PDF generation")
                
                # Extract filename for title
                import os
                file_title = os.path.splitext(os.path.basename(file_path))[0]
                
                # Prepare Braille data for PDF
                pdf_data = self.braille_service.prepare_for_pdf(
                    braille_result, 
                    title=file_title
                )
                
                if pdf_data["ready"]:
                    # Generate embossable PDF
                    pdf_output_path = file_path.replace(f'.{file_type}', '_braille.pdf')
                    pdf_result = self.braille_pdf_generator.generate_braille_pdf(
                        pdf_data, 
                        pdf_output_path
                    )
                    
                    if pdf_result["success"]:
                        results["pdf_result"] = pdf_result
                        results["steps_completed"].append("pdf_generation")
                        logger.info(f"✅ PDF generation complete: {pdf_output_path}")
                        
                        # Also generate preview PDF for sighted users
                        preview_path = file_path.replace(f'.{file_type}', '_preview.pdf')
                        preview_result = self.braille_pdf_generator.generate_preview_pdf(
                            pdf_data,
                            preview_path,
                            include_visual=True
                        )
                        
                        if preview_result["success"]:
                            results["preview_pdf"] = preview_result
                            results["steps_completed"].append("preview_generation")
                            logger.info(f"✅ Preview PDF generated: {preview_path}")
                    else:
                        results["errors"].append(f"PDF generation error: {pdf_result['error']}")
                        logger.error(f"❌ PDF generation failed: {pdf_result['error']}")
                else:
                    results["errors"].append(f"PDF preparation error: {pdf_data.get('error', 'Unknown error')}")
                    logger.error("❌ Failed to prepare Braille data for PDF")
            else:
                results["errors"].append(f"Braille conversion error: {braille_result['error_message']}")
                logger.error(f"❌ Braille conversion failed: {braille_result['error_message']}")
            
            # Determine final status
            if len(results["steps_completed"]) == 5:  # All steps completed
                results["status"] = "completed"
                logger.info("🎉 Full pipeline completed successfully!")
            elif results["errors"]:
                results["status"] = "partial_success"
                logger.warning(f"⚠️ Pipeline completed with {len(results['errors'])} errors")
            else:
                results["status"] = "success"
            
            return results
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results["status"] = "error"
            results["error"] = str(e)
            results["errors"].append(f"Pipeline error: {str(e)}")
            return results
