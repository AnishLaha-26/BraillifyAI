#!/bin/bash

# Start the Braille API in the background
python -m app.braille_api --port 10001 & export FLASK_APP=run.py & export FLASK_ENV=production & exec gunicorn --bind 0.0.0.0:$PORT run:app
