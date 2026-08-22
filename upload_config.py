import os
import secrets
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_upload_config(app):
    upload_folder = os.path.join(app.root_path, 'static', 'admin', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max limit

def save_uploaded_file(file, upload_folder=None):
    if not file or file.filename == '':
        return None
    if allowed_file(file.filename):
        if not upload_folder:
            upload_folder = os.path.join(os.getcwd(), 'static', 'admin', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        orig_name = secure_filename(file.filename)
        ext = orig_name.rsplit('.', 1)[1].lower() if '.' in orig_name else 'jpg'
        unique_name = f"{secrets.token_hex(6)}_{orig_name}"
        file_path = os.path.join(upload_folder, unique_name)
        file.save(file_path)
        return unique_name
    return None
