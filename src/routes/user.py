from flask import Blueprint, jsonify, request
from src.models.models import User, db

user_bp = Blueprint('user', __name__)

@user_bp.route('/', methods=['GET'])
def get_users():
    users = User.query.filter_by(is_active=True).all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    
    # Update user fields
    user.first_name = data.get('first_name', user.first_name)
    user.last_name = data.get('last_name', user.last_name)
    user.bio = data.get('bio', user.bio)
    user.college = data.get('college', user.college)
    user.major = data.get('major', user.major)
    user.year = data.get('year', user.year)
    user.skills = data.get('skills', user.skills)
    user.github_url = data.get('github_url', user.github_url)
    user.linkedin_url = data.get('linkedin_url', user.linkedin_url)
    user.portfolio_url = data.get('portfolio_url', user.portfolio_url)
    
    db.session.commit()
    return jsonify(user.to_dict())

@user_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    return '', 204

@user_bp.route('/<int:user_id>/communities', methods=['GET'])
def get_user_communities(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify([community.to_dict() for community in user.communities])

@user_bp.route('/<int:user_id>/projects', methods=['GET'])
def get_user_projects(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify([project.to_dict() for project in user.projects])

@user_bp.route('/<int:user_id>/events', methods=['GET'])
def get_user_events(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify([event.to_dict() for event in user.events])
