import os
import secrets
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_upload_config(app):
    upload_folder = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static', 'admin', 'uploads'), exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max limit

def save_uploaded_file(file, upload_folder=None):
    if not file or file.filename == '':
        return None
    if allowed_file(file.filename):
        if not upload_folder:
            upload_folder = os.path.join(os.getcwd(), 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        orig_name = secure_filename(file.filename)
        unique_name = orig_name
        file_path = os.path.join(upload_folder, unique_name)
        file.save(file_path)
        
        # Also mirror in static/admin/uploads for template compatibility
        admin_uploads = os.path.join(os.getcwd(), 'static', 'admin', 'uploads')
        os.makedirs(admin_uploads, exist_ok=True)
        try:
            import shutil
            shutil.copy2(file_path, os.path.join(admin_uploads, unique_name))
        except Exception:
            pass
            
        return unique_name
    return None
