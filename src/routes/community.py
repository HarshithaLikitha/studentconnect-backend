from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.models import Community, User, db
import json

community_bp = Blueprint('community', __name__)

@community_bp.route('/', methods=['GET'])
def get_communities():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        category = request.args.get('category')
        
        query = Community.query
        
        if category:
            query = query.filter_by(category=category)
        
        communities = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'communities': [community.to_dict() for community in communities.items],
            'total': communities.total,
            'pages': communities.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>', methods=['GET'])
def get_community(community_id):
    try:
        community = Community.query.get_or_404(community_id)
        return jsonify(community.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/', methods=['POST'])
@jwt_required()
def create_community():
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        if not data.get('name'):
            return jsonify({'error': 'Community name is required'}), 400
        
        community = Community(
            name=data['name'],
            description=data.get('description', ''),
            category=data.get('category', ''),
            image_url=data.get('image_url', ''),
            is_private=data.get('is_private', False),
            created_by=current_user_id
        )
        
        db.session.add(community)
        db.session.commit()
        
        # Add creator as a member
        creator = User.query.get(current_user_id)
        community.members.append(creator)
        db.session.commit()
        
        return jsonify(community.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>', methods=['PUT'])
@jwt_required()
def update_community(community_id):
    try:
        current_user_id = get_jwt_identity()
        community = Community.query.get_or_404(community_id)
        
        if community.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        
        community.name = data.get('name', community.name)
        community.description = data.get('description', community.description)
        community.category = data.get('category', community.category)
        community.image_url = data.get('image_url', community.image_url)
        community.is_private = data.get('is_private', community.is_private)
        
        db.session.commit()
        
        return jsonify(community.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>', methods=['DELETE'])
@jwt_required()
def delete_community(community_id):
    try:
        current_user_id = get_jwt_identity()
        community = Community.query.get_or_404(community_id)
        
        if community.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        db.session.delete(community)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>/join', methods=['POST'])
@jwt_required()
def join_community(community_id):
    try:
        current_user_id = get_jwt_identity()
        community = Community.query.get_or_404(community_id)
        user = User.query.get(current_user_id)
        
        if user in community.members:
            return jsonify({'error': 'Already a member of this community'}), 400
        
        community.members.append(user)
        db.session.commit()
        
        return jsonify({'message': 'Successfully joined community'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>/leave', methods=['POST'])
@jwt_required()
def leave_community(community_id):
    try:
        current_user_id = get_jwt_identity()
        community = Community.query.get_or_404(community_id)
        user = User.query.get(current_user_id)
        
        if user not in community.members:
            return jsonify({'error': 'Not a member of this community'}), 400
        
        if community.created_by == current_user_id:
            return jsonify({'error': 'Community creator cannot leave'}), 400
        
        community.members.remove(user)
        db.session.commit()
        
        return jsonify({'message': 'Successfully left community'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>/members', methods=['GET'])
def get_community_members(community_id):
    try:
        community = Community.query.get_or_404(community_id)
        return jsonify([member.to_dict() for member in community.members]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

