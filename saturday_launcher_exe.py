#!/usr/bin/env python3
"""SATURDAY AI OS - Main Launcher for PyInstaller Bundle"""
import sys
import os
import uvicorn

# Fix module paths for PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    BUNDLE_DIR = os.path.dirname(sys.executable)
    # The core module is in _internal/
    sys.path.insert(0, os.path.join(BUNDLE_DIR, '_internal'))
    sys.path.insert(0, os.path.join(BUNDLE_DIR, '_internal', 'core'))
    os.chdir(BUNDLE_DIR)
else:
    # Running from source
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BUNDLE_DIR)
    sys.path.insert(0, os.path.join(BUNDLE_DIR, 'core'))
    os.chdir(BUNDLE_DIR)

# Ensure core can be imported
try:
    import core.main
    print("core.main imported successfully")
except ImportError as e:
    print(f"Failed to import core.main: {e}")
    print(f"sys.path: {sys.path}")
    print(f"BUNDLE_DIR: {BUNDLE_DIR}")
    print(f"Contents of _internal: {os.listdir(os.path.join(BUNDLE_DIR, '_internal')) if os.path.exists(os.path.join(BUNDLE_DIR, '_internal')) else 'NOT FOUND'}")
    raise

from dotenv import load_dotenv
load_dotenv(os.path.join(BUNDLE_DIR, '.env'))

print("=" * 60)
print("   SATURDAY AI OS v2.0 - Deep Learning Powered")
print("   All Systems Operational")
print("=" * 60)
print()
print(f"   Bundle Dir: {BUNDLE_DIR}")
print(f"   Python:     {sys.version}")
print(f"   Platform:   {sys.platform}")
print()

if __name__ == '__main__':
    uvicorn.run(
        'core.main:app',
        host='0.0.0.0',
        port=8000,
        log_level='info',
        access_log=True,
    )