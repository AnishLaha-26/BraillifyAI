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
                        upload.braille_content = braille_result.get('braille_text', '')
                        upload.braille_pages = braille_result.get('page_count', 0)
                    
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
                                        upload.braille_content = braille_result.get('braille_text', '')
                                        upload.braille_pages = braille_result.get('page_count', 0)
                                    
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
                                        upload.braille_content = braille_result.get('braille_text', '')
                                        upload.braille_pages = braille_result.get('page_count', 0)
                                    
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
        braille_text = upload.braille_text
        braille_grade = upload.braille_grade or 2  # Default to grade 2
        pagination = {
            'total_pages': upload.braille_pages or 0,
            'chars_per_page': upload.braille_chars_per_page or 0,
            'lines_per_page': upload.braille_lines_per_page or 0
        }

        # Convert to braille on-the-fly if not already available
        if not braille_text and display_text:
            print("DEBUG: Converting to braille on-the-fly")
            try:
                from .services import BrailleConversionService
                braille_service = BrailleConversionService()
                result = braille_service.convert_to_braille(display_text, grade=braille_grade)

                # Update database with all details
                upload.braille_text = result.get('braille_text')
                upload.braille_pages = result.get('pages')
                upload.braille_chars_per_page = result.get('chars_per_page')
                upload.braille_lines_per_page = result.get('lines_per_page')
                upload.braille_grade = result.get('grade')
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
            except Exception as e:
                print(f"Error converting to braille: {e}")
                braille_text = "Braille conversion not available"

        print("DEBUG: Rendering template with pagination")
        return render_template('textbook_view.html',
                             upload=upload,
                             textbook_title=upload.title,
                             optimized_text=display_text,
                             text_pages=text_pages,
                             braille_text=braille_text,
                             braille_grade=braille_grade,
                             pagination=pagination)

    except Exception as e:
        print(f"Error in textbook_view: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading textbook view', 'error')
        return redirect(url_for('main.index'))

def _paginate_text(text: str, words_per_page: int = 500) -> list:
    """Split text into pages for display"""
    if not text:
        return [""]
    
    words = text.split()
    pages = []
    current_page = []
    word_count = 0
    
    for word in words:
        current_page.append(word)
        word_count += 1
        
        if word_count >= words_per_page:
            pages.append(' '.join(current_page))
            current_page = []
            word_count = 0
    
    # Add remaining words as the last page
    if current_page:
        pages.append(' '.join(current_page))
    
    return pages if pages else [""]

@main.route('/textbook/<int:upload_id>', methods=['DELETE'])
def delete_textbook(upload_id):
    """Delete a textbook and its associated files"""
    try:
        upload = Upload.query.get_or_404(upload_id)
        
        # Delete associated files
        if upload.file_path and os.path.exists(upload.file_path):
            try:
                os.remove(upload.file_path)
            except Exception as e:
                print(f"Error deleting file {upload.file_path}: {e}")
        
        # Delete thumbnail if exists
        thumbnail_path = os.path.join('uploads', 'thumbnails', f"{upload_id}_thumb.png")
        if os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except Exception as e:
                print(f"Error deleting thumbnail {thumbnail_path}: {e}")
        
        # Delete from database
        db.session.delete(upload)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Textbook deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting textbook: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main.route('/update_textbook_title', methods=['POST'])
def update_textbook_title():
    """Update the textbook title"""
    try:
        data = request.get_json()
        upload_id = data.get('upload_id')
        new_title = data.get('title', '').strip()
        
        if not upload_id or not new_title:
            return jsonify({'error': 'Missing upload_id or title'}), 400
            
        upload = Upload.query.get_or_404(upload_id)
        upload.title = new_title
        db.session.commit()
        
        return jsonify({'success': True, 'title': new_title})
        
    except Exception as e:
        return jsonify({'error': f'Error updating title: {str(e)}'}), 500

@main.route('/download/original/<int:upload_id>')
def download_original(upload_id):
    """Download original uploaded file"""
    try:
        upload = Upload.query.get_or_404(upload_id)
        
        if not upload.file_path or not os.path.exists(upload.file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(upload.file_path, as_attachment=True, download_name=upload.filename)
        
    except Exception as e:
        return jsonify({'error': f'Error downloading file: {str(e)}'}), 500

@main.route('/download/optimized/<int:upload_id>')
def download_optimized(upload_id):
    """Download optimized text as file"""
    try:
        upload = Upload.query.get_or_404(upload_id)
        
        if not upload.optimized_text:
            return jsonify({'error': 'No optimized text available'}), 404
            
        # Create temporary text file
        temp_filename = f"{upload.title or 'optimized_text'}.txt"
        temp_path = os.path.join('uploads', f"temp_{upload_id}_optimized.txt")
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(upload.optimized_text)
        
        return send_file(temp_path, as_attachment=True, download_name=temp_filename)
        
    except Exception as e:
        return jsonify({'error': f'Error downloading optimized text: {str(e)}'}), 500
