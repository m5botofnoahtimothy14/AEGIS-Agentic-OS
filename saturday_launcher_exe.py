#!/usr/bin/env python3
"""SATURDAY AI OS - Main Launcher for PyInstaller Bundle"""
import sys
import os
import uvicorn
from fastapi.staticfiles import StaticFiles

# Fix module paths for PyInstaller bundle
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = os.path.dirname(sys.executable)
    # Change to _internal where data files are (core/ui/static -> _internal/core/ui/static)
    INTERNAL_DIR = os.path.join(BUNDLE_DIR, '_internal')
    os.chdir(INTERNAL_DIR)
    sys.path.insert(0, INTERNAL_DIR)
    sys.path.insert(0, os.path.join(INTERNAL_DIR, 'core'))
    BUNDLE_DIR = INTERNAL_DIR
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BUNDLE_DIR)
    sys.path.insert(0, os.path.join(BUNDLE_DIR, 'core'))
    os.chdir(BUNDLE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BUNDLE_DIR, '.env'))

# Import core.main AFTER chdir so relative paths work
import core.main

# Patch core.main's static/template paths for PyInstaller
if getattr(sys, 'frozen', False):
    # Static files and templates are now at relative paths core/ui/
    core.main.app.mount("/static", StaticFiles(directory="core/ui/static"), name="static")
    from fastapi.templating import Jinja2Templates
    core.main.templates = Jinja2Templates(directory="core/ui/templates")
    if hasattr(core.main.app, 'templates'):
        core.main.app.templates = core.main.templates

from core.main import app

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
        app,
        host='0.0.0.0',
        port=8000,
        log_level='info',
        access_log=True,
    )