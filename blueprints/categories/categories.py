from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Category
from extensions import db
from sqlalchemy.exc import IntegrityError

category_bp = Blueprint('categories', __name__)

@category_bp.route('/', methods=['POST'])
@jwt_required()
def create_category():
    """Create a new category
    ---
    tags:
      - categories
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name]
          properties:
            name:
              type: string
    responses:
      201:
        description: Category created successfully.
      400:
        description: Bad request (e.g., name is missing).
      409:
        description: Conflict (category with this name already exists).
    """
    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'message': 'Category name is required'}), 400

    current_user_id = get_jwt_identity()
    
    new_category = Category(name=name, user_id=current_user_id)

    try:
        db.session.add(new_category)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'Category with this name already exists for this user'}), 409

    return jsonify({'id': new_category.id, 'name': new_category.name}), 201

@category_bp.route('/', methods=['GET'])
@jwt_required()
def get_categories():
    """Get all categories for the current user
    ---
    tags:
      - categories
    security:
      - Bearer: []
    responses:
      200:
        description: A list of categories.
    """
    current_user_id = get_jwt_identity()
    categories = Category.query.filter_by(user_id=current_user_id).order_by(Category.name).all()
    return jsonify([{'id': cat.id, 'name': cat.name} for cat in categories]), 200

@category_bp.route('/<int:category_id>', methods=['GET'])
@jwt_required()
def get_category(category_id):
    """Get a single category by its ID, including its bookmarks
    ---
    tags:
      - categories
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Category details with a list of its bookmarks.
      404:
        description: Category not found.
    """
    current_user_id = get_jwt_identity()
    category = Category.query.filter_by(user_id=current_user_id, id=category_id).first()

    if not category:
        return jsonify({'message': 'Category not found'}), 404

    # Serialize bookmarks associated with this category
    bookmarks_in_category = []
    for bookmark in category.bookmarks:
        bookmarks_in_category.append({
            'id': bookmark.id,
            'url': bookmark.url,
            'body': bookmark.body,
            'short_url': bookmark.short_url,
            'visits': bookmark.visits,
            'created_at': bookmark.created_at
        })

    return jsonify({
        'id': category.id,
        'name': category.name,
        'bookmarks': bookmarks_in_category
    }), 200

@category_bp.route('/<int:category_id>', methods=['PATCH'])
@jwt_required()
def update_category(category_id):
    """Update a category name (partial update)
    ---
    tags:
      - categories
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            name:
              type: string
    responses:
      200:
        description: Category updated successfully.
      404:
        description: Category not found.
      409:
        description: Conflict (category with this name already exists).
    """
    current_user_id = get_jwt_identity()
    category = Category.query.filter_by(id=category_id, user_id=current_user_id).first()

    if not category:
        return jsonify({'message': 'Category not found'}), 404

    data = request.get_json()
    new_name = data.get('name')

    if not new_name:
        return jsonify({'message': 'New name is required'}), 400

    category.name = new_name
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'message': 'A category with this name already exists'}), 409

    return jsonify({'id': category.id, 'name': category.name}), 200

@category_bp.route('/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    """Delete a category
    ---
    tags:
      - categories
    security:
      - Bearer: []
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
    responses:
      204:
        description: Category deleted successfully.
      404:
        description: Category not found.
    """
    current_user_id = get_jwt_identity()
    category = Category.query.filter_by(id=category_id, user_id=current_user_id).first()

    if not category:
        return jsonify({'message': 'Category not found'}), 404

    db.session.delete(category)
    db.session.commit()

    return '', 204
