#!/usr/bin/env python3
"""
Startup script for Tactiq backend
Ensures proper Python path setup before starting uvicorn
"""

import sys
import os
from pathlib import Path

# Get the directory containing this script
script_dir = Path(__file__).parent.absolute()
backend_dir = script_dir

# Add backend directory to Python path
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Change to backend directory so imports work correctly
os.chdir(backend_dir)

# Now import and run uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_dir)],
        log_level="info"
    )
