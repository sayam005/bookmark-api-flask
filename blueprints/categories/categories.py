from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Category, User, category_collaborators, Bookmark
from config import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from utils.smtp import send_collaborator_invitation_email

category_bp = Blueprint('categories', __name__)

# This helper function is correct and matches your models.
def is_owner(user_id, category):
    conn = db.engine.connect()
    query = db.select(category_collaborators.c.role).where(
        db.and_(
            category_collaborators.c.user_id == user_id,
            category_collaborators.c.category_id == category.id
        )
    )
    result = conn.execute(query).scalar_one_or_none()
    conn.close()
    return result == 'owner'

@category_bp.route('/', methods=['POST'])
@jwt_required()
def create_category():
    """Create a new category, making the creator the owner.
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
            is_public:
              type: boolean
              description: Set to true to make the category public. Defaults to false.
    responses:
      201:
        description: Category created successfully.
      400:
        description: Bad request (e.g., name is missing).
      409:
        description: A category with this name already exists for this user.
    """
    data = request.get_json()
    name = data.get('name')
    is_public = data.get('is_public', False)

    if not name:
        return jsonify({'message': 'Category name is required'}), 400

    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # FIXED QUERY: This now correctly checks for ownership using the collaborators table.
    existing_category = Category.query.join(category_collaborators).filter(
        category_collaborators.c.user_id == current_user_id,
        category_collaborators.c.role == 'owner',
        Category.name == name
    ).first()

    if existing_category:
        return jsonify({'message': 'You already have a category with this name'}), 409

    # THE FIX: You must provide the user_id when creating the Category
    # because your database requires it.
    new_category = Category(name=name, is_public=is_public, user_id=current_user_id)
    
    # This part is still correct for setting up the relationship.
    new_category.collaborators.append(user)
    
    db.session.add(new_category)
    db.session.flush()

    # This correctly sets the creator's role to 'owner'.
    stmt = db.update(category_collaborators).where(
        db.and_(
            category_collaborators.c.user_id == current_user_id,
            category_collaborators.c.category_id == new_category.id
        )
    ).values(role='owner')
    db.session.execute(stmt)
    db.session.commit()

    return jsonify({'id': new_category.id, 'name': new_category.name, 'is_public': new_category.is_public}), 201

@category_bp.route('/', methods=['GET'])
@jwt_required()
def get_categories():
    """Get all categories the user owns or collaborates on, with optional search.
    ---
    tags:
      - categories
    security:
      - Bearer: []
    parameters:
      - in: query
        name: q
        description: Optional search term to filter categories by name.
    responses:
      200:
        description: A list of categories.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    query = user.shared_categories

    search_term = request.args.get('q')
    if search_term:
        query = query.filter(Category.name.ilike(f'%{search_term}%'))
    
    categories = query.all()
    
    result = [{'id': cat.id, 'name': cat.name, 'is_public': cat.is_public} for cat in categories]
    return jsonify(result), 200

@category_bp.route('/<int:category_id>', methods=['GET'])
@jwt_required()
def get_category(category_id):
    """Get a single category if the user is a collaborator.
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
        description: Category details.
      404:
        description: Category not found or access denied.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    category = user.shared_categories.filter(Category.id == category_id).first()

    if not category:
        return jsonify({'message': 'Category not found or access denied'}), 404

    return jsonify({'id': category.id, 'name': category.name, 'is_public': category.is_public}), 200

@category_bp.route('/<int:category_id>', methods=['PATCH'])
@jwt_required()
def update_category(category_id):
    """Update a category. Only the owner can do this.
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
            is_public:
              type: boolean
    responses:
      200:
        description: Category updated successfully.
      403:
        description: Forbidden, only the owner can update.
      404:
        description: Category not found.
    """
    current_user_id = get_jwt_identity()
    category = Category.query.get(category_id)

    if not category:
        return jsonify({'message': 'Category not found'}), 404

    if not is_owner(current_user_id, category):
        return jsonify({'message': 'Forbidden: Only the owner can update this category'}), 403

    data = request.get_json()
    new_name = data.get('name')

    if new_name:
        # FIXED QUERY: Checks for ownership using the collaborators table.
        existing_category = Category.query.join(category_collaborators).filter(
            category_collaborators.c.user_id == current_user_id,
            category_collaborators.c.role == 'owner',
            Category.name == new_name,
            Category.id != category_id
        ).first()
        if existing_category:
            return jsonify({'message': 'You already have a category with this name'}), 409
        category.name = new_name

    if 'is_public' in data:
        category.is_public = data.get('is_public')
    
    db.session.commit()
    return jsonify({'id': category.id, 'name': category.name, 'is_public': category.is_public}), 200

