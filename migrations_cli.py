from flask import Flask
from flask_migrate import Migrate
from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        from app.models import Upload  # Import all models here
        
        # Create the migrations directory and initialize it
        migrate = Migrate(app, db)
        
        # The following commands should be run manually:
        # 1. Initialize migrations: flask db init
        # 2. Create first migration: flask db migrate -m "Initial migration"
        # 3. Apply migration: flask db upgrade
        print("\nMigration Commands:")
        print("1. Initialize migrations folder:  flask db init")
        print("2. Create migration:             flask db migrate -m \"Initial migration\"")
        print("3. Apply migration:              flask db upgrade")
        print("\nRun these commands in your terminal to set up the database.")
