import os
from app import create_app, db

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Only use the Flask development server if not in production
    if os.environ.get('FLASK_ENV') != 'production':
        app.run(host='0.0.0.0', port=port, debug=True)
    else:
        # In production, Gunicorn will be used
        app.run(host='0.0.0.0', port=port)
