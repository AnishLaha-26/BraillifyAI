from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file, current_app, abort
import os
import shutil
from werkzeug.utils import secure_filename
import PyPDF2
import io
from . import db
from .models import Upload
from datetime import datetime

main = Blueprint('main', __name__)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {
    'document': {'pdf', 'txt', 'doc', 'docx', 'ppt', 'pptx'},
    'audio': {'mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'wma'},
    'image': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'tiff', 'webp'}
}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
def allowed_file(filename, upload_type='document'):
    """Check if file extension is allowed for the given upload type"""
    if '.' not in filename:
        return False
    
    file_ext = filename.rsplit('.', 1)[1].lower()
    allowed_exts = ALLOWED_EXTENSIONS.get(upload_type, ALLOWED_EXTENSIONS['document'])
    return file_ext in allowed_exts

def get_file_type_from_upload_type(upload_type):
    """Map upload type to database file_type"""
    type_mapping = {
        'audio': 'audio',
        'image': 'image', 
        'document': 'document'
    }
    return type_mapping.get(upload_type, 'document')

def get_error_message_for_type(upload_type):
    """Get appropriate error message for file type validation"""
    messages = {
        'audio': 'Only audio files are allowed (MP3, WAV, FLAC, AAC, M4A, OGG, WMA)',
        'image': 'Only image files are allowed (JPG, JPEG, PNG, GIF, BMP, SVG, TIFF, WEBP)',
        'document': 'Only document files are allowed (PDF, TXT, DOC, DOCX, PPT, PPTX)'
    }
    return messages.get(upload_type, messages['document'])

def extract_text_from_pdf(file_stream):
    """Extract text from PDF file"""
    try:
        # Ensure we're at the beginning of the stream
        file_stream.seek(0)
        pdf_reader = PyPDF2.PdfReader(file_stream)
        
        # Check if PDF has pages
        if len(pdf_reader.pages) == 0:
            return "Error: PDF file appears to be empty (no pages found)"
        
        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                text += page_text + "\n"
            except Exception as page_error:
                print(f"Error extracting text from page {page_num + 1}: {page_error}")
                text += f"[Error reading page {page_num + 1}]\n"
        
        extracted_text = text.strip()
        if not extracted_text:
            return "Warning: No text could be extracted from this PDF (it may contain only images or be scanned)"
        
        return extracted_text
    except Exception as e:
        error_msg = f"Error processing PDF: {str(e)}"
        print(error_msg)
        return error_msg

@main.route('/')
def index():
    # Fetch recent uploads to display on dashboard
    try:
        recent_uploads = Upload.query.filter(
            Upload.status == 'completed'
        ).order_by(Upload.upload_date.desc()).limit(10).all()
        
        textbooks = []
        for upload in recent_uploads:
            textbook = {
                'id': upload.id,
                'title': upload.title or upload.filename,
                'filename': upload.filename,
                'upload_date': upload.upload_date,
                'file_type': upload.file_type,
                'page_count': upload.page_count,
                'file_size': f"{upload.file_size/1024:.1f} KB" if upload.file_size else "Unknown",
                'has_text': bool(upload.text_content or upload.ocr_text),
                'has_optimized': bool(upload.optimized_text),
                'has_braille': bool(upload.braille_text),
                'file_path': upload.file_path
            }
            textbooks.append(textbook)
            
        return render_template('index.html', textbooks=textbooks)
        
    except Exception as e:
        print(f"Error fetching textbooks: {e}")
        return render_template('index.html', textbooks=[])

