#!/usr/bin/env python3
import os
import sys

print("=== ENVIRONMENT INFORMATION ===")
print(f"Current directory: {os.getcwd()}")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path}")
print(f"Directory contents: {os.listdir('.')}")

try:
    print("\n=== IMPORTING MODULES ===")
    print("Trying to import main module...")
    import main
    print("✅ main module imported successfully")
    print(f"main.__file__: {main.__file__}")
    
    print("\nTrying to access app object...")
    app = main.app
    print("✅ app object found in main module")
    print(f"app type: {type(app)}")
    
    print("\nTrying to import app.api.api module...")
    import app.api.api
    print("✅ app.api.api module imported successfully")
    
except Exception as e:
    print(f"❌ ERROR: {e.__class__.__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n=== TEST COMPLETE ===") 