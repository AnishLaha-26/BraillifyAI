#!/bin/bash

# Start the Braille API in the background
python -m app.braille_api --port 10001 &

# Start the main web application
gunicorn app:app --worker-class eventlet -w 1 --threads 2 --bind 0.0.0.0:$PORT

# Keep the container running
wait
