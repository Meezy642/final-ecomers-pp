import os
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, upload_folder=None):
    if not file or file.filename == '':
        return None
        
    if allowed_file(file.filename):
        if not upload_folder:
            upload_folder = current_app.config.get('UPLOAD_FOLDER') or os.path.join(os.getcwd(), 'static', 'uploads')
            
        os.makedirs(upload_folder, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Mirror to static/admin/uploads for compatibility
        admin_uploads = os.path.join(os.getcwd(), 'static', 'admin', 'uploads')
        os.makedirs(admin_uploads, exist_ok=True)
        try:
            import shutil
            shutil.copy2(file_path, os.path.join(admin_uploads, filename))
        except Exception:
            pass
            
        return filename
    return None
