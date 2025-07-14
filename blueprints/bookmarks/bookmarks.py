from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Bookmark, Category
from extensions import db

bookmarks_bp = Blueprint('bookmarks', __name__)

@bookmarks_bp.route('/', methods=['POST'])
@jwt_required()
def create_bookmark():
    """Create a new bookmark
    This endpoint creates a new bookmark for the currently authenticated user.
    ---
    tags:
      - bookmarks
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - url
          properties:
            url:
              type: string
              description: The URL of the bookmark.
            body:
              type: string
              description: A description or notes for the bookmark.
            category_id:
              type: integer
              description: The ID of the category to assign this bookmark to.
    responses:
      201:
        description: Bookmark created successfully.
      400:
        description: Bad request (e.g., URL is missing).
      401:
        description: Unauthorized (missing or invalid token).
      404:
        description: Category not found.
    """
    data = request.get_json()
    url = data.get('url')
    category_id = data.get('category_id') # This will be None if not provided

    if not url:
        return jsonify({'message': 'URL is required'}), 400

    current_user_id = get_jwt_identity()

    # THIS IS THE FIX:
    # The code inside this 'if' block only runs when a category_id
    # is actually sent in the request.
    if category_id:
        category = Category.query.filter_by(id=category_id, user_id=current_user_id).first()
        if not category:
            # If a category_id is sent but it's invalid, we return an error.
            return jsonify({'message': 'Category not found'}), 404

    # If no category_id was sent, the code above is skipped,
    # and the bookmark is created with category_id=None.
    new_bookmark = Bookmark(
        url=url,
        body=data.get('body'),
        user_id=current_user_id,
        category_id=category_id
    )

    db.session.add(new_bookmark)
    db.session.commit()

    return jsonify({
        'id': new_bookmark.id,
        'url': new_bookmark.url,
        'body': new_bookmark.body,
        'short_url': new_bookmark.short_url,
        'visits': new_bookmark.visits,
        'category': new_bookmark.category.name if new_bookmark.category else None,
        'created_at': new_bookmark.created_at,
        'updated_at': new_bookmark.updated_at
    }), 201

@bookmarks_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_bookmarks():
    """Get all bookmarks for the current user
    This endpoint retrieves a list of all bookmarks created by the authenticated user.
    ---
    tags:
      - bookmarks
    security:
      - Bearer: []
    responses:
      200:
        description: A list of bookmarks.
      401:
        description: Unauthorized (missing or invalid token).
    """
    current_user_id = get_jwt_identity()
    bookmarks = Bookmark.query.filter_by(user_id=current_user_id).all()

    result = []
    for bookmark in bookmarks:
        result.append({
            'id': bookmark.id,
            'url': bookmark.url,
            'body': bookmark.body,
            'short_url': bookmark.short_url,
            'visits': bookmark.visits,
            'category': bookmark.category.name if bookmark.category else None,
            'created_at': bookmark.created_at,
            'updated_at': bookmark.updated_at
        })

    return jsonify(result), 200


@bookmarks_bp.route('/<int:bookmark_id>', methods=['GET'])
@jwt_required()
def get_bookmark(bookmark_id):
    """Get a single bookmark by its ID
    ---
    tags:
      - bookmarks
    security:
      - Bearer: []
    parameters:
      - name: bookmark_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Bookmark details.
      404:
        description: Bookmark not found.
    """
    current_user_id = get_jwt_identity()
    bookmark = Bookmark.query.filter_by(user_id=current_user_id, id=bookmark_id).first()

    if not bookmark:
        return jsonify({'message': 'Bookmark not found'}), 404

    return jsonify({
        'id': bookmark.id,
        'url': bookmark.url,
        'body': bookmark.body,
        'short_url': bookmark.short_url,
        'visits': bookmark.visits,
        'category': bookmark.category.name if bookmark.category else None,
        'created_at': bookmark.created_at,
        'updated_at': bookmark.updated_at
    }), 200


@bookmarks_bp.route('/<int:bookmark_id>', methods=['PATCH'])
@jwt_required()
def update_bookmark(bookmark_id):
    """Update a bookmark (partial update)
    ---
    tags:
      - bookmarks
    security:
      - Bearer: []
    parameters:
      - name: bookmark_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            url:
              type: string
            body:
              type: string
            category_id:
              type: integer
    responses:
      200:
        description: Bookmark updated successfully.
      404:
        description: Bookmark not found.
    """
    current_user_id = get_jwt_identity()
    bookmark = Bookmark.query.filter_by(user_id=current_user_id, id=bookmark_id).first()

    if not bookmark:
        return jsonify({'message': 'Bookmark not found'}), 404

    data = request.get_json()
    bookmark.url = data.get('url', bookmark.url)
    bookmark.body = data.get('body', bookmark.body)
    
    if 'category_id' in data:
        category_id = data['category_id']
        if category_id is None:
            bookmark.category_id = None
        else:
            category = Category.query.filter_by(id=category_id, user_id=current_user_id).first()
            if not category:
                return jsonify({'message': 'Category not found'}), 404
            bookmark.category_id = category_id

    db.session.commit()

    return jsonify({
        'id': bookmark.id,
        'url': bookmark.url,
        'body': bookmark.body,
        'short_url': bookmark.short_url,
        'visits': bookmark.visits,
        'category': bookmark.category.name if bookmark.category else None,
        'created_at': bookmark.created_at,
        'updated_at': bookmark.updated_at
    }), 200


@bookmarks_bp.route('/<int:bookmark_id>', methods=['DELETE'])
@jwt_required()
def delete_bookmark(bookmark_id):
    """Delete a bookmark
    ---
    tags:
      - bookmarks
    security:
      - Bearer: []
    parameters:
      - name: bookmark_id
        in: path
        type: integer
        required: true
    responses:
      204:
        description: Bookmark deleted successfully.
      404:
        description: Bookmark not found.
    """
    current_user_id = get_jwt_identity()
    bookmark = Bookmark.query.filter_by(user_id=current_user_id, id=bookmark_id).first()

    if not bookmark:
        return jsonify({'message': 'Bookmark not found'}), 404

    db.session.delete(bookmark)
    db.session.commit()

    return '', 204