@main.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Debug logging
        print("=== UPLOAD REQUEST ===")
        print(f"request.files: {request.files}")
        print(f"request.form: {request.form}")
        print(f"request.files keys: {list(request.files.keys())}")
        
        # Check if this is direct text input
        if 'text' in request.form and request.form['text'].strip():
            print("DEBUG: Processing direct text input")
            text_content = request.form['text'].strip()
            
            # Create database record for text input
            upload = Upload(
                filename="Direct Text Input",
                file_path="",
                file_type='text',
                mime_type='text/plain',
                file_size=len(text_content.encode('utf-8'))
            )
            
            # Add to database to get the ID
            db.session.add(upload)
            db.session.commit()
            
            # Save the raw text content
            upload.text_content = text_content
            
            # Apply text optimization using the enhanced service
            try:
                print("DEBUG: Applying text optimization to direct input")
                from .services import DocumentProcessingService
                processing_service = DocumentProcessingService()
                
                # Save text to a temporary file for processing
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                    temp_file.write(text_content)
                    temp_path = temp_file.name
                
                # Process through complete pipeline
                pipeline_result = processing_service.process_document_full_pipeline(
                    temp_path, 
                    'txt',
                    optimize_text=True,
                    braille_grade=2
                )
                
                # Clean up temp file
                os.unlink(temp_path)
                
                # Save all results to database
                if pipeline_result["status"] in ["completed", "partial_success", "success"]:
                    upload.optimized_text = pipeline_result.get('optimized_text', text_content)
                    upload.is_optimized = True
                    upload.optimization_date = datetime.utcnow()
                    upload.optimization_model = pipeline_result.get('optimization_method', 'pipeline')
                    upload.optimization_notes = f"Pipeline completed: {', '.join(pipeline_result.get('steps_completed', []))}"
                    # Store Braille results if available
                    if 'braille_result' in pipeline_result:
                                        braille_result = pipeline_result['braille_result']
                                        upload.braille_text = braille_result.get('braille_text', '')
                                        upload.braille_content = braille_result.get('braille_text', '')  # Use same content for both fields
                                        upload.braille_pages = braille_result.get('pagination', {}).get('total_pages', 0)
                                        upload.braille_chars_per_page = braille_result.get('pagination', {}).get('chars_per_line', 40)
                                        upload.braille_lines_per_page = braille_result.get('pagination', {}).get('lines_per_page', 25)
                                        upload.braille_grade = braille_result.get('grade', 2)
                                        upload.is_braille_converted = True
                                        upload.braille_conversion_date = datetime.utcnow()
                                        print(f"DEBUG: Braille conversion saved - Pages: {upload.braille_pages}, Grade: {upload.braille_grade}")
                    else:
                        print("DEBUG: No braille_result found in pipeline_result")
                        print(f"DEBUG: Available keys: {list(pipeline_result.keys())}")
                    
                    # Store PDF paths if generated
                    if 'pdf_result' in pipeline_result:
                        upload.pdf_path = pipeline_result['pdf_result'].get('output_path', '')
                    
                    if 'preview_pdf' in pipeline_result:
                        upload.preview_pdf_path = pipeline_result['preview_pdf'].get('output_path', '')
                
                print(f"DEBUG: Full pipeline completed, status: {pipeline_result['status']}")
                
            except Exception as e:
                print(f"Warning: Pipeline processing failed: {e}")
                # Continue without optimization
            
            upload.status = 'completed'
            db.session.commit()
            
            # Redirect to the textbook view
            return redirect(url_for('main.textbook_view', upload_id=upload.id))
        
        # Handle file uploads (existing logic)
        if 'files' not in request.files:
            print("ERROR: No 'files' key in request.files and no text input")
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        upload_type = request.form.get('upload_type', 'document')
        
        print(f"Files found: {len(files)}")
        print(f"Upload type: {upload_type}")
        
        if not files or all(file.filename == '' for file in files):
            print("ERROR: No files selected or empty filenames")
            return jsonify({'error': 'No files selected'}), 400
        
        results = []
        upload_dir = os.path.abspath('uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        for file in files:
            if file and allowed_file(file.filename, upload_type):
                filename = secure_filename(file.filename)
                
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    results.append({
                        'filename': filename,
                        'status': 'error',
                        'message': f'File too large. Maximum size is {MAX_FILE_SIZE/1024/1024:.1f}MB'
                    })
                    continue
                
                file_ext = filename.rsplit('.', 1)[1].lower()
                
                # Create database record with correct file type
                upload = Upload(
                    filename=filename,
                    file_path="",  # Will be set after we get the upload ID
                    file_type=get_file_type_from_upload_type(upload_type),
                    mime_type=file.content_type,
                    file_size=file_size
                )
                
                # Add to database to get the ID
                db.session.add(upload)
                db.session.commit()
                
                # Now use the upload ID for file naming
                pdf_filename = f"{upload.id}_{secure_filename(filename)}"
                file_path = os.path.join(upload_dir, pdf_filename)
                upload.file_path = file_path
                
                try:
                    # Handle different file types based on upload type
                    if upload_type == 'document':
                        # Process documents (PDF, TXT, etc.)
                        if file_ext == 'pdf':
                            upload.status = 'processing'
                            db.session.commit()
                            
                            # Save PDF with upload ID
                            file_content = file.read()
                            with open(file_path, 'wb') as f:
                                f.write(file_content)
                            
                            # Save extracted text with upload ID
                            text_filename = f"{upload.id}_extracted.txt"
                            text_path = os.path.join(upload_dir, text_filename)
                            extracted_text = extract_text_from_pdf(io.BytesIO(file_content))
                            with open(text_path, 'w', encoding='utf-8') as f:
                                f.write(extracted_text)
                            
                            upload.text_content = extracted_text
                            upload.text_file_path = text_path
                            
                            # Apply text optimization using the enhanced service
                            try:
                                print("DEBUG: Applying text optimization during upload")
                                from .services import DocumentProcessingService
                                processing_service = DocumentProcessingService()
                                
                                # Save text to a temporary file for processing
                                import tempfile
                                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                                    temp_file.write(extracted_text)
                                    temp_path = temp_file.name
                                
                                # Process through complete pipeline
                                pipeline_result = processing_service.process_document_full_pipeline(
                                    temp_path, 
                                    'txt',
                                    optimize_text=True,
                                    braille_grade=2
                                )
                                
                                # Clean up temp file
                                os.unlink(temp_path)
                                
                                # Save all results to database
                                if pipeline_result["status"] in ["completed", "partial_success", "success"]:
                                    upload.optimized_text = pipeline_result.get('optimized_text', extracted_text)
                                    upload.is_optimized = True
                                    upload.optimization_date = datetime.utcnow()
                                    upload.optimization_model = pipeline_result.get('optimization_method', 'pipeline')
                                    upload.optimization_notes = f"Pipeline completed: {', '.join(pipeline_result.get('steps_completed', []))}"
                                    
                                    # Store Braille results if available
                                    if 'braille_result' in pipeline_result:
                                        braille_result = pipeline_result['braille_result']
                                        upload.braille_text = braille_result.get('braille_text', '')
                                        upload.braille_content = braille_result.get('braille_text', '')  # Use same content for both fields
                                        upload.braille_pages = braille_result.get('pagination', {}).get('total_pages', 0)
                                        upload.braille_chars_per_page = braille_result.get('pagination', {}).get('chars_per_line', 40)
                                        upload.braille_lines_per_page = braille_result.get('pagination', {}).get('lines_per_page', 25)
                                        upload.braille_grade = braille_result.get('grade', 2)
                                        upload.is_braille_converted = True
                                        upload.braille_conversion_date = datetime.utcnow()
                                        print(f"DEBUG: Braille conversion saved - Pages: {upload.braille_pages}, Grade: {upload.braille_grade}")
                                    else:
                                        print("DEBUG: No braille_result found in pipeline_result")
                                        print(f"DEBUG: Available keys: {list(pipeline_result.keys())}")
                                    
                                    # Store PDF paths if generated
                                    if 'pdf_result' in pipeline_result:
                                        upload.pdf_path = pipeline_result['pdf_result'].get('output_path', '')
                                    
                                    if 'preview_pdf' in pipeline_result:
                                        upload.preview_pdf_path = pipeline_result['preview_pdf'].get('output_path', '')
                                
                                print(f"DEBUG: Full pipeline completed, status: {pipeline_result['status']}")
                                
                            except Exception as e:
                                print(f"Warning: Pipeline processing failed: {e}")
                                # Continue without optimization - it can be done later
                            
                            # Get page count from the same content
                            try:
                                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                                upload.page_count = len(pdf_reader.pages)
                            except Exception as e:
                                print(f"Error getting page count: {e}")
                                upload.page_count = 0
                            
                            upload.status = 'completed'
                            
                            results.append({
                                'upload_id': upload.id,
                                'id': upload.id,
                                'filename': filename,
                                'status': 'success',
                                'message': 'PDF uploaded and text extracted successfully',
                                'text_preview': extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text,
                                'file_size': f"{file_size/1024:.1f} KB",
                                'pages': upload.page_count
                            })
                            
                        elif file_ext == 'txt':
                            upload.status = 'processing'
                            db.session.commit()
                            
                            content = file.read().decode('utf-8')
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            
                            upload.text_content = content
                            
                            # Apply text optimization using the enhanced service
                            try:
                                print("DEBUG: Applying text optimization during text upload")
                                from .services import DocumentProcessingService
                                processing_service = DocumentProcessingService()
                                
                                # Save text to a temporary file for processing
                                import tempfile
                                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                                    temp_file.write(content)
                                    temp_path = temp_file.name
                                
                                # Process through complete pipeline
                                pipeline_result = processing_service.process_document_full_pipeline(
                                    temp_path, 
                                    'txt',
                                    optimize_text=True,
                                    braille_grade=2
                                )
                                
                                # Clean up temp file
                                os.unlink(temp_path)
                                
                                # Save all results to database
                                if pipeline_result["status"] in ["completed", "partial_success", "success"]:
                                    upload.optimized_text = pipeline_result.get('optimized_text', content)
                                    upload.is_optimized = True
                                    upload.optimization_date = datetime.utcnow()
                                    upload.optimization_model = pipeline_result.get('optimization_method', 'pipeline')
                                    upload.optimization_notes = f"Pipeline completed: {', '.join(pipeline_result.get('steps_completed', []))}"
                                    
                                    # Store Braille results if available
                                    if 'braille_result' in pipeline_result:
                                        braille_result = pipeline_result['braille_result']
                                        upload.braille_text = braille_result.get('braille_text', '')
                                        upload.braille_content = braille_result.get('braille_text', '')  # Use same content for both fields
                                        upload.braille_pages = braille_result.get('pagination', {}).get('total_pages', 0)
                                        upload.braille_chars_per_page = braille_result.get('pagination', {}).get('chars_per_line', 40)
                                        upload.braille_lines_per_page = braille_result.get('pagination', {}).get('lines_per_page', 25)
                                        upload.braille_grade = braille_result.get('grade', 2)
                                        upload.is_braille_converted = True
                                        upload.braille_conversion_date = datetime.utcnow()
                                        print(f"DEBUG: Braille conversion saved - Pages: {upload.braille_pages}, Grade: {upload.braille_grade}")
                                    else:
                                        print("DEBUG: No braille_result found in pipeline_result")
                                        print(f"DEBUG: Available keys: {list(pipeline_result.keys())}")
                                    
                                    # Store PDF paths if generated
                                    if 'pdf_result' in pipeline_result:
                                        upload.pdf_path = pipeline_result['pdf_result'].get('output_path', '')
                                    
                                    if 'preview_pdf' in pipeline_result:
                                        upload.preview_pdf_path = pipeline_result['preview_pdf'].get('output_path', '')
                                
                                print(f"DEBUG: Full pipeline completed, status: {pipeline_result['status']}")
                                
                            except Exception as e:
                                print(f"Warning: Pipeline processing failed: {e}")
                                # Continue without optimization - it can be done later
                            
                            upload.status = 'completed'
                            
                            results.append({
                                'id': upload.id,
                                'filename': filename,
                                'status': 'success',
                                'message': 'Text file uploaded successfully',
                                'text_preview': content[:200] + "..." if len(content) > 200 else content,
                                'file_size': f"{file_size/1024:.1f} KB"
                            })
                            
                        else:
                            # Handle other document types
                            upload.status = 'processing'
                            db.session.commit()
                            
                            file.save(file_path)
                            upload.status = 'completed'
                            
                            results.append({
                                'id': upload.id,
                                'filename': filename,
                                'status': 'success',
                                'message': f'{file_ext.upper()} document uploaded successfully',
                                'file_size': f"{file_size/1024:.1f} KB",
                                'note': 'Text extraction for this file type will be implemented in future updates'
                            })
                    
                    elif upload_type == 'audio':
                        # Handle audio files
                        upload.status = 'processing'
                        db.session.commit()
                        
                        file.save(file_path)
                        upload.status = 'completed'
                        
                        results.append({
                            'id': upload.id,
                            'filename': filename,
                            'status': 'success',
                            'message': f'{file_ext.upper()} audio file uploaded successfully',
                            'file_size': f"{file_size/1024:.1f} KB",
                            'note': 'Audio processing features will be implemented in future updates'
                        })
                    
                    elif upload_type == 'image':
                        # Handle image files
                        upload.status = 'processing'
                        db.session.commit()
                        
                        file.save(file_path)
                        upload.status = 'completed'
                        
                        results.append({
                            'id': upload.id,
                            'filename': filename,
                            'status': 'success',
                            'message': f'{file_ext.upper()} image uploaded successfully',
                            'file_size': f"{file_size/1024:.1f} KB",
                            'note': 'Image processing features will be implemented in future updates'
                        })
                    
                    db.session.commit()
                    
                except Exception as e:
                    upload.status = 'error'
                    upload.error_message = str(e)
                    db.session.commit()
                    results.append({
                        'id': upload.id,
                        'filename': filename,
                        'status': 'error',
                        'message': f'Error processing file: {str(e)}'
                    })
            else:
                results.append({
                    'filename': file.filename if file else 'Unknown file',
                    'status': 'error',
                    'message': get_error_message_for_type(upload_type)
                })
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(results)} files',
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error processing upload: {str(e)}'
        }), 500

