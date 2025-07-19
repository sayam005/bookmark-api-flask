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
            source:
              type: string
      500:
        description: Error fetching quote from external API.
    """
    try:
        # UPDATED: New API URL
        base_url = "https://thequoteshub.com/api/random"
        
        # Make request to external API
        response = requests.get(base_url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        # THE FINAL FIX: The API returns a single object, not a list.
        # We check if it's a dictionary and has the keys 'text' and 'author'.
        if isinstance(data, dict) and 'text' in data and 'author' in data:
            return jsonify({
                'content': data['text'],  # Use the 'text' key for the quote content
                'author': data['author'],
                'source': 'The Quotes Hub API'
            }), 200

        # If the checks above fail, the format is wrong.
        return jsonify({
            'message': 'Unexpected response format from quote service',
            'error': 'The API did not return a dictionary with "text" and "author" keys.',
            'api_response': data
        }), 500
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            'message': 'Failed to fetch quote from external service',
            'error': str(e)
        }), 500