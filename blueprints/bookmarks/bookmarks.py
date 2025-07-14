from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Bookmark, Category, User
from extensions import db

bookmarks_bp = Blueprint('bookmarks', __name__)

@bookmarks_bp.route('/', methods=['POST'])
@jwt_required()
def create_bookmark():
    """Create a new bookmark.
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
          required: [url]
          properties:
            url:
              type: string
            body:
              type: string
            category_id:
              type: integer
    responses:
      201:
        description: Bookmark created successfully.
      400:
        description: Bad request (e.g., URL is missing).
      401:
        description: Unauthorized (Missing or invalid token).
      403:
        description: Forbidden, the category does not exist or you do not have access to it.
    """
    data = request.get_json()
    url = data.get('url')
    category_id = data.get('category_id')

    if not url:
        return jsonify({'message': 'URL is required'}), 400

    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if category_id:
        # Check if user has access through collaboration OR if category is public
        category = user.shared_categories.filter(Category.id == category_id).first()
        
        if not category:
            # Check if it's a public category
            public_category = Category.query.filter_by(id=category_id, is_public=True).first()
            if not public_category:
                return jsonify({'message': 'Category not found or you do not have access to it'}), 403
            # If it's public, we can proceed

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
    """Get all bookmarks for the current user, with optional search
    ---
    tags:
      - bookmarks
    security:
      - Bearer: []
    parameters:
      - name: q
        in: query
        type: string
        required: false
        description: Search term to filter bookmarks by URL or body.
    responses:
      200:
        description: A list of bookmarks.
      401:
        description: Unauthorized (Missing or invalid token).
    """
    current_user_id = get_jwt_identity()
    query = Bookmark.query.filter_by(user_id=current_user_id)

    search_term = request.args.get('q')
    if search_term:
        # Filter by URL or body, case-insensitive
        query = query.filter(
            db.or_(
                Bookmark.url.ilike(f'%{search_term}%'),
                Bookmark.body.ilike(f'%{search_term}%')
            )
        )

    bookmarks = query.all()

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
    """Update a bookmark. Only the bookmark creator can do this.
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
      403:
        description: Forbidden, you did not create this bookmark or do not have access to the new category.
      404:
        description: Bookmark or new category not found.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    # Find the bookmark and ensure the current user is its creator
    bookmark = Bookmark.query.filter_by(id=bookmark_id, user_id=current_user_id).first()

    if not bookmark:
        return jsonify({'message': 'Bookmark not found or you are not the owner'}), 403

    data = request.get_json()
    bookmark.url = data.get('url', bookmark.url)
    bookmark.body = data.get('body', bookmark.body)
    
    if 'category_id' in data:
        new_category_id = data['category_id']
        if new_category_id is None:
            bookmark.category_id = None
        else:
            # Check if the user has access to the new category through collaboration OR if it's public
            new_category = user.shared_categories.filter(Category.id == new_category_id).first()
            if not new_category:
                # Check if it's a public category
                public_category = Category.query.filter_by(id=new_category_id, is_public=True).first()
                if not public_category:
                    return jsonify({'message': 'New category not found or you do not have access to it'}), 403
            bookmark.category_id = new_category_id

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

@bookmarks_bp.route('/public', methods=['GET'])
def get_public_bookmarks():
    """Get bookmarks from public categories, with optional search and filtering.
    ---
    tags:
      - bookmarks
    parameters:
      - name: q
        in: query
        type: string
        required: false
        description: Search term to filter bookmarks by URL or body.
      - name: category_id
        in: query
        type: integer
        required: false
        description: Filter bookmarks by public category ID.
      - name: limit
        in: query
        type: integer
        required: false
        description: Maximum number of bookmarks to return (default 50).
      - name: offset
        in: query
        type: integer
        required: false
        description: Number of bookmarks to skip for pagination (default 0).
    responses:
      200:
        description: A list of public bookmarks.
        schema:
          type: object
          properties:
            bookmarks:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  url:
                    type: string
                  body:
                    type: string
                  category:
                    type: string
                  owner:
                    type: string
                  created_at:
                    type: string
            total:
              type: integer
    """
    # Start with bookmarks in public categories
    query = Bookmark.query.join(Category).filter(Category.is_public == True)

    # Filter by category if specified
    category_id = request.args.get('category_id')
    if category_id:
        query = query.filter(Category.id == category_id)

    # Search functionality
    search_term = request.args.get('q')
    if search_term:
        query = query.filter(
            db.or_(
                Bookmark.url.ilike(f'%{search_term}%'),
                Bookmark.body.ilike(f'%{search_term}%')
            )
        )

    # Pagination
    limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 items
    offset = int(request.args.get('offset', 0))
    
    total = query.count()
    bookmarks = query.offset(offset).limit(limit).all()

    result = []
    for bookmark in bookmarks:
        result.append({
            'id': bookmark.id,
            'url': bookmark.url,
            'body': bookmark.body,
            'category': bookmark.category.name if bookmark.category else None,
            'owner': bookmark.owner.username,
            'created_at': bookmark.created_at
        })

    return jsonify({
        'bookmarks': result,
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200