@main.route('/thumbnail/<int:upload_id>')
def get_thumbnail(upload_id):
    """Generate and serve PDF thumbnail"""
    try:
        upload = Upload.query.get_or_404(upload_id)
        
        # Build possible file paths using new naming convention
        possible_paths = []
        if upload.file_path:
            # First try the stored file path
            possible_paths.append(upload.file_path)
            
        # Also try new naming convention
        if upload.filename:
            # Try with upload ID prefix
            upload_dir = os.path.abspath('uploads')
            new_filename = f"{upload.id}_{secure_filename(upload.filename)}"
            possible_paths.append(os.path.join(upload_dir, new_filename))
            
            # Also try original filename for backwards compatibility
            possible_paths.append(os.path.join(upload_dir, upload.filename))
        
        # Find the actual file
        actual_file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                actual_file_path = path
                print(f"Found PDF file at: {path}")
                break
                
        if not actual_file_path:
            print(f"File not found for upload {upload_id}: tried {possible_paths}")
            return send_file("static/default-pdf-icon.svg")
            
        # Check if thumbnail already exists - use absolute path
        thumbnail_dir = os.path.abspath(os.path.join("uploads", "thumbnails"))
        os.makedirs(thumbnail_dir, exist_ok=True)
        thumbnail_path = os.path.join(thumbnail_dir, f"{upload_id}_thumb.png")
        
        if not os.path.exists(thumbnail_path):
            # Generate thumbnail from first page of PDF
            print(f"Generating thumbnail for upload {upload_id} from {actual_file_path}")
            
            try:
                import fitz  # PyMuPDF
                print("Using PyMuPDF for thumbnail generation")
                doc = fitz.open(actual_file_path)
                if len(doc) > 0:
                    page = doc[0]
                    # Render page to image at 150 DPI
                    mat = fitz.Matrix(150/72, 150/72)
                    pix = page.get_pixmap(matrix=mat)
                    pix.save(thumbnail_path)
                    doc.close()
                    print(f"Successfully generated thumbnail using PyMuPDF: {thumbnail_path}")
                else:
                    print("PDF has no pages")
                    return send_file("static/default-pdf-icon.svg")
                    
            except ImportError as e:
                print(f"PyMuPDF not available: {e}")
                return send_file("static/default-pdf-icon.svg")
            
            except Exception as e:
                print(f"Error generating thumbnail with PyMuPDF: {e}")
                return send_file("static/default-pdf-icon.svg")
                
        print(f"Serving thumbnail from absolute path: {thumbnail_path}")
        return send_file(thumbnail_path)
        
    except Exception as e:
        print(f"Error in get_thumbnail: {e}")
        return send_file("static/default-pdf-icon.svg")

