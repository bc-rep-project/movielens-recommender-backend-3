#!/bin/bash

echo "======== DEBUGGING INFORMATION ========"
echo "Current directory: $(pwd)"
echo "Directory listing:"
ls -la
echo "Python version: $(python --version)"
echo "Python path:"
python -c "import sys; print(sys.path)"
echo "Checking main.py:"
if [ -f "main.py" ]; then
    echo "main.py exists"
    echo "Content of main.py (first few lines):"
    head -n 10 main.py
else
    echo "ERROR: main.py does not exist!"
    echo "Looking for main.py in subdirectories:"
    find . -name "main.py" -type f
fi

echo "======== STARTING APPLICATION ========"
exec gunicorn main:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --worker-class uvicorn.workers.UvicornWorker --timeout 60 --log-level debug 