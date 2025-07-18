from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.models import Project, User, db
import json

project_bp = Blueprint('project', __name__)

@project_bp.route('/', methods=['GET'])
def get_projects():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        tech = request.args.get('tech')
        
        query = Project.query
        
        if status:
            query = query.filter_by(status=status)
        
        if tech:
            query = query.filter(Project.tech_stack.contains(tech))
        
        projects = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'projects': [project.to_dict() for project in projects.items],
            'total': projects.total,
            'pages': projects.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    try:
        project = Project.query.get_or_404(project_id)
        return jsonify(project.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/', methods=['POST'])
@jwt_required()
def create_project():
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        if not data.get('title'):
            return jsonify({'error': 'Project title is required'}), 400
        
        project = Project(
            title=data['title'],
            description=data.get('description', ''),
            tech_stack=json.dumps(data.get('tech_stack', [])),
            status=data.get('status', 'active'),
            github_url=data.get('github_url', ''),
            demo_url=data.get('demo_url', ''),
            image_url=data.get('image_url', ''),
            looking_for=json.dumps(data.get('looking_for', [])),
            created_by=current_user_id
        )
        
        db.session.add(project)
        db.session.commit()
        
        # Add creator as a member
        creator = User.query.get(current_user_id)
        project.members.append(creator)
        db.session.commit()
        
        return jsonify(project.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        
        if project.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        
        project.title = data.get('title', project.title)
        project.description = data.get('description', project.description)
        project.tech_stack = json.dumps(data.get('tech_stack', json.loads(project.tech_stack or '[]')))
        project.status = data.get('status', project.status)
        project.github_url = data.get('github_url', project.github_url)
        project.demo_url = data.get('demo_url', project.demo_url)
        project.image_url = data.get('image_url', project.image_url)
        project.looking_for = json.dumps(data.get('looking_for', json.loads(project.looking_for or '[]')))
        
        db.session.commit()
        
        return jsonify(project.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        
        if project.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        db.session.delete(project)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>/join', methods=['POST'])
@jwt_required()
def join_project(project_id):
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        user = User.query.get(current_user_id)
        
        if user in project.members:
            return jsonify({'error': 'Already a member of this project'}), 400
        
        project.members.append(user)
        db.session.commit()
        
        return jsonify({'message': 'Successfully joined project'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>/leave', methods=['POST'])
@jwt_required()
def leave_project(project_id):
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        user = User.query.get(current_user_id)
        
        if user not in project.members:
            return jsonify({'error': 'Not a member of this project'}), 400
        
        if project.created_by == current_user_id:
            return jsonify({'error': 'Project creator cannot leave'}), 400
        
        project.members.remove(user)
        db.session.commit()
        
        return jsonify({'message': 'Successfully left project'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>/members', methods=['GET'])
def get_project_members(project_id):
    try:
        project = Project.query.get_or_404(project_id)
        return jsonify([member.to_dict() for member in project.members]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

