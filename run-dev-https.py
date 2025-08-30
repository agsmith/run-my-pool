#!/usr/bin/env python3
"""
Run My Pool - HTTPS Development Server
This script runs the FastAPI application with SSL support for local development.
"""

import uvicorn
import os
from pathlib import Path

def main():
    # Get the project root directory
    project_root = Path(__file__).parent
    cert_dir = project_root / "certs"
    
    # SSL certificate paths
    ssl_certfile = cert_dir / "cert.pem"
    ssl_keyfile = cert_dir / "key.pem"
    
    # Verify certificate files exist
    if not ssl_certfile.exists():
        print(f"❌ SSL certificate not found: {ssl_certfile}")
        print("Run the following command to generate certificates:")
        print("openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes")
        return
    
    if not ssl_keyfile.exists():
        print(f"❌ SSL private key not found: {ssl_keyfile}")
        return
    
    print("🚀 Starting Run My Pool HTTPS development server...")
    print(f"📁 Project root: {project_root}")
    print(f"🔒 SSL Certificate: {ssl_certfile}")
    print(f"🔑 SSL Private Key: {ssl_keyfile}")
    print("🌐 Server will be available at: https://localhost:8000")
    print("⚠️  You may need to accept the self-signed certificate in your browser")
    print("")
    
    # Load environment variables from .env file if it exists
    env_file = project_root / ".env"
    if env_file.exists():
        print(f"📄 Loading environment from: {env_file}")
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    # Run the server with SSL
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        ssl_certfile=str(ssl_certfile),
        ssl_keyfile=str(ssl_keyfile),
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
