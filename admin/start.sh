#!/bin/bash
# Start the admin dashboard
cd "$(dirname "$0")/.."
echo "Starting admin dashboard at http://127.0.0.1:3001"
.venv/bin/python admin/app.py