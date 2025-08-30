# SSL Certificate Setup for Local Development

This directory contains SSL certificates for running the Run My Pool application with HTTPS support in local development.

## Files

- `cert.pem` - Self-signed SSL certificate (safe to commit)
- `key.pem` - Private key file (DO NOT COMMIT - excluded by .gitignore)

## Usage

### Option 1: Use the HTTPS Development Scripts

The easiest way to run the application with HTTPS:

```bash
# Shell script version (recommended)
./run-dev-https.sh

# Python script version
python run-dev-https.py
```

### Option 2: Manual uvicorn with SSL

```bash
# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(cat .env | xargs)

# Run with SSL
uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --ssl-certfile certs/cert.pem \
    --ssl-keyfile certs/key.pem \
    --reload
```

## Certificate Details

- **Valid for**: 365 days from generation
- **Common Name**: localhost
- **Subject Alternative Names**: 
  - DNS: localhost
  - DNS: 127.0.0.1
  - IP: 127.0.0.1

## Browser Security Warning

Since this is a self-signed certificate, your browser will show a security warning. This is expected and safe for local development. To proceed:

1. **Chrome/Edge**: Click "Advanced" → "Proceed to localhost (unsafe)"
2. **Firefox**: Click "Advanced" → "Accept the Risk and Continue"
3. **Safari**: Click "Show Details" → "visit this website"

## Regenerating Certificates

If you need to regenerate the certificates (e.g., if they expire):

```bash
cd certs

# Generate new self-signed certificate
openssl req -x509 -newkey rsa:4096 \
    -keyout key.pem \
    -out cert.pem \
    -days 365 -nodes \
    -subj "/C=US/ST=California/L=San Francisco/O=RunMyPool/OU=Development/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:127.0.0.1,IP:127.0.0.1"
```

## Security Notes

- These certificates are for **local development only**
- The private key (`key.pem`) is automatically excluded from git
- Never use self-signed certificates in production
- For production, use proper SSL certificates from a trusted CA

## Troubleshooting

### "Certificate not trusted" errors
This is normal for self-signed certificates. Accept the browser warning or add the certificate to your system's trusted store.

### "Address already in use" errors
Make sure no other server is running on port 8000:
```bash
# Kill any existing uvicorn processes
pkill -f uvicorn

# Or check what's using port 8000
lsof -i :8000
```

### SSL handshake errors
Ensure both `cert.pem` and `key.pem` files exist and have correct permissions:
```bash
ls -la certs/
# Should show:
# -rw-r--r-- cert.pem (readable by all)
# -rw------- key.pem (readable only by owner)
```
