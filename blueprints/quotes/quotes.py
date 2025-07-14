from flask import Blueprint, jsonify, request
import requests
from flask_jwt_extended import jwt_required

quotes_bp = Blueprint('quotes', __name__)

@quotes_bp.route('/random', methods=['GET'])
@jwt_required()
def get_random_quote():
    """Get a random inspirational quote.
    ---
    tags:
      - quotes
    security:
      - Bearer: []
    parameters:
      - name: tags
        in: query
        type: string
        required: false
        description: Filter quotes by tags (e.g., 'motivational,success')
      - name: author
        in: query
        type: string
        required: false
        description: Get quotes from a specific author
    responses:
      200:
        description: A random quote.
        schema:
          type: object
          properties:
            content:
              type: string
            author:
              type: string
            tags:
              type: array
              items:
                type: string
            source:
              type: string
      500:
        description: Error fetching quote from external API.
    """
    try:
        # Build the API URL with optional parameters
        base_url = "https://api.quotable.io/random"
        params = {}
        
        if request.args.get('tags'):
            params['tags'] = request.args.get('tags')
        
        if request.args.get('author'):
            params['author'] = request.args.get('author')
        
        # Make request to external API
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        
        quote_data = response.json()
        
        return jsonify({
            'content': quote_data['content'],
            'author': quote_data['author'],
            'tags': quote_data['tags'],
            'source': 'Quotable API'
        }), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'message': 'Failed to fetch quote from external service',
            'error': str(e)
        }), 500
    except KeyError as e:
        return jsonify({
            'message': 'Unexpected response format from quote service',
            'error': f'Missing key: {str(e)}'
        }), 500

@quotes_bp.route('/authors', methods=['GET'])
@jwt_required()
def get_quote_authors():
    """Get list of available quote authors.
    ---
    tags:
      - quotes
    security:
      - Bearer: []
    parameters:
      - name: search
        in: query
        type: string
        required: false
        description: Search for authors by name
      - name: limit
        in: query
        type: integer
        required: false
        description: Limit number of results (default 20)
    responses:
      200:
        description: List of quote authors.
      500:
        description: Error fetching authors from external API.
    """
    try:
        base_url = "https://api.quotable.io/authors"
        params = {
            'limit': min(int(request.args.get('limit', 20)), 50)
        }
        
        if request.args.get('search'):
            params['query'] = request.args.get('search')
        
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        authors = []
        for author in data.get('results', []):
            authors.append({
                'name': author['name'],
                'description': author.get('description', ''),
                'quote_count': author.get('quoteCount', 0)
            })
        
        return jsonify({
            'authors': authors,
            'total': data.get('totalCount', 0)
        }), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'message': 'Failed to fetch authors from external service',
            'error': str(e)
        }), 500