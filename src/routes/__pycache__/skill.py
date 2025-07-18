from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.enhanced_models import Skill, UserSkill, SkillEndorsement, User, db
from sqlalchemy import or_, and_
from datetime import datetime
import json

skill_bp = Blueprint('skill', __name__)

@skill_bp.route('/', methods=['GET'])
def get_skills():
    """Get all available skills"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        category = request.args.get('category')
        search = request.args.get('search')
        
        query = Skill.query
        
        if category:
            query = query.filter_by(category=category)
        
        if search:
            query = query.filter(
                or_(
                    Skill.name.ilike(f'%{search}%'),
                    Skill.description.ilike(f'%{search}%')
                )
            )
        
        skills = query.order_by(Skill.name.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'skills': [skill.to_dict() for skill in skills.items],
            'total': skills.total,
            'pages': skills.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/categories', methods=['GET'])
def get_skill_categories():
    """Get all skill categories"""
    try:
        categories = db.session.query(Skill.category).distinct().filter(
            Skill.category.isnot(None),
            Skill.category != ''
        ).all()
        
        category_list = [cat[0] for cat in categories if cat[0]]
        
        # Add default categories if none exist
        if not category_list:
            category_list = [
                'Programming', 'Web Development', 'Mobile Development',
                'Data Science', 'Machine Learning', 'DevOps',
                'Design', 'Project Management', 'Database',
                'Cloud Computing', 'Cybersecurity', 'Testing'
            ]
        
        return jsonify({'categories': category_list}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/', methods=['POST'])
@jwt_required()
def create_skill():
    """Create a new skill (admin only or if skill doesn't exist)"""
    try:
        data = request.json
        
        name = data.get('name')
        category = data.get('category')
        description = data.get('description', '')
        icon_url = data.get('icon_url', '')
        
        if not name or not category:
            return jsonify({'error': 'Skill name and category are required'}), 400
        
        # Check if skill already exists
        existing_skill = Skill.query.filter_by(name=name).first()
        if existing_skill:
            return jsonify({
                'message': 'Skill already exists',
                'skill': existing_skill.to_dict()
            }), 200
        
        skill = Skill(
            name=name,
            category=category,
            description=description,
            icon_url=icon_url
        )
        
        db.session.add(skill)
        db.session.commit()
        
        return jsonify({
            'message': 'Skill created successfully',
            'skill': skill.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/popular', methods=['GET'])
def get_popular_skills():
    """Get popular skills based on user count"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        # Get skills with most users
        popular_skills = db.session.query(
            Skill,
            db.func.count(UserSkill.id).label('user_count')
        ).join(UserSkill).group_by(Skill.id)\
         .order_by(db.func.count(UserSkill.id).desc())\
         .limit(limit).all()
        
        skills_data = []
        for skill, user_count in popular_skills:
            skill_data = skill.to_dict()
            skill_data['user_count'] = user_count
            skills_data.append(skill_data)
        
        return jsonify({'skills': skills_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# User Skills Management
@skill_bp.route('/my-skills', methods=['GET'])
@jwt_required()
def get_my_skills():
    """Get current user's skills"""
    try:
        current_user_id = get_jwt_identity()
        
        user_skills = UserSkill.query.filter_by(user_id=current_user_id)\
            .order_by(UserSkill.endorsement_count.desc()).all()
        
        skills_data = []
        for user_skill in user_skills:
            skill_data = user_skill.to_dict()
            skills_data.append(skill_data)
        
        return jsonify({'skills': skills_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/my-skills', methods=['POST'])
@jwt_required()
def add_my_skill():
    """Add a skill to current user's profile"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        skill_id = data.get('skill_id')
        proficiency_level = data.get('proficiency_level', 'beginner')
        years_experience = data.get('years_experience', 0)
        
        if not skill_id:
            return jsonify({'error': 'Skill ID is required'}), 400
        
        # Check if skill exists
        skill = Skill.query.get_or_404(skill_id)
        
        # Check if user already has this skill
        existing_user_skill = UserSkill.query.filter_by(
            user_id=current_user_id, skill_id=skill_id
        ).first()
        
        if existing_user_skill:
            return jsonify({'error': 'You already have this skill in your profile'}), 400
        
        user_skill = UserSkill(
            user_id=current_user_id,
            skill_id=skill_id,
            proficiency_level=proficiency_level,
            years_experience=years_experience,
            endorsement_count=0
        )
        
        db.session.add(user_skill)
        db.session.commit()
        
        return jsonify({
            'message': 'Skill added to your profile successfully',
            'user_skill': user_skill.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/my-skills/<int:user_skill_id>', methods=['PUT'])
@jwt_required()
def update_my_skill(user_skill_id):
    """Update a skill in current user's profile"""
    try:
        current_user_id = get_jwt_identity()
        user_skill = UserSkill.query.get_or_404(user_skill_id)
        
        if user_skill.user_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        
        if 'proficiency_level' in data:
            user_skill.proficiency_level = data['proficiency_level']
        if 'years_experience' in data:
            user_skill.years_experience = data['years_experience']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Skill updated successfully',
            'user_skill': user_skill.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/my-skills/<int:user_skill_id>', methods=['DELETE'])
@jwt_required()
def remove_my_skill(user_skill_id):
    """Remove a skill from current user's profile"""
    try:
        current_user_id = get_jwt_identity()
        user_skill = UserSkill.query.get_or_404(user_skill_id)
        
        if user_skill.user_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Remove related endorsements
        SkillEndorsement.query.filter_by(
            endorsed_user_id=current_user_id,
            skill_id=user_skill.skill_id
        ).delete()
        
        db.session.delete(user_skill)
        db.session.commit()
        
        return jsonify({'message': 'Skill removed from your profile'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/users/<int:user_id>/skills', methods=['GET'])
def get_user_skills(user_id):
    """Get skills for a specific user"""
    try:
        user = User.query.get_or_404(user_id)
        
        user_skills = UserSkill.query.filter_by(user_id=user_id)\
            .order_by(UserSkill.endorsement_count.desc()).all()
        
        skills_data = []
        for user_skill in user_skills:
            skill_data = user_skill.to_dict()
            skills_data.append(skill_data)
        
        return jsonify({
            'user': user.to_dict(),
            'skills': skills_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Skill Endorsements
@skill_bp.route('/endorse', methods=['POST'])
@jwt_required()
def endorse_skill():
    """Endorse a user's skill"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        endorsed_user_id = data.get('endorsed_user_id')
        skill_id = data.get('skill_id')
        
        if not endorsed_user_id or not skill_id:
            return jsonify({'error': 'Endorsed user ID and skill ID are required'}), 400
        
        if endorsed_user_id == current_user_id:
            return jsonify({'error': 'Cannot endorse your own skills'}), 400
        
        # Check if user has this skill
        user_skill = UserSkill.query.filter_by(
            user_id=endorsed_user_id, skill_id=skill_id
        ).first()
        
        if not user_skill:
            return jsonify({'error': 'User does not have this skill in their profile'}), 400
        
        # Check if already endorsed
        existing_endorsement = SkillEndorsement.query.filter_by(
            endorser_id=current_user_id,
            endorsed_user_id=endorsed_user_id,
            skill_id=skill_id
        ).first()
        
        if existing_endorsement:
            return jsonify({'error': 'You have already endorsed this skill for this user'}), 400
        
        endorsement = SkillEndorsement(
            endorser_id=current_user_id,
            endorsed_user_id=endorsed_user_id,
            skill_id=skill_id
        )
        
        db.session.add(endorsement)
        
        # Update endorsement count
        user_skill.endorsement_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': 'Skill endorsed successfully',
            'endorsement_count': user_skill.endorsement_count
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/endorsements/<int:endorsement_id>', methods=['DELETE'])
@jwt_required()
def remove_endorsement(endorsement_id):
    """Remove a skill endorsement"""
    try:
        current_user_id = get_jwt_identity()
        endorsement = SkillEndorsement.query.get_or_404(endorsement_id)
        
        if endorsement.endorser_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Update endorsement count
        user_skill = UserSkill.query.filter_by(
            user_id=endorsement.endorsed_user_id,
            skill_id=endorsement.skill_id
        ).first()
        
        if user_skill:
            user_skill.endorsement_count = max(0, user_skill.endorsement_count - 1)
        
        db.session.delete(endorsement)
        db.session.commit()
        
        return jsonify({'message': 'Endorsement removed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/endorsements/given', methods=['GET'])
@jwt_required()
def get_given_endorsements():
    """Get endorsements given by current user"""
    try:
        current_user_id = get_jwt_identity()
        
        endorsements = SkillEndorsement.query.filter_by(endorser_id=current_user_id)\
            .order_by(SkillEndorsement.created_at.desc()).all()
        
        endorsements_data = []
        for endorsement in endorsements:
            endorsement_data = endorsement.to_dict()
            endorsement_data['endorsed_user'] = endorsement.endorsed_user.to_dict()
            endorsement_data['skill'] = endorsement.skill.to_dict()
            endorsements_data.append(endorsement_data)
        
        return jsonify({'endorsements': endorsements_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/endorsements/received', methods=['GET'])
@jwt_required()
def get_received_endorsements():
    """Get endorsements received by current user"""
    try:
        current_user_id = get_jwt_identity()
        
        endorsements = SkillEndorsement.query.filter_by(endorsed_user_id=current_user_id)\
            .order_by(SkillEndorsement.created_at.desc()).all()
        
        endorsements_data = []
        for endorsement in endorsements:
            endorsement_data = endorsement.to_dict()
            endorsement_data['endorser'] = endorsement.endorser.to_dict()
            endorsement_data['skill'] = endorsement.skill.to_dict()
            endorsements_data.append(endorsement_data)
        
        return jsonify({'endorsements': endorsements_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/search-users', methods=['GET'])
def search_users_by_skill():
    """Search users by skill"""
    try:
        skill_name = request.args.get('skill')
        proficiency = request.args.get('proficiency')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not skill_name:
            return jsonify({'error': 'Skill name is required'}), 400
        
        # Find skill
        skill = Skill.query.filter(Skill.name.ilike(f'%{skill_name}%')).first()
        if not skill:
            return jsonify({'users': [], 'total': 0}), 200
        
        query = UserSkill.query.filter_by(skill_id=skill.id)
        
        if proficiency:
            query = query.filter_by(proficiency_level=proficiency)
        
        user_skills = query.order_by(UserSkill.endorsement_count.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        users_data = []
        for user_skill in user_skills.items:
            user_data = user_skill.user.to_dict()
            user_data['skill_info'] = {
                'proficiency_level': user_skill.proficiency_level,
                'years_experience': user_skill.years_experience,
                'endorsement_count': user_skill.endorsement_count
            }
            users_data.append(user_data)
        
        return jsonify({
            'users': users_data,
            'total': user_skills.total,
            'pages': user_skills.pages,
            'current_page': page,
            'skill': skill.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@skill_bp.route('/stats', methods=['GET'])
def get_skill_stats():
    """Get overall skill statistics"""
    try:
        total_skills = Skill.query.count()
        total_user_skills = UserSkill.query.count()
        total_endorsements = SkillEndorsement.query.count()
        
        # Most popular skills
        popular_skills = db.session.query(
            Skill.name,
            db.func.count(UserSkill.id).label('user_count')
        ).join(UserSkill).group_by(Skill.id)\
         .order_by(db.func.count(UserSkill.id).desc())\
         .limit(10).all()
        
        # Skills by category
        skills_by_category = db.session.query(
            Skill.category,
            db.func.count(Skill.id).label('skill_count')
        ).group_by(Skill.category).all()
        
        return jsonify({
            'total_skills': total_skills,
            'total_user_skills': total_user_skills,
            'total_endorsements': total_endorsements,
            'popular_skills': [{'name': skill[0], 'user_count': skill[1]} for skill in popular_skills],
            'skills_by_category': [{'category': cat[0], 'count': cat[1]} for cat in skills_by_category]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
