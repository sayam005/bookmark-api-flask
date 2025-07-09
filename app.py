from flask import Flask
from flask_restx import Api
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from config import config_by_name

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Bind extensions to the app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    api = Api(app,
              title='Bookmarks API',
              version='1.0',
              description='A simple bookmarks API with user authentication',
              doc='/docs')

    # Import and register blueprints/namespaces here
    from blueprints.auth import auth_ns
    # from blueprints.bookmarks import bookmarks_ns
    
    api.add_namespace(auth_ns, path='/auth')
    # api.add_namespace(bookmarks_ns, path='/bookmarks')

    # Import models to ensure they are registered with SQLAlchemy
    from models import User, Bookmark

    return app

if __name__ == '__main__':
    app = create_app()
    app.run()