@main.route("/textbook/<int:upload_id>")
def textbook_view(upload_id):
    """View processed textbook with split-screen layout"""
    try:
        print(f"DEBUG: textbook_view called with upload_id: {upload_id}")
        upload = Upload.query.get_or_404(upload_id)
        print(f"DEBUG: Found upload: {upload.filename}, status: {upload.status}")

        # Ensure we have processed content
        if not upload.optimized_text and not upload.text_content:
            print("DEBUG: No content available, redirecting to index")
            flash('No content available for this upload. Please process the document first.', 'error')
            return redirect(url_for('main.index'))

        display_text = upload.optimized_text if upload.optimized_text else upload.text_content

        # Generate auto title if not already set
        if not upload.title:
            print("DEBUG: Generating auto title")
            try:
                from .services import TextOptimizationService
                optimization_service = TextOptimizationService()
                upload.title = optimization_service.generate_auto_title(display_text, upload.filename)
                db.session.commit()
                print(f"DEBUG: Generated title: {upload.title}")
            except Exception as e:
                print(f"DEBUG: Error generating title: {e}")
                upload.title = upload.filename

        # Split text into pages for display (approximately 500 words per page)
        text_pages = _paginate_text(display_text, words_per_page=500)

        # Prepare Braille and Pagination data
        braille_text = upload.braille_text or upload.braille_content  # Try both fields
        braille_grade = upload.braille_grade or 2  # Default to grade 2
        pagination = {
            'total_pages': upload.braille_pages or 0,
            'chars_per_page': upload.braille_chars_per_page or 40,
            'lines_per_page': upload.braille_lines_per_page or 25
        }
        
        # Get individual page content for proper display
        braille_pages = []
        if braille_text:
            try:
                from .services import BrailleConversionService
                braille_service = BrailleConversionService()
                # Get pagination with individual page content
                pagination_data = braille_service._calculate_pagination(braille_text)
                braille_pages = pagination_data.get('pages', [])
                # Update pagination with accurate data
                pagination.update({
                    'total_pages': pagination_data.get('total_pages', 0),
                    'chars_per_page': pagination_data.get('chars_per_page', 40),
                    'lines_per_page': pagination_data.get('lines_per_page', 25),
                    'chars_per_line': pagination_data.get('chars_per_line', 40)
                })
            except Exception as e:
                print(f"Error calculating pagination: {e}")
                # Fallback: create single page with all content
                braille_pages = [{
                    'page_number': 1,
                    'lines': braille_text.split('\n') if braille_text else [],
                    'char_count': len(braille_text) if braille_text else 0,
                    'line_count': len(braille_text.split('\n')) if braille_text else 0
                }]
        
        print(f"DEBUG: Braille data - Text length: {len(braille_text) if braille_text else 0}, Grade: {braille_grade}, Pages: {pagination['total_pages']}")

        # Convert to braille on-the-fly if not already available
        if not braille_text and display_text:
            print("DEBUG: Converting to braille on-the-fly")
            print(f"DEBUG: Display text length: {len(display_text)}")
            print(f"DEBUG: Display text preview: {display_text[:100]}...")
            try:
                from .services import BrailleConversionService
                braille_service = BrailleConversionService()
                result = braille_service.convert_to_braille(display_text, grade=braille_grade)
                
                print(f"DEBUG: Braille conversion result status: {result.get('status')}")
                print(f"DEBUG: Braille conversion error: {result.get('error', 'None')}")
                
                if result.get('status') == 'success':
                    # Update database with all details
                    upload.braille_text = result.get('braille_text', '')
                    upload.braille_content = result.get('braille_text', '')  # Store in both fields
                    
                    # Get pagination info
                    pagination_info = result.get('pagination', {})
                    upload.braille_pages = pagination_info.get('total_pages', 0)
                    upload.braille_chars_per_page = pagination_info.get('chars_per_line', 40)
                    upload.braille_lines_per_page = pagination_info.get('lines_per_page', 25)
                    upload.braille_grade = result.get('grade', braille_grade)
                    upload.is_braille_converted = True
                    upload.braille_conversion_date = datetime.utcnow()
                    db.session.commit()

                    # Update local variables for rendering this request
                    braille_text = upload.braille_text
                    braille_grade = upload.braille_grade
                    pagination['total_pages'] = upload.braille_pages
                    pagination['chars_per_page'] = upload.braille_chars_per_page
                    pagination['lines_per_page'] = upload.braille_lines_per_page

                    print(f"DEBUG: Braille conversion successful, pages: {upload.braille_pages}")
                    print(f"DEBUG: Updated braille_text length: {len(braille_text)}")
                    
                    # Re-calculate braille_pages after successful conversion
                    if braille_text:
                        try:
                            pagination_data = braille_service._calculate_pagination(braille_text)
                            braille_pages = pagination_data.get('pages', [])
                            print(f"DEBUG: Recalculated braille_pages count: {len(braille_pages)}")
                        except Exception as e:
                            print(f"DEBUG: Error recalculating pagination: {e}")
                else:
                    print(f"DEBUG: Braille conversion failed: {result.get('error', 'Unknown error')}")
                    braille_text = f"Braille conversion failed: {result.get('error', 'Unknown error')}"
            except Exception as e:
                print(f"Error converting to braille: {e}")
                import traceback
                traceback.print_exc()
                braille_text = f"Braille conversion error: {str(e)}"
        
        print("DEBUG: Rendering template with pagination")
        print(f"DEBUG: Final braille_pages count: {len(braille_pages)}")
        print(f"DEBUG: Final pagination: {pagination}")
        return render_template('textbook_view.html',
                             upload=upload,
                             textbook_title=upload.title,
                             optimized_text=display_text,
                             text_pages=text_pages,
                             braille_pages=braille_pages,
                             braille_grade=braille_grade,
                             pagination=pagination)

    except Exception as e:
        print(f"Error in textbook_view: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading textbook view', 'error')
        return redirect(url_for('main.index'))

def _paginate_text(text: str, words_per_page: int = 500) -> list:
    """Split text into pages for display while preserving formatting"""
    if not text:
        return [""]
    
    # Split by paragraphs first to preserve structure
    paragraphs = text.split('\n\n')
    pages = []
    current_page_content = []
    current_word_count = 0
    
    for paragraph in paragraphs:
        # Count words in this paragraph
        paragraph_words = len(paragraph.split()) if paragraph.strip() else 0
        
        # If adding this paragraph would exceed the limit, start a new page
        if current_word_count > 0 and current_word_count + paragraph_words > words_per_page:
            # Join current page content preserving formatting
            pages.append('\n\n'.join(current_page_content))
            current_page_content = []
            current_word_count = 0
        
        # Add paragraph to current page
        if paragraph.strip():  # Only add non-empty paragraphs
            current_page_content.append(paragraph)
            current_word_count += paragraph_words
        elif current_page_content:  # Preserve empty paragraphs between content
            current_page_content.append(paragraph)
    
    # Add remaining content as the last page
    if current_page_content:
        pages.append('\n\n'.join(current_page_content))
    
    return pages if pages else [""]

@main.route("/textbook/<int:upload_id>", methods=['DELETE'])
def delete_textbook(upload_id):
    """Delete a textbook and its associated files"""
    try:
        print(f"DEBUG: delete_textbook called with upload_id: {upload_id}")
        
        # Find the upload record
        upload = Upload.query.get(upload_id)
        if not upload:
            print(f"DEBUG: Upload {upload_id} not found")
            return jsonify({'success': False, 'error': 'Textbook not found'}), 404
        
        print(f"DEBUG: Found upload: {upload.filename}")
        
        # Delete associated files
        files_to_delete = []
        
        # Original file
        if upload.file_path and os.path.exists(upload.file_path):
            files_to_delete.append(upload.file_path)
        
        # Thumbnail file
        thumbnail_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'thumbnails')
        thumbnail_path = os.path.join(thumbnail_dir, f"{upload_id}_thumb.png")
        if os.path.exists(thumbnail_path):
            files_to_delete.append(thumbnail_path)
        
        # Try alternative paths based on filename
        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        alt_paths = [
            os.path.join(upload_dir, f"{upload_id}_{upload.filename}"),
            os.path.join(upload_dir, upload.filename)
        ]
        
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                files_to_delete.append(alt_path)
        
        # Delete files
        deleted_files = []
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                deleted_files.append(file_path)
                print(f"DEBUG: Deleted file: {file_path}")
            except Exception as e:
                print(f"DEBUG: Failed to delete file {file_path}: {e}")
        
        # Delete database record
        db.session.delete(upload)
        db.session.commit()
        
        print(f"DEBUG: Successfully deleted upload {upload_id}")
        print(f"DEBUG: Deleted files: {deleted_files}")
        
        return jsonify({
            'success': True, 
            'message': 'Textbook deleted successfully',
            'deleted_files': len(deleted_files)
        })
        
    except Exception as e:
        print(f"ERROR: Failed to delete textbook {upload_id}: {e}")
        import traceback
        traceback.print_exc()
        
        # Rollback database changes
        db.session.rollback()
        
        return jsonify({
            'success': False, 
            'error': f'Failed to delete textbook: {str(e)}'
        }), 500

