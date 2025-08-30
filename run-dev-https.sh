#!/bin/bash
# Run My Pool - HTTPS Development Server
# This script runs the FastAPI application with SSL support for local development.

set -euo pipefail

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
CERT_DIR="$PROJECT_ROOT/certs"

echo -e "${BLUE}🚀 Starting Run My Pool HTTPS Development Server...${NC}"
echo -e "${BLUE}📁 Project root: ${PROJECT_ROOT}${NC}"

# Check if certificates exist
if [[ ! -f "$CERT_DIR/cert.pem" ]] || [[ ! -f "$CERT_DIR/key.pem" ]]; then
    echo -e "${RED}❌ SSL certificates not found!${NC}"
    echo -e "${YELLOW}Generating self-signed certificates...${NC}"
    
    # Create certs directory if it doesn't exist
    mkdir -p "$CERT_DIR"
    
    # Generate self-signed certificate
    openssl req -x509 -newkey rsa:4096 \
        -keyout "$CERT_DIR/key.pem" \
        -out "$CERT_DIR/cert.pem" \
        -days 365 -nodes \
        -subj "/C=US/ST=California/L=San Francisco/O=RunMyPool/OU=Development/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,DNS:127.0.0.1,IP:127.0.0.1"
    
    echo -e "${GREEN}✅ SSL certificates generated successfully!${NC}"
fi

echo -e "${GREEN}🔒 SSL Certificate: ${CERT_DIR}/cert.pem${NC}"
echo -e "${GREEN}🔑 SSL Private Key: ${CERT_DIR}/key.pem${NC}"
echo -e "${GREEN}🌐 Server will be available at: https://localhost:8000${NC}"
echo -e "${YELLOW}⚠️  You may need to accept the self-signed certificate in your browser${NC}"
echo ""

# Load environment variables
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    echo -e "${BLUE}📄 Loading environment variables from .env${NC}"
    set -a  # Automatically export all variables
    source "$PROJECT_ROOT/.env"
    set +a  # Stop automatically exporting
fi

# Activate virtual environment if it exists
if [[ -f "$PROJECT_ROOT/venv/bin/activate" ]]; then
    echo -e "${BLUE}🐍 Activating Python virtual environment${NC}"
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Install python-dotenv if not already installed
pip install python-dotenv >/dev/null 2>&1 || true

# Run the HTTPS server
echo -e "${GREEN}🚀 Starting HTTPS server...${NC}"
uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --ssl-certfile "$CERT_DIR/cert.pem" \
    --ssl-keyfile "$CERT_DIR/key.pem" \
    --reload
