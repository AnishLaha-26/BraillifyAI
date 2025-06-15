from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
import os
from werkzeug.utils import secure_filename
import PyPDF2
import io

main = Blueprint('main', __name__)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx', 'ppt', 'pptx'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_stream):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(file_stream)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting text: {str(e)}"

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Check if files were uploaded
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            return jsonify({'error': 'No files selected'}), 400
        
        results = []
        upload_dir = os.path.join(os.getcwd(), UPLOAD_FOLDER)
        
        # Create upload directory if it doesn't exist
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        for file in files:
            if file and allowed_file(file.filename):
                # Secure the filename
                filename = secure_filename(file.filename)
                
                # Check file size
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
                
                # Process the file based on type
                file_ext = filename.rsplit('.', 1)[1].lower()
                
                if file_ext == 'pdf':
                    # Extract text from PDF
                    extracted_text = extract_text_from_pdf(file)
                    
                    # Save original file
                    file_path = os.path.join(upload_dir, filename)
                    file.seek(0)  # Reset file pointer
                    file.save(file_path)
                    
                    # Save extracted text
                    text_filename = f"{filename.rsplit('.', 1)[0]}_extracted.txt"
                    text_path = os.path.join(upload_dir, text_filename)
                    with open(text_path, 'w', encoding='utf-8') as f:
                        f.write(extracted_text)
                    
                    results.append({
                        'filename': filename,
                        'status': 'success',
                        'message': 'PDF uploaded and text extracted successfully',
                        'text_preview': extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text,
                        'file_size': f"{file_size/1024:.1f} KB",
                        'pages': len(PyPDF2.PdfReader(io.BytesIO(file.read())).pages) if file_ext == 'pdf' else None
                    })
                    
                elif file_ext == 'txt':
                    # Handle text files
                    content = file.read().decode('utf-8')
                    file_path = os.path.join(upload_dir, filename)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    results.append({
                        'filename': filename,
                        'status': 'success',
                        'message': 'Text file uploaded successfully',
                        'text_preview': content[:200] + "..." if len(content) > 200 else content,
                        'file_size': f"{file_size/1024:.1f} KB"
                    })
                    
                else:
                    # Handle other document types (doc, docx, ppt, pptx)
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    
                    results.append({
                        'filename': filename,
                        'status': 'success',
                        'message': f'{file_ext.upper()} file uploaded successfully',
                        'file_size': f"{file_size/1024:.1f} KB",
                        'note': 'Text extraction for this file type will be implemented in future updates'
                    })
                    
            else:
                results.append({
                    'filename': file.filename,
                    'status': 'error',
                    'message': 'File type not allowed. Supported types: PDF, TXT, DOC, DOCX, PPT, PPTX'
                })
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(results)} files',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500