@main.route("/textbook/<int:upload_id>/gcode", methods=['GET'])
def download_gcode(upload_id):
    """Generate and download G-code for 3D printing Braille text"""
    try:
        print(f"DEBUG: download_gcode called with upload_id: {upload_id}")
        
        # Find the upload record
        upload = Upload.query.get_or_404(upload_id)
        print(f"DEBUG: Found upload: {upload.filename}")
        
        # Get braille text
        braille_text = upload.braille_text or upload.braille_content
        if not braille_text:
            print("DEBUG: No braille text available, generating on-the-fly")
            
            # Generate braille text on-the-fly if not available
            display_text = upload.optimized_text if upload.optimized_text else upload.text_content
            if not display_text:
                return jsonify({'error': 'No text content available for G-code generation'}), 400
            
            try:
                from .services import BrailleConversionService
                braille_service = BrailleConversionService()
                result = braille_service.convert_to_braille(display_text, grade=2)
                
                if result.get('status') == 'success':
                    braille_text = result.get('braille_text', '')
                else:
                    return jsonify({'error': f'Braille conversion failed: {result.get("error")}'}), 500
            except Exception as e:
                return jsonify({'error': f'Braille conversion error: {str(e)}'}), 500
        
        # Generate G-code
        try:
            from .services import GCodeGenerationService
            gcode_service = GCodeGenerationService()
            
            # Get printer settings from request parameters
            settings = {}
            if request.args.get('speed'):
                settings['speed'] = int(request.args.get('speed'))
            if request.args.get('head_down'):
                settings['head_down_position'] = float(request.args.get('head_down'))
            if request.args.get('head_up'):
                settings['head_up_position'] = float(request.args.get('head_up'))
            
            result = gcode_service.generate_gcode(braille_text, settings)
            
            if result.get('status') != 'success':
                return jsonify({'error': f'G-code generation failed: {result.get("error")}'}), 500
            
            gcode = result.get('gcode', '')
            dimensions = result.get('dimensions', {})
            stats = result.get('stats', {})
            
            print(f"DEBUG: G-code generated successfully")
            print(f"DEBUG: Dimensions: {dimensions}")
            print(f"DEBUG: Stats: {stats}")
            
            # Create filename
            safe_filename = secure_filename(upload.filename or 'braille_text')
            if safe_filename.endswith('.pdf'):
                safe_filename = safe_filename[:-4]
            gcode_filename = f"{safe_filename}_braille.gcode"
            
            # Create response with G-code file
            response = current_app.response_class(
                gcode,
                mimetype='text/plain',
                headers={
                    'Content-Disposition': f'attachment; filename="{gcode_filename}"',
                    'Content-Type': 'text/plain; charset=utf-8'
                }
            )
            
            print(f"DEBUG: Sending G-code file: {gcode_filename}")
            return response
            
        except Exception as e:
            print(f"ERROR: G-code generation failed: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'G-code generation error: {str(e)}'}), 500
            
    except Exception as e:
        print(f"ERROR: Failed to generate G-code for upload {upload_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate G-code: {str(e)}'}), 500

@main.route("/textbook/<int:upload_id>/gcode/preview", methods=['GET'])
def preview_gcode(upload_id):
    """Preview G-code generation details without downloading"""
    try:
        upload = Upload.query.get_or_404(upload_id)
        
        # Get braille text
        braille_text = upload.braille_text or upload.braille_content
        if not braille_text:
            # Generate braille text on-the-fly
            display_text = upload.optimized_text if upload.optimized_text else upload.text_content
            if not display_text:
                return jsonify({'error': 'No text content available'}), 400
            
            from .services import BrailleConversionService
            braille_service = BrailleConversionService()
            result = braille_service.convert_to_braille(display_text, grade=2)
            
            if result.get('status') == 'success':
                braille_text = result.get('braille_text', '')
            else:
                return jsonify({'error': f'Braille conversion failed: {result.get("error")}'}), 500
        
        # Generate G-code preview
        from .services import GCodeGenerationService
        gcode_service = GCodeGenerationService()
        result = gcode_service.generate_gcode(braille_text)
        
        if result.get('status') != 'success':
            return jsonify({'error': f'G-code generation failed: {result.get("error")}'}), 500
        
        # Return preview information
        return jsonify({
            'success': True,
            'dimensions': result.get('dimensions', {}),
            'settings': result.get('settings', {}),
            'stats': result.get('stats', {}),
            'gcode_preview': result.get('gcode', '')[:500] + '...' if len(result.get('gcode', '')) > 500 else result.get('gcode', '')
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to preview G-code: {str(e)}'}), 500
