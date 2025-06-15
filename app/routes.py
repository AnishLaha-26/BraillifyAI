from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
import os
from werkzeug.utils import secure_filename
import PyPDF2
import io
from . import db
from .models import Upload

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
    return render_template('index.html')

@main.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Debug logging
        print("=== UPLOAD REQUEST ===")
        print(f"request.files: {request.files}")
        print(f"request.form: {request.form}")
        print(f"request.files keys: {list(request.files.keys())}")
        
        if 'files' not in request.files:
            print("ERROR: No 'files' key in request.files")
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        upload_type = request.form.get('upload_type', 'document')
        
        print(f"Files found: {len(files)}")
        print(f"Upload type: {upload_type}")
        
        if not files or all(file.filename == '' for file in files):
            print("ERROR: No files selected or empty filenames")
            return jsonify({'error': 'No files selected'}), 400
        
        results = []
        upload_dir = os.path.join(os.getcwd(), UPLOAD_FOLDER)
        
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
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
                file_path = os.path.join(upload_dir, filename)
                
                # Create database record with correct file type
                upload = Upload(
                    filename=filename,
                    file_path=file_path,
                    file_type=get_file_type_from_upload_type(upload_type),
                    mime_type=file.content_type,
                    file_size=file_size
                )
                
                try:
                    # Handle different file types based on upload type
                    if upload_type == 'document':
                        # Process documents (PDF, TXT, etc.)
                        if file_ext == 'pdf':
                            upload.status = 'processing'
                            db.session.add(upload)
                            db.session.commit()
                            
                            # Read file content once and store in memory
                            file.seek(0)  # Ensure we're at the beginning
                            file_content = file.read()
                            
                            # Extract text from PDF using the content
                            extracted_text = extract_text_from_pdf(io.BytesIO(file_content))
                            
                            # Save the file using the same content
                            with open(file_path, 'wb') as f:
                                f.write(file_content)
                            
                            text_filename = f"{filename.rsplit('.', 1)[0]}_extracted.txt"
                            text_path = os.path.join(upload_dir, text_filename)
                            with open(text_path, 'w', encoding='utf-8') as f:
                                f.write(extracted_text)
                            
                            upload.text_content = extracted_text
                            upload.text_file_path = text_path
                            
                            # Get page count from the same content
                            try:
                                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                                upload.page_count = len(pdf_reader.pages)
                            except Exception as e:
                                print(f"Error getting page count: {e}")
                                upload.page_count = 0
                            
                            upload.status = 'completed'
                            
                            results.append({
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
                            db.session.add(upload)
                            db.session.commit()
                            
                            content = file.read().decode('utf-8')
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            
                            upload.text_content = content
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
                            db.session.add(upload)
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
                        db.session.add(upload)
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
                        db.session.add(upload)
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
