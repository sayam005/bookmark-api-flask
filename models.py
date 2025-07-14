from extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# Association Table for Many-to-Many relationship between User and Category
category_collaborators = db.Table('category_collaborators',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True),
    db.Column('role', db.String(50), nullable=False, default='editor')  # 'owner' or 'editor'
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # This is the relationship to bookmarks the user has personally created.
    bookmarks = db.relationship('Bookmark', backref='owner', lazy=True, cascade="all, delete-orphan")

    # This is the new relationship for collaboration.
    shared_categories = db.relationship('Category', secondary=category_collaborators,
                                        back_populates='collaborators', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    share_token = db.Column(db.String(36), unique=True, nullable=True) # For read-only sharing
    
    # This relationship links a category to the users who have access to it
    collaborators = db.relationship('User', secondary=category_collaborators,
                                    back_populates='shared_categories', lazy='dynamic')
    
    # Relationship to bookmarks in this category
    category_bookmarks = db.relationship('Bookmark', backref='category', lazy=True, cascade="all, delete-orphan")

    def generate_share_token(self):
        if not self.share_token:
            self.share_token = str(uuid.uuid4())

    def __repr__(self):
        return f'<Category {self.name}>'

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String, nullable=True)
    url = db.Column(db.String, nullable=False)
    short_url = db.Column(db.String(10), nullable=True)
    visits = db.Column(db.Integer, default=0)
    
    # The user who created the bookmark
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # The category this bookmark belongs to
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Bookmark {self.url}>'
