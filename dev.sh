#!/bin/bash
# Start the dev server + admin dashboard
cd "$(dirname "$0")/.."

echo "Starting dev server at http://localhost:4321"
echo "Starting admin dashboard at http://127.0.0.1:3001"

# Start dashboard in background
.venv/bin/python admin/app.py &
DASHBOARD_PID=$!

# Start Astro dev server
npx astro dev

# Cleanup
kill $DASHBOARD_PID 2>/dev/null