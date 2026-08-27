#!/bin/bash
set -e

echo "=== 1. Writing systemd service ==="
cat << 'EOF' | sudo tee /etc/systemd/system/flaskapp.service > /dev/null
[Unit]
Description=Gunicorn instance to serve Flask E-commerce App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/flaskapp
Environment="PATH=/var/www/flaskapp/venv/bin"
Environment="FLASK_SECRET_KEY=super_secret_heng_key_production"
ExecStart=/var/www/flaskapp/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "=== 2. Writing Nginx config ==="
cat << 'EOF' | sudo tee /etc/nginx/sites-available/flaskapp > /dev/null
server {
    listen 80;
    server_name _;
    client_max_body_size 25M;

    location /static/ {
        alias /var/www/flaskapp/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

echo "=== 3. Setting permissions ==="
sudo mkdir -p /var/www/flaskapp/static/uploads /var/www/flaskapp/instance
sudo chown -R www-data:www-data /var/www/flaskapp/instance /var/www/flaskapp/static/uploads
sudo chmod -R 775 /var/www/flaskapp/instance /var/www/flaskapp/static/uploads

echo "=== 4. Starting services ==="
sudo systemctl daemon-reload
sudo systemctl restart flaskapp
sudo systemctl enable flaskapp

sudo ln -sf /etc/nginx/sites-available/flaskapp /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "=== DEPLOYMENT COMPLETED SUCCESSFULLY! ==="