@category_bp.route('/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    """Delete a category. Only the owner can do this.
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
      403:
        description: Forbidden, only the owner can delete.
      404:
        description: Category not found.
    """
    current_user_id = get_jwt_identity()
    category = Category.query.get(category_id)

    if not category:
        return jsonify({'message': 'Category not found'}), 404

    if not is_owner(current_user_id, category):
        return jsonify({'message': 'Forbidden: Only the owner can delete this category'}), 403

    db.session.delete(category)
    db.session.commit()
    return '', 204

@category_bp.route('/<int:category_id>/collaborators', methods=['POST'])
@jwt_required()
def add_collaborator(category_id):
    """Add a collaborator to a category.
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
        required: true
        schema:
          type: object
          required: [email]
          properties:
            email:
              type: string
              description: The email of the user to add as a collaborator.
            role:
              type: string
              enum: [editor, reader]
              default: editor
              description: The role to assign to the collaborator.
    responses:
      200:
        description: Collaborator added successfully.
      400:
        description: Bad request (e.g., email is missing, invalid role).
      403:
        description: Forbidden, only the owner can add collaborators.
      404:
        description: Category or user not found.
      409:
        description: User is already a collaborator.
    """
    current_user_id = get_jwt_identity()
    category = Category.query.get(category_id)

    if not category:
        return jsonify({'message': 'Category not found'}), 404

    # Only the owner can add collaborators
    if not is_owner(current_user_id, category):
        return jsonify({'message': 'Forbidden: Only the owner can add collaborators'}), 403

    data = request.get_json()
    collaborator_email = data.get('email')
    role = data.get('role', 'editor')

    if not collaborator_email:
        return jsonify({'message': 'Collaborator email is required'}), 400
    
    if role not in ['editor', 'reader']:
        return jsonify({'message': 'Invalid role. Must be "editor" or "reader".'}), 400

    collaborator = User.query.filter_by(email=collaborator_email).first()
    if not collaborator:
        return jsonify({'message': f'User with email {collaborator_email} not found'}), 404

    # Check if the user is already a collaborator
    if collaborator in category.collaborators:
        return jsonify({'message': 'User is already a collaborator in this category'}), 409

    category.collaborators.append(collaborator)
    db.session.flush()

    # Set the specific role for the new collaborator
    stmt = db.update(category_collaborators).where(
        db.and_(
            category_collaborators.c.user_id == collaborator.id,
            category_collaborators.c.category_id == category.id
        )
    ).values(role=role)
    db.session.execute(stmt)

    # --- START OF CHANGES ---
    # 1. Ensure the category has a share token so the link will work.
    if not category.share_token:
        category.generate_share_token()
        # The commit below will also save the new collaborator relationship
    
    db.session.commit()

    # 2. After adding the collaborator, send the notification email with the share token.
    inviter = User.query.get(current_user_id)
    send_collaborator_invitation_email(
        recipient_email=collaborator.email,
        inviter_username=inviter.username,
        category_name=category.name,
        share_token=category.share_token  # Pass the share token instead of the ID
    )
    # --- END OF CHANGES ---

    return jsonify({'message': f'User {collaborator.username} added as a collaborator with role {role}'}), 200

@category_bp.route('/<int:category_id>/collaborators/<int:user_id>', methods=['DELETE'])
@jwt_required()
def remove_collaborator(category_id, user_id):
    """Remove a collaborator from a category. Only the owner can do this.
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
      - name: user_id
        in: path
        type: integer
        required: true
        description: The ID of the user to remove as collaborator
    responses:
      200:
        description: Collaborator removed successfully.
      403:
        description: Forbidden, only the owner can remove collaborators or you cannot remove the owner.
      404:
        description: Category or user not found, or user is not a collaborator.
    """
    current_user_id = get_jwt_identity()
    category = Category.query.get(category_id)

    if not category:
        return jsonify({'message': 'Category not found'}), 404

    if not is_owner(current_user_id, category):
        return jsonify({'message': 'Forbidden: Only the owner can remove collaborators'}), 403

    # Get the user to remove
    user_to_remove = User.query.get(user_id)
    if not user_to_remove:
        return jsonify({'message': 'User not found'}), 404

    # Check if the user is actually a collaborator
    if user_to_remove not in category.collaborators:
        return jsonify({'message': 'User is not a collaborator of this category'}), 404

    # Prevent removing the owner
    if is_owner(user_id, category):
        return jsonify({'message': 'Cannot remove the category owner. Transfer ownership first.'}), 403

    # Remove the collaborator
    category.collaborators.remove(user_to_remove)
    db.session.commit()

    return jsonify({'message': f'User {user_to_remove.username} removed as collaborator'}), 200

@category_bp.route('/<int:category_id>/collaborators', methods=['GET'])
@jwt_required()
def list_collaborators(category_id):
    """List all collaborators of a category.
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
        description: List of collaborators.
        schema:
          type: object
          properties:
            collaborators:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  username:
                    type: string
                  email:
                    type: string
                  role:
                    type: string
      403:
        description: Forbidden, you don't have access to this category.
      404:
        description: Category not found.
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    # Check if user has access to this category
    category = user.shared_categories.filter(Category.id == category_id).first()
    if not category:
        return jsonify({'message': 'Category not found or access denied'}), 404

    # Get all collaborators with their roles
    collaborators = []
    for collaborator in category.collaborators:
        # Get the role of this collaborator
        role_query = db.session.execute(
            db.select(category_collaborators.c.role).where(
                db.and_(
                    category_collaborators.c.user_id == collaborator.id,
                    category_collaborators.c.category_id == category.id
                )
            )
        ).scalar_one_or_none()
        
        collaborators.append({
            'id': collaborator.id,
            'username': collaborator.username,
            'email': collaborator.email,
            'role': role_query or 'editor'
        })

    return jsonify({
        'collaborators': collaborators,
        'total': len(collaborators)
    }), 200

@category_bp.route('/<int:category_id>/collaborators/<int:user_id>/role', methods=['PATCH'])
@jwt_required()
def update_collaborator_role(category_id, user_id):
    """Update a collaborator's role. Only the owner can do this.
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
      - name: user_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [role]
          properties:
            role:
              type: string
              enum: [owner, editor]
              description: The new role for the collaborator
    responses:
      200:
        description: Role updated successfully.
      403:
        description: Forbidden, only the owner can update roles.
      404:
        description: Category or user not found.
      400:
        description: Invalid role specified.
    """
    current_user_id = get_jwt_identity()
    category = Category.query.get(category_id)

    if not category:
        return jsonify({'message': 'Category not found'}), 404

    if not is_owner(current_user_id, category):
        return jsonify({'message': 'Forbidden: Only the owner can update collaborator roles'}), 403

    # Get the user whose role we're updating
    user_to_update = User.query.get(user_id)
    if not user_to_update:
        return jsonify({'message': 'User not found'}), 404

    # Check if the user is a collaborator
    if user_to_update not in category.collaborators:
        return jsonify({'message': 'User is not a collaborator of this category'}), 404

    data = request.get_json()
    new_role = data.get('role')

    if new_role not in ['owner', 'editor']:
        return jsonify({'message': 'Invalid role. Must be "owner" or "editor"'}), 400

    # If making someone else owner, demote current owner to editor AND TRANSFER OWNERSHIP
    if new_role == 'owner' and user_id != current_user_id:
        # CRUCIAL FIX: Update the main owner of the category
        category.user_id = user_id

        # Update current owner to editor
        stmt_current = db.update(category_collaborators).where(
            category_collaborators.c.user_id == current_user_id,
            category_collaborators.c.category_id == category_id
        ).values(role='editor')
        db.session.execute(stmt_current)

    # Update the target user's role
    stmt = db.update(category_collaborators).where(
        category_collaborators.c.user_id == user_id,
        category_collaborators.c.category_id == category_id
    ).values(role=new_role)
    db.session.execute(stmt)
    db.session.commit()

    return jsonify({
        'message': f'User {user_to_update.username} role updated to {new_role}'
    }), 200

@category_bp.route('/<int:category_id>/share', methods=['POST'])
@jwt_required()
def generate_share_token(category_id):
    """Generate a shareable token for read-only access to a category.
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
        description: Share token generated successfully.
        schema:
          type: object
          properties:
            share_token:
              type: string
            share_url:
              type: string
      403:
        description: Forbidden, only the owner can generate share tokens.
      404:
        description: Category not found.
    """
    current_user_id = get_jwt_identity()
    category = Category.query.get(category_id)

    if not category:
        return jsonify({'message': 'Category not found'}), 404

    if not is_owner(current_user_id, category):
        return jsonify({'message': 'Forbidden: Only the owner can generate share tokens'}), 403

    category.generate_share_token()
    db.session.commit()

    # In a real application, this would be your actual domain
    share_url = f"/shared/{category.share_token}"
    
    return jsonify({
        'share_token': category.share_token,
        'share_url': share_url
    }), 200

@category_bp.route('/<int:category_id>/share', methods=['DELETE'])
@jwt_required()
def revoke_share_token(category_id):
    """Revoke the share token for a category.
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
        description: Share token revoked successfully.
      403:
        description: Forbidden, only the owner can revoke share tokens.
      404:
        description: Category not found.
    """
    current_user_id = get_jwt_identity()
    category = Category.query.get(category_id)

    if not category:
        return jsonify({'message': 'Category not found'}), 404

    if not is_owner(current_user_id, category):
        return jsonify({'message': 'Forbidden: Only the owner can revoke share tokens'}), 403

    category.share_token = None
    db.session.commit()

    return jsonify({'message': 'Share token revoked successfully'}), 200

@category_bp.route('/shared/<string:share_token>', methods=['GET'])
def get_shared_category(share_token):
    """Get a category via its share token (read-only access).
    ---
    tags:
      - categories
    parameters:
      - name: share_token
        in: path
        type: string
        required: true
        description: The share token for the category
    responses:
      200:
        description: Category details with read-only access.
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            is_public:
              type: boolean
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
                  created_at:
                    type: string
                  owner:
                    type: string
      404:
        description: Invalid share token.
    """
    category = Category.query.filter_by(share_token=share_token).first()

    if not category:
        return jsonify({'message': 'Invalid share token'}), 404

    # Get all bookmarks in this category - FIXED: use category_bookmarks
    bookmarks = []
    for bookmark in category.bookmarks:
        bookmarks.append({
            'id': bookmark.id,
            'url': bookmark.url,
            'body': bookmark.body,
            'created_at': bookmark.created_at,
            'owner': bookmark.owner.username
        })

    return jsonify({
        'id': category.id,
        'name': category.name,
        'is_public': category.is_public,
        'bookmarks': bookmarks,
        'read_only': True  # Indicate this is read-only access
    }), 200

@category_bp.route('/public', methods=['GET'])
def get_public_categories():
    """Get all public categories for discovery.
    ---
    tags:
      - categories
    parameters:
      - name: q
        in: query
        type: string
        required: false
        description: Search term to filter categories by name.
      - name: limit
        in: query
        type: integer
        required: false
        description: Maximum number of categories to return (default 50).
      - name: offset
        in: query
        type: integer
        required: false
        description: Number of categories to skip for pagination (default 0).
    responses:
      200:
        description: A list of public categories.
    """
    # Build the optimized query that gets everything in one go
    # SIMPLIFIED QUERY: Joins on the direct user_id for ownership
    query = db.session.query(
        Category.id,
        Category.name,
        User.username.label('owner_username'),
        func.count(Bookmark.id).label('bookmark_count')
    ).select_from(Category)\
    .join(User, Category.user_id == User.id)\
    .outerjoin(Bookmark, Category.id == Bookmark.category_id)\
    .filter(Category.is_public == True)\
    .group_by(Category.id, Category.name, User.username)

    # Apply search filter if provided
    search_term = request.args.get('q')
    if search_term:
        query = query.filter(Category.name.ilike(f'%{search_term}%'))

    # Get total count before applying pagination
    total_query = query.statement.alias()
    total = db.session.query(func.count()).select_from(total_query).scalar()

    # Apply pagination
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    results = query.offset(offset).limit(limit).all()

    # Format the results
    categories = []
    for row in results:
        categories.append({
            'id': row.id,
            'name': row.name,
            'bookmark_count': row.bookmark_count,
            'owner': row.owner_username
        })

    return jsonify({
        'categories': categories,
        'total': total,
        'limit': limit,
        'offset': offset
    }), 200

@category_bp.route('/public/<int:category_id>', methods=['GET'])
def get_public_category(category_id):
    """Get a public category with its bookmarks.
    ---
    tags:
      - categories
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Public category details with bookmarks.
        schema:
          type: object
          properties:
            id:
              type: integer
            name:
              type: string
            is_public:
              type: boolean
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
                  created_at:
                    type: string
                  owner:
                    type: string
            owner:
              type: string
      404:
        description: Category not found or not public.
    """
    category = Category.query.filter_by(id=category_id, is_public=True).first()

    if not category:
        return jsonify({'message': 'Public category not found'}), 404

    # Get the owner using the direct relationship
    # SIMPLIFIED: No complex query needed
    owner_username = category.owner.username if category.owner else 'Unknown'

    # Get all bookmarks in this category
    bookmarks = []
    for bookmark in category.bookmarks:
        bookmarks.append({
            'id': bookmark.id,
            'url': bookmark.url,
            'body': bookmark.body,
            'created_at': bookmark.created_at,
            'owner': bookmark.owner.username
        })

    return jsonify({
        'id': category.id,
        'name': category.name,
        'is_public': category.is_public,
        'bookmarks': bookmarks,
        'owner': owner_username
    }), 200
