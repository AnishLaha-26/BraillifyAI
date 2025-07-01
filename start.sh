#!/bin/bash

# Start the Braille API in the background
python -m app.braille_api --port 10001 &

# Start the main web application using run.py
exec python run.py
