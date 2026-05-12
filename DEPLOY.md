# IGN2932M75 Bond Pull Data — Deployment Guide

## Requirements
- Python 3.10+
- Linux server (Ubuntu 22.04 recommended)
- Nginx (reverse proxy)
- Gunicorn (WSGI server)
- Certbot (for HTTPS / Let's Encrypt SSL)

## First-time Install on Remote Server

### 1. Install system packages
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx
```

### 2. Clone the repository
```bash
cd /opt
sudo git clone https://github.com/vandav887509/integra-royce.git bondapp
sudo chown -R $USER:$USER /opt/bondapp
cd /opt/bondapp
```

### 3. Create virtual environment and install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Upload RoyceData.csv (from Windows, run in PowerShell)
```powershell
scp C:\path\to\RoyceData.csv user@your-server:/opt/bondapp/RoyceData.csv
```

### 5. Edit credentials in app.py
```python
USERS = {
    'admin': 'your-secure-password',
}
app.secret_key = 'your-random-secret-key'
```

### 6. Test the app
```bash
source venv/bin/activate
python app.py
# Visit http://chart.integratech.com
```

### 7. Run with Gunicorn (production)
```bash
source venv/bin/activate
gunicorn -w 2 -b 127.0.0.1:5000 app:app
```

### 8. Configure Nginx (HTTP only — before SSL)
```bash
sudo nano /etc/nginx/sites-available/bondapp
```
Paste:
```nginx
server {
    listen 80;
    server_name chart.integratech.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
```bash
sudo ln -s /etc/nginx/sites-available/bondapp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

### 9. Obtain SSL certificate with Certbot
```bash
sudo certbot --nginx -d chart.integratech.com
```
Certbot will:
- Automatically obtain a free Let's Encrypt certificate
- Update your Nginx config to serve HTTPS on port 443
- Add an HTTP → HTTPS redirect

When prompted, choose **option 2: Redirect** to force all HTTP traffic to HTTPS.

After this step, your Nginx config will look like:
```nginx
server {
    listen 80;
    server_name chart.integratech.com;
    return 301 https://$host$request_uri;  # HTTP → HTTPS redirect
}

server {
    listen 443 ssl;
    server_name chart.integratech.com;

    ssl_certificate /etc/letsencrypt/live/chart.integratech.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chart.integratech.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 10. Verify HTTPS auto-renewal
Let's Encrypt certificates expire every 90 days. Certbot installs a cron job / systemd timer to renew automatically. Verify it works:
```bash
sudo certbot renew --dry-run
```

### 11. Run Gunicorn as a system service
```bash
sudo nano /etc/systemd/system/bondapp.service
```
Paste:
```ini
[Unit]
Description=IGN2932M75 Bond Pull Data App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/bondapp
ExecStart=/opt/bondapp/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable bondapp
sudo systemctl start bondapp
sudo systemctl status bondapp
```

---

## Updating the App (after code changes)

```bash
cd /opt/bondapp
git pull origin main
sudo systemctl restart bondapp
```

---

## Updating the Data (upload new RoyceData.csv)

From Windows PowerShell:
```powershell
scp C:\path\to\RoyceData.csv user@your-server:/opt/bondapp/RoyceData.csv
```
No restart needed — the app reads the CSV fresh on every page load.

---

## Useful commands

```bash
# Check app status
sudo systemctl status bondapp

# View live logs
sudo journalctl -u bondapp -f

# Restart app
sudo systemctl restart bondapp

# Stop app
sudo systemctl stop bondapp

# Check SSL certificate status
sudo certbot certificates

# Manually renew SSL certificate
sudo certbot renew
```
