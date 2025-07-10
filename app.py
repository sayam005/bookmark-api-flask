from flask import Flask
from flasgger import Swagger
from config import config_by_name
from extensions import db, migrate, jwt

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Bind extensions to the app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Initialize Swagger UI with Flasgger
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs/"
    }
    
    template = {
        "swagger": "2.0",
        "info": {
            "title": "Bookmarks API",
            "description": "A simple bookmarks API with user authentication",
            "version": "1.0"
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
            }
        },
    }

    swagger = Swagger(app, config=swagger_config, template=template)

    # Import and register blueprints
    from blueprints.auth import auth_bp
    from blueprints.bookmarks import bookmarks_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(bookmarks_bp, url_prefix='/bookmarks')

    # Import models to ensure they are registered with SQLAlchemy
    from models import User, Bookmark

    return app

if __name__ == '__main__':
    app = create_app()
    app.run()
