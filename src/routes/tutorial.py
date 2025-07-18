from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.models import Tutorial, db
import json

tutorial_bp = Blueprint('tutorial', __name__)

@tutorial_bp.route('/', methods=['GET'])
def get_tutorials():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        category = request.args.get('category')
        difficulty = request.args.get('difficulty')
        
        query = Tutorial.query
        
        if category:
            query = query.filter_by(category=category)
        
        if difficulty:
            query = query.filter_by(difficulty=difficulty)
        
        tutorials = query.order_by(Tutorial.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'tutorials': [tutorial.to_dict() for tutorial in tutorials.items],
            'total': tutorials.total,
            'pages': tutorials.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/<int:tutorial_id>', methods=['GET'])
def get_tutorial(tutorial_id):
    try:
        tutorial = Tutorial.query.get_or_404(tutorial_id)
        return jsonify(tutorial.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/', methods=['POST'])
@jwt_required()
def create_tutorial():
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        if not data.get('title'):
            return jsonify({'error': 'Tutorial title is required'}), 400
        
        tutorial = Tutorial(
            title=data['title'],
            description=data.get('description', ''),
            content=data.get('content', ''),
            category=data.get('category', ''),
            difficulty=data.get('difficulty', 'beginner'),
            duration=data.get('duration', ''),
            tags=json.dumps(data.get('tags', [])),
            video_url=data.get('video_url', ''),
            external_url=data.get('external_url', ''),
            image_url=data.get('image_url', ''),
            created_by=current_user_id
        )
        
        db.session.add(tutorial)
        db.session.commit()
        
        return jsonify(tutorial.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/<int:tutorial_id>', methods=['PUT'])
@jwt_required()
def update_tutorial(tutorial_id):
    try:
        current_user_id = get_jwt_identity()
        tutorial = Tutorial.query.get_or_404(tutorial_id)
        
        if tutorial.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        
        tutorial.title = data.get('title', tutorial.title)
        tutorial.description = data.get('description', tutorial.description)
        tutorial.content = data.get('content', tutorial.content)
        tutorial.category = data.get('category', tutorial.category)
        tutorial.difficulty = data.get('difficulty', tutorial.difficulty)
        tutorial.duration = data.get('duration', tutorial.duration)
        tutorial.tags = json.dumps(data.get('tags', json.loads(tutorial.tags or '[]')))
        tutorial.video_url = data.get('video_url', tutorial.video_url)
        tutorial.external_url = data.get('external_url', tutorial.external_url)
        tutorial.image_url = data.get('image_url', tutorial.image_url)
        
        db.session.commit()
        
        return jsonify(tutorial.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/<int:tutorial_id>', methods=['DELETE'])
@jwt_required()
def delete_tutorial(tutorial_id):
    try:
        current_user_id = get_jwt_identity()
        tutorial = Tutorial.query.get_or_404(tutorial_id)
        
        if tutorial.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        db.session.delete(tutorial)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/categories', methods=['GET'])
def get_tutorial_categories():
    try:
        categories = db.session.query(Tutorial.category).distinct().filter(Tutorial.category != '').all()
        return jsonify([category[0] for category in categories]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/search', methods=['GET'])
def search_tutorials():
    try:
        query = request.args.get('q', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        tutorials = Tutorial.query.filter(
            Tutorial.title.contains(query) | 
            Tutorial.description.contains(query) |
            Tutorial.tags.contains(query)
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'tutorials': [tutorial.to_dict() for tutorial in tutorials.items],
            'total': tutorials.total,
            'pages': tutorials.pages,
            'current_page': page,
            'query': query
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

