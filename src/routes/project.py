from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.enhanced_models import (
    Project, User, ProjectRole, ProjectApplication, db
)
from sqlalchemy import or_, and_
from datetime import datetime
import json

project_bp = Blueprint('project', __name__)

@project_bp.route('/', methods=['GET'])
def get_projects():
    """Get all projects with filtering and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        status = request.args.get('status')
        project_type = request.args.get('project_type')
        difficulty = request.args.get('difficulty')
        tech = request.args.get('tech')
        search = request.args.get('search')
        recruiting_only = request.args.get('recruiting', type=bool)
        
        query = Project.query
        
        # Apply filters
        if status:
            query = query.filter_by(status=status)
        
        if project_type:
            query = query.filter_by(project_type=project_type)
        
        if difficulty:
            query = query.filter_by(difficulty_level=difficulty)
        
        if tech:
            query = query.filter(Project.tech_stack.contains(tech))
        
        if search:
            query = query.filter(
                or_(
                    Project.title.ilike(f'%{search}%'),
                    Project.description.ilike(f'%{search}%')
                )
            )
        
        if recruiting_only:
            query = query.filter_by(is_recruiting=True)
        
        # Order by creation date and recruiting status
        query = query.order_by(
            Project.is_recruiting.desc(),
            Project.created_at.desc()
        )
        
        projects = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'projects': [project.to_dict() for project in projects.items],
            'total': projects.total,
            'pages': projects.pages,
            'current_page': page,
            'has_next': projects.has_next,
            'has_prev': projects.has_prev
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/types', methods=['GET'])
def get_project_types():
    """Get all available project types"""
    try:
        types = ['open_source', 'hackathon', 'academic', 'startup', 'personal', 'freelance']
        return jsonify({'types': types}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/technologies', methods=['GET'])
def get_popular_technologies():
    """Get popular technologies from existing projects"""
    try:
        # This would ideally be cached or pre-computed
        popular_techs = [
            'React', 'Node.js', 'Python', 'JavaScript', 'TypeScript',
            'Vue.js', 'Angular', 'Django', 'Flask', 'Express.js',
            'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Docker',
            'AWS', 'Firebase', 'GraphQL', 'REST API', 'Machine Learning',
            'TensorFlow', 'PyTorch', 'Kubernetes', 'Git', 'HTML/CSS'
        ]
        
        return jsonify({'technologies': popular_techs}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project with detailed information"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get project roles and team members
        project_roles = ProjectRole.query.filter_by(project_id=project_id).all()
        
        # Get pending applications count
        pending_applications = ProjectApplication.query.filter_by(
            project_id=project_id, status='pending'
        ).count()
        
        project_data = project.to_dict()
        project_data['team_roles'] = [role.to_dict() for role in project_roles]
        project_data['pending_applications'] = pending_applications
        
        return jsonify(project_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/', methods=['POST'])
@jwt_required()
def create_project():
    """Create a new project"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Project title is required'}), 400
        
        if not data.get('description'):
            return jsonify({'error': 'Project description is required'}), 400
        
        if not data.get('project_type'):
            return jsonify({'error': 'Project type is required'}), 400
        
        project = Project(
            title=data['title'],
            description=data['description'],
            tech_stack=json.dumps(data.get('tech_stack', [])),
            status=data.get('status', 'active'),
            github_url=data.get('github_url', ''),
            demo_url=data.get('demo_url', ''),
            image_url=data.get('image_url', ''),
            looking_for=json.dumps(data.get('looking_for', [])),
            created_by=current_user_id,
            
            # Enhanced fields
            project_type=data['project_type'],
            difficulty_level=data.get('difficulty_level', 'intermediate'),
            estimated_duration=data.get('estimated_duration', ''),
            required_skills=data.get('required_skills', []),
            current_team_size=1,  # Creator is first member
            max_team_size=data.get('max_team_size', 5),
            progress_percentage=0,
            is_recruiting=data.get('is_recruiting', True),
            tags=data.get('tags', []),
            featured_image=data.get('featured_image', ''),
            screenshots=data.get('screenshots', [])
        )
        
        db.session.add(project)
        db.session.flush()  # Get the project ID
        
        # Add creator as a member and project lead
        creator = User.query.get(current_user_id)
        project.members.append(creator)
        
        # Create project role for creator
        creator_role = ProjectRole(
            project_id=project.id,
            user_id=current_user_id,
            role_name=data.get('creator_role', 'Project Lead'),
            responsibilities='Project management, coordination, and oversight',
            is_lead=True
        )
        
        db.session.add(creator_role)
        
        # Update user's project count
        creator.total_projects = (creator.total_projects or 0) + 1
        
        db.session.commit()
        
        return jsonify(project.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    """Update a project (only by creator or project leads)"""
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        
        # Check permissions (creator or project lead)
        is_lead = ProjectRole.query.filter_by(
            project_id=project_id, user_id=current_user_id, is_lead=True
        ).first()
        
        if project.created_by != current_user_id and not is_lead:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        
        # Update fields
        if 'title' in data:
            project.title = data['title']
        if 'description' in data:
            project.description = data['description']
        if 'tech_stack' in data:
            project.tech_stack = json.dumps(data['tech_stack'])
        if 'status' in data:
            project.status = data['status']
        if 'github_url' in data:
            project.github_url = data['github_url']
        if 'demo_url' in data:
            project.demo_url = data['demo_url']
        if 'image_url' in data:
            project.image_url = data['image_url']
        if 'looking_for' in data:
            project.looking_for = json.dumps(data['looking_for'])
        if 'project_type' in data:
            project.project_type = data['project_type']
        if 'difficulty_level' in data:
            project.difficulty_level = data['difficulty_level']
        if 'estimated_duration' in data:
            project.estimated_duration = data['estimated_duration']
        if 'required_skills' in data:
            project.required_skills = data['required_skills']
        if 'max_team_size' in data:
            project.max_team_size = data['max_team_size']
        if 'progress_percentage' in data:
            project.progress_percentage = data['progress_percentage']
        if 'is_recruiting' in data:
            project.is_recruiting = data['is_recruiting']
        if 'tags' in data:
            project.tags = data['tags']
        if 'featured_image' in data:
            project.featured_image = data['featured_image']
        if 'screenshots' in data:
            project.screenshots = data['screenshots']
        
        project.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(project.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    """Delete a project (only by creator)"""
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        
        if project.created_by != current_user_id:
            return jsonify({'error': 'Only the project creator can delete it'}), 403
        
        # Update member counts
        for member in project.members:
            member.total_projects = max(0, (member.total_projects or 1) - 1)
        
        db.session.delete(project)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>/apply', methods=['POST'])
@jwt_required()
def apply_to_project(project_id):
    """Apply to join a project"""
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        user = User.query.get(current_user_id)
        
        # Check if user is already a member
        if user in project.members:
            return jsonify({'error': 'Already a member of this project'}), 400
        
        # Check if project is recruiting
        if not project.is_recruiting:
            return jsonify({'error': 'This project is not currently recruiting'}), 400
        
        # Check if team is full
        if project.current_team_size >= project.max_team_size:
            return jsonify({'error': 'Project team is full'}), 400
        
        data = request.json
        role_applied_for = data.get('role_applied_for')
        message = data.get('message', '')
        
        if not role_applied_for:
            return jsonify({'error': 'Role applied for is required'}), 400
        
        # Check if user already has a pending application
        existing_application = ProjectApplication.query.filter_by(
            project_id=project_id,
            applicant_id=current_user_id,
            status='pending'
        ).first()
        
        if existing_application:
            return jsonify({'error': 'You already have a pending application for this project'}), 400
        
        application = ProjectApplication(
            project_id=project_id,
            applicant_id=current_user_id,
            role_applied_for=role_applied_for,
            message=message,
            status='pending'
        )
        
        db.session.add(application)
        db.session.commit()
        
        return jsonify({
            'message': 'Application submitted successfully',
            'application': application.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>/applications', methods=['GET'])
@jwt_required()
def get_project_applications(project_id):
    """Get applications for a project (only for creator and leads)"""
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        
        # Check permissions
        is_lead = ProjectRole.query.filter_by(
            project_id=project_id, user_id=current_user_id, is_lead=True
        ).first()
        
        if project.created_by != current_user_id and not is_lead:
            return jsonify({'error': 'Permission denied'}), 403
        
        status_filter = request.args.get('status', 'pending')
        
        applications = ProjectApplication.query.filter_by(
            project_id=project_id,
            status=status_filter
        ).order_by(ProjectApplication.applied_at.desc()).all()
        
        return jsonify({
            'applications': [app.to_dict() for app in applications]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>/applications/<int:application_id>', methods=['PUT'])
@jwt_required()
def review_application(project_id, application_id):
    """Review a project application (accept/reject)"""
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        application = ProjectApplication.query.get_or_404(application_id)
        
        # Check permissions
        is_lead = ProjectRole.query.filter_by(
            project_id=project_id, user_id=current_user_id, is_lead=True
        ).first()
        
        if project.created_by != current_user_id and not is_lead:
            return jsonify({'error': 'Permission denied'}), 403
        
        if application.project_id != project_id:
            return jsonify({'error': 'Application does not belong to this project'}), 400
        
        data = request.json
        action = data.get('action')  # 'accept' or 'reject'
        
        if action not in ['accept', 'reject']:
            return jsonify({'error': 'Action must be either "accept" or "reject"'}), 400
        
        if action == 'accept':
            # Check if team is full
            if project.current_team_size >= project.max_team_size:
                return jsonify({'error': 'Project team is full'}), 400
            
            # Add user to project
            applicant = User.query.get(application.applicant_id)
            project.members.append(applicant)
            project.current_team_size += 1
            
            # Create project role
            project_role = ProjectRole(
                project_id=project_id,
                user_id=application.applicant_id,
                role_name=application.role_applied_for,
                responsibilities=data.get('responsibilities', ''),
                is_lead=False
            )
            
            db.session.add(project_role)
            
            # Update user's project count
            applicant.total_projects = (applicant.total_projects or 0) + 1
            
            application.status = 'accepted'
        else:
            application.status = 'rejected'
        
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = current_user_id
        
        db.session.commit()
        
        return jsonify({
            'message': f'Application {action}ed successfully',
            'application': application.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>/members', methods=['GET'])
def get_project_members(project_id):
    """Get project members with their roles"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get all project roles
        project_roles = ProjectRole.query.filter_by(project_id=project_id).all()
        
        members_data = []
        for role in project_roles:
            member_data = role.user.to_dict()
            member_data['project_role'] = {
                'role_name': role.role_name,
                'responsibilities': role.responsibilities,
                'is_lead': role.is_lead,
                'joined_at': role.joined_at.isoformat() if role.joined_at else None
            }
            member_data['is_creator'] = role.user.id == project.created_by
            members_data.append(member_data)
        
        return jsonify({'members': members_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>/members/<int:user_id>', methods=['DELETE'])
@jwt_required()
def remove_member(project_id, user_id):
    """Remove a member from the project"""
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        
        # Check permissions (creator or project leads)
        is_lead = ProjectRole.query.filter_by(
            project_id=project_id, user_id=current_user_id, is_lead=True
        ).first()
        
        if project.created_by != current_user_id and not is_lead:
            return jsonify({'error': 'Permission denied'}), 403
        
        if user_id == project.created_by:
            return jsonify({'error': 'Cannot remove project creator'}), 400
        
        user = User.query.get_or_404(user_id)
        
        if user not in project.members:
            return jsonify({'error': 'User is not a member of this project'}), 400
        
        # Remove user from project
        project.members.remove(user)
        project.current_team_size -= 1
        
        # Remove project role
        project_role = ProjectRole.query.filter_by(
            project_id=project_id, user_id=user_id
        ).first()
        if project_role:
            db.session.delete(project_role)
        
        # Update user's project count
        user.total_projects = max(0, (user.total_projects or 1) - 1)
        
        db.session.commit()
        
        return jsonify({'message': 'Member removed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>/leave', methods=['POST'])
@jwt_required()
def leave_project(project_id):
    """Leave a project"""
    try:
        current_user_id = get_jwt_identity()
        project = Project.query.get_or_404(project_id)
        user = User.query.get(current_user_id)
        
        if user not in project.members:
            return jsonify({'error': 'Not a member of this project'}), 400
        
        if project.created_by == current_user_id:
            return jsonify({'error': 'Project creator cannot leave. Transfer ownership or delete the project.'}), 400
        
        # Remove user from project
        project.members.remove(user)
        project.current_team_size -= 1
        
        # Remove project role
        project_role = ProjectRole.query.filter_by(
            project_id=project_id, user_id=current_user_id
        ).first()
        if project_role:
            db.session.delete(project_role)
        
        # Update user's project count
        user.total_projects = max(0, (user.total_projects or 1) - 1)
        
        db.session.commit()
        
        return jsonify({'message': 'Successfully left project'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@project_bp.route('/my-projects', methods=['GET'])
@jwt_required()
def get_my_projects():
    """Get projects that the current user is involved in"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        projects_data = []
        for project in user.projects:
            project_data = project.to_dict()
            
            # Get user's role in this project
            user_role = ProjectRole.query.filter_by(
                project_id=project.id, user_id=current_user_id
            ).first()
            
            if user_role:
                project_data['my_role'] = {
                    'role_name': user_role.role_name,
                    'is_lead': user_role.is_lead,
                    'joined_at': user_role.joined_at.isoformat() if user_role.joined_at else None
                }
            
            project_data['is_creator'] = project.created_by == current_user_id
            projects_data.append(project_data)
        
        return jsonify({'projects': projects_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/my-applications', methods=['GET'])
@jwt_required()
def get_my_applications():
    """Get current user's project applications"""
    try:
        current_user_id = get_jwt_identity()
        
        applications = ProjectApplication.query.filter_by(
            applicant_id=current_user_id
        ).order_by(ProjectApplication.applied_at.desc()).all()
        
        applications_data = []
        for app in applications:
            app_data = app.to_dict()
            app_data['project'] = app.project.to_dict()
            applications_data.append(app_data)
        
        return jsonify({'applications': applications_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/featured', methods=['GET'])
def get_featured_projects():
    """Get featured/popular projects"""
    try:
        limit = request.args.get('limit', 6, type=int)
        
        # Get projects with high activity (many members, recent updates)
        projects = Project.query.filter_by(status='active')\
            .order_by(Project.current_team_size.desc(), Project.updated_at.desc())\
            .limit(limit).all()
        
        return jsonify({
            'projects': [project.to_dict() for project in projects]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@project_bp.route('/stats', methods=['GET'])
def get_project_stats():
    """Get overall project statistics"""
    try:
        total_projects = Project.query.count()
        active_projects = Project.query.filter_by(status='active').count()
        recruiting_projects = Project.query.filter_by(is_recruiting=True).count()
        total_collaborations = db.session.query(db.func.sum(Project.current_team_size)).scalar() or 0
        
        return jsonify({
            'total_projects': total_projects,
            'active_projects': active_projects,
            'recruiting_projects': recruiting_projects,
            'total_collaborations': total_collaborations
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
