#!/usr/bin/env python3
"""
Clear rate limiter for development
Run this script if you get locked out during development
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from security_config import rate_limiter

def clear_rate_limiter():
    """Clear all rate limiting data"""
    rate_limiter.clear_all()
    print("✅ Rate limiter cleared successfully!")
    print("🔄 You can now access the application without rate limiting restrictions")

if __name__ == "__main__":
    clear_rate_limiter()
