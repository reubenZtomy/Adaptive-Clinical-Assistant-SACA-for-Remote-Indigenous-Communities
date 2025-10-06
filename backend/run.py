#!/usr/bin/env python3
"""
Main application runner for Medical Diagnosis API
Educational example – NOT for clinical or medical use.
"""

import os
import sys
from app import create_app

def main():
    """Main application entry point"""
    
    # Get configuration from environment
    config_name = os.environ.get('FLASK_ENV', 'development')
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Create Flask app
    app = create_app(config_name)
    
    print("="*60)
    print("🏥 Medical Diagnosis API")
    print("Educational example – NOT for clinical or medical use")
    print("="*60)
    print(f"🌐 Server: http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/api")
    print(f"🔍 Health Check: http://{host}:{port}/api/health")
    print("="*60)
    
    # Run the app
    app.run(
        host=host,
        port=port,
        debug=debug
    )

if __name__ == '__main__':
    main()
