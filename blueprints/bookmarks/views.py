from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Bookmark
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
    responses:
      201:
        description: Bookmark created successfully.
      400:
        description: Bad request (e.g., URL is missing).
      401:
        description: Unauthorized (missing or invalid token).
    """
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'message': 'URL is required'}), 400

    current_user_id = get_jwt_identity()

    new_bookmark = Bookmark(
        url=url,
        body=data.get('body'),
        user_id=current_user_id
    )

    db.session.add(new_bookmark)
    db.session.commit()

    return jsonify({
        'id': new_bookmark.id,
        'url': new_bookmark.url,
        'body': new_bookmark.body,
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
            'created_at': bookmark.created_at,
            'updated_at': bookmark.updated_at
        })

    return jsonify(result), 200