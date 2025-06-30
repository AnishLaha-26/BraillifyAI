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
        text = re.sub(r'[''']', "'", text)  # Normalize apostrophes
        text = re.sub(r'…', '...', text)  # Normalize ellipsis
        
        # Remove emojis and special Unicode characters
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
2. Start each paragraph with exactly 2 spaces
3. Each line must be 40 characters or less
4. Put blank lines between sections
5. Format lists with dash (-) for bullets
6. Remove any remaining URLs or metadata

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
        """
        logger.info("Step 3: Line wrapping for Braille")
        
        lines = text.split('\n')
        wrapped_lines = []
        
        for line in lines:
            line = line.rstrip()
            
            # Empty lines pass through
            if not line:
                wrapped_lines.append('')
                continue
            
            # Titles (all caps, no indent)
            if line.isupper() and len(line) <= self.MAX_LINE_LENGTH:
                wrapped_lines.append(line)
                continue
            
            # Check if this is a list item
            is_list_item = re.match(r'^[-•*]\s+', line) or re.match(r'^\d+\.\s+', line)
            
            if is_list_item:
                # Handle list items with hanging indent
                wrapped_lines.extend(self._wrap_list_item(line))
            else:
                # Regular paragraph or long title
                if line.isupper():
                    # Long title - wrap without indent
                    wrapped_lines.extend(self._wrap_text(line, indent=''))
                else:
                    # Regular paragraph - wrap with indent
                    wrapped_lines.extend(self._wrap_text(line, indent=self.PARAGRAPH_INDENT))
        
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
        match = re.match(r'^([-•*]\s+|\d+\.\s+)', text)
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
        current_line = []
        current_length = 0
        is_first_line = True
        
        for word in words:
            word_length = len(word)
            max_length = first_line_max if is_first_line else (self.MAX_LINE_LENGTH - len(hanging_indent))
            
            if current_line and current_length + 1 + word_length > max_length:
                # Save current line
                if is_first_line:
                    lines.append(marker + ' '.join(current_line))
                    is_first_line = False
                else:
                    lines.append(hanging_indent + ' '.join(current_line))
                
                current_line = [word]
                current_length = word_length
            else:
                if current_line:
                    current_length += 1 + word_length
                else:
                    current_length = word_length
                current_line.append(word)
        
        # Add the last line
        if current_line:
            if is_first_line:
                lines.append(marker + ' '.join(current_line))
            else:
                lines.append(hanging_indent + ' '.join(current_line))
        
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
        Convert text to braille using liblouis with proper formatting
        
        Args:
            text: Text to convert
            grade: Braille grade (1 or 2)
            
        Returns:
            Dictionary with braille conversion results
        """
        try:
            # Pre-process text for Braille formatting
            formatted_text = self._format_for_braille(text)
            
            # Choose appropriate braille table
            table = "en-us-g2.ctb" if grade == 2 else "en-us-g1.ctb"
            
            # Convert text to braille
            braille_text = louis.translateString([table], formatted_text)
            
            # Calculate pagination
            pagination_info = self._calculate_pagination(braille_text)
            
            return {
                "braille_text": braille_text,
                "original_text": text,
                "formatted_text": formatted_text,
                "grade": grade,
                "table_used": table,
                "pagination": pagination_info,
                "status": "success"
            }
            
        except Exception as e:
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
                    wrap_pos = line.rfind(' ', 0, self.BRAILLE_CHARS_PER_LINE - 2)  # Leave 2 char margin
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
                     not wrapped_lines[i+1].startswith(('-', '*', '•', '‣', '⁃')))):
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


class DocumentProcessingService:
    """Main service that orchestrates all document processing steps"""
    
    def __init__(self):
        self.text_optimizer = TextOptimizationService()
        self.ocr_service = OCRService()
        self.braille_service = BrailleConversionService()
    
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
            "status": "processing"
        }
        
        try:
            # Step 1: Text extraction (already handled in routes.py for PDFs)
            # For images, use OCR
            if file_type == "image":
                ocr_result = self.ocr_service.extract_text_from_image(file_path)
                if ocr_result["status"] == "success":
                    extracted_text = ocr_result["text"]
                    results["ocr_result"] = ocr_result
                    results["steps_completed"].append("ocr_extraction")
                else:
                    results["status"] = "error"
                    results["error"] = f"OCR failed: {ocr_result.get('error', 'Unknown error')}"
                    return results
            else:
                # For documents, text should already be extracted
                # This would be passed in or read from file
                extracted_text = ""  # This would be provided by the caller
            
            # Step 2: Text optimization (if requested)
            if optimize_text and extracted_text:
                optimization_result = self.text_optimizer.optimize_extracted_text(
                    extracted_text, "textbook"
                )
                optimized_text = optimization_result["optimized_text"]
                results["optimization_result"] = optimization_result
                results["steps_completed"].append("text_optimization")
            else:
                optimized_text = extracted_text
            
            # Step 3: Braille conversion
            if optimized_text:
                braille_result = self.braille_service.convert_to_braille(
                    optimized_text, braille_grade
                )
                results["braille_result"] = braille_result
                results["steps_completed"].append("braille_conversion")
            
            results["status"] = "completed"
            return results
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results["status"] = "error"
            results["error"] = str(e)
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
