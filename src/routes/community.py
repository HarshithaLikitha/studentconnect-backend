from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.enhanced_models import Community, User, Post, db, community_moderators
from sqlalchemy import or_, and_
import json

community_bp = Blueprint('community', __name__)

@community_bp.route('/', methods=['GET'])
def get_communities():
    """Get all communities with filtering and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        category = request.args.get('category')
        search = request.args.get('search')
        featured_only = request.args.get('featured', type=bool)
        
        query = Community.query
        
        # Apply filters
        if category:
            query = query.filter_by(category=category)
        
        if search:
            query = query.filter(
                or_(
                    Community.name.ilike(f'%{search}%'),
                    Community.description.ilike(f'%{search}%')
                )
            )
        
        if featured_only:
            query = query.filter_by(is_featured=True)
        
        # Order by activity score and creation date
        query = query.order_by(Community.activity_score.desc(), Community.created_at.desc())
        
        communities = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'communities': [community.to_dict() for community in communities.items],
            'total': communities.total,
            'pages': communities.pages,
            'current_page': page,
            'has_next': communities.has_next,
            'has_prev': communities.has_prev
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/categories', methods=['GET'])
def get_community_categories():
    """Get all available community categories"""
    try:
        categories = db.session.query(Community.category).distinct().filter(
            Community.category.isnot(None),
            Community.category != ''
        ).all()
        
        category_list = [cat[0] for cat in categories if cat[0]]
        
        # Add some default categories if none exist
        if not category_list:
            category_list = [
                'Technology', 'Programming', 'Design', 'Data Science', 
                'AI/ML', 'Web Development', 'Mobile Development', 
                'DevOps', 'Cybersecurity', 'Gaming', 'Startups', 'Career'
            ]
        
        return jsonify({'categories': category_list}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>', methods=['GET'])
def get_community(community_id):
    """Get a specific community with detailed information"""
    try:
        community = Community.query.get_or_404(community_id)
        
        # Get recent posts from this community
        recent_posts = Post.query.filter_by(community_id=community_id)\
            .order_by(Post.created_at.desc())\
            .limit(5).all()
        
        community_data = community.to_dict()
        community_data['recent_posts'] = [post.to_dict() for post in recent_posts]
        
        return jsonify(community_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/', methods=['POST'])
@jwt_required()
def create_community():
    """Create a new community"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Community name is required'}), 400
        
        if not data.get('description'):
            return jsonify({'error': 'Community description is required'}), 400
        
        if not data.get('category'):
            return jsonify({'error': 'Community category is required'}), 400
        
        # Check if community name already exists
        existing_community = Community.query.filter_by(name=data['name']).first()
        if existing_community:
            return jsonify({'error': 'A community with this name already exists'}), 400
        
        community = Community(
            name=data['name'],
            description=data['description'],
            category=data['category'],
            image_url=data.get('image_url', ''),
            is_private=data.get('is_private', False),
            created_by=current_user_id,
            tags=data.get('tags', []),
            rules=data.get('rules', ''),
            member_count=1,  # Creator is the first member
            post_count=0,
            activity_score=0
        )
        
        db.session.add(community)
        db.session.flush()  # Get the community ID
        
        # Add creator as a member and moderator
        creator = User.query.get(current_user_id)
        community.members.append(creator)
        community.moderators.append(creator)
        
        # Update user's community count
        creator.total_communities = (creator.total_communities or 0) + 1
        
        db.session.commit()
        
        return jsonify(community.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>', methods=['PUT'])
@jwt_required()
def update_community(community_id):
    """Update a community (only by creator or moderators)"""
    try:
        current_user_id = get_jwt_identity()
        community = Community.query.get_or_404(community_id)
        current_user = User.query.get(current_user_id)
        
        # Check permissions (creator or moderator)
        if (community.created_by != current_user_id and 
            current_user not in community.moderators):
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        
        # Update fields
        if 'name' in data:
            # Check if new name conflicts with existing communities
            existing = Community.query.filter(
                and_(Community.name == data['name'], Community.id != community_id)
            ).first()
            if existing:
                return jsonify({'error': 'A community with this name already exists'}), 400
            community.name = data['name']
        
        if 'description' in data:
            community.description = data['description']
        if 'category' in data:
            community.category = data['category']
        if 'image_url' in data:
            community.image_url = data['image_url']
        if 'is_private' in data:
            community.is_private = data['is_private']
        if 'tags' in data:
            community.tags = data['tags']
        if 'rules' in data:
            community.rules = data['rules']
        
        db.session.commit()
        
        return jsonify(community.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>', methods=['DELETE'])
@jwt_required()
def delete_community(community_id):
    """Delete a community (only by creator)"""
    try:
        current_user_id = get_jwt_identity()
        community = Community.query.get_or_404(community_id)
        
        if community.created_by != current_user_id:
            return jsonify({'error': 'Only the community creator can delete it'}), 403
        
        # Update member counts
        for member in community.members:
            member.total_communities = max(0, (member.total_communities or 1) - 1)
        
        db.session.delete(community)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>/join', methods=['POST'])
@jwt_required()
def join_community(community_id):
    """Join a community"""
    try:
        current_user_id = get_jwt_identity()
        community = Community.query.get_or_404(community_id)
        user = User.query.get(current_user_id)
        
        if user in community.members:
            return jsonify({'error': 'Already a member of this community'}), 400
        
        # Check if community is private (would need invitation system)
        if community.is_private:
            return jsonify({'error': 'This is a private community. Invitation required.'}), 403
        
        community.members.append(user)
        community.member_count = len(community.members)
        community.activity_score += 1  # Increase activity score
        
        # Update user's community count
        user.total_communities = (user.total_communities or 0) + 1
        
        db.session.commit()
        
        return jsonify({
            'message': 'Successfully joined community',
            'member_count': community.member_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>/leave', methods=['POST'])
@jwt_required()
def leave_community(community_id):
    """Leave a community"""
    try:
        current_user_id = get_jwt_identity()
        community = Community.query.get_or_404(community_id)
        user = User.query.get(current_user_id)
        
        if user not in community.members:
            return jsonify({'error': 'Not a member of this community'}), 400
        
        if community.created_by == current_user_id:
            return jsonify({'error': 'Community creator cannot leave. Transfer ownership or delete the community.'}), 400
        
        community.members.remove(user)
        community.member_count = len(community.members)
        
        # Remove from moderators if applicable
        if user in community.moderators:
            community.moderators.remove(user)
        
        # Update user's community count
        user.total_communities = max(0, (user.total_communities or 1) - 1)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Successfully left community',
            'member_count': community.member_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>/members', methods=['GET'])
def get_community_members(community_id):
    """Get community members with pagination"""
    try:
        community = Community.query.get_or_404(community_id)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Get paginated members
        members_query = User.query.join(community.members).filter(
            User.id.in_([member.id for member in community.members])
        )
        
        members = members_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        members_data = []
        for member in members.items:
            member_data = member.to_dict()
            # Add role information
            member_data['is_creator'] = member.id == community.created_by
            member_data['is_moderator'] = member in community.moderators
            members_data.append(member_data)
        
        return jsonify({
            'members': members_data,
            'total': members.total,
            'pages': members.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>/moderators', methods=['GET'])
def get_community_moderators(community_id):
    """Get community moderators"""
    try:
        community = Community.query.get_or_404(community_id)
        moderators_data = []
        
        for moderator in community.moderators:
            mod_data = moderator.to_dict()
            mod_data['is_creator'] = moderator.id == community.created_by
            moderators_data.append(mod_data)
        
        return jsonify({'moderators': moderators_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>/moderators', methods=['POST'])
@jwt_required()
def add_moderator(community_id):
    """Add a moderator to the community (only by creator)"""
    try:
        current_user_id = get_jwt_identity()
        community = Community.query.get_or_404(community_id)
        
        if community.created_by != current_user_id:
            return jsonify({'error': 'Only the community creator can add moderators'}), 403
        
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        user = User.query.get_or_404(user_id)
        
        # Check if user is a member
        if user not in community.members:
            return jsonify({'error': 'User must be a member to become a moderator'}), 400
        
        # Check if already a moderator
        if user in community.moderators:
            return jsonify({'error': 'User is already a moderator'}), 400
        
        community.moderators.append(user)
        db.session.commit()
        
        return jsonify({'message': 'User added as moderator successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>/moderators/<int:user_id>', methods=['DELETE'])
@jwt_required()
def remove_moderator(community_id, user_id):
    """Remove a moderator from the community (only by creator)"""
    try:
        current_user_id = get_jwt_identity()
        community = Community.query.get_or_404(community_id)
        
        if community.created_by != current_user_id:
            return jsonify({'error': 'Only the community creator can remove moderators'}), 403
        
        if user_id == current_user_id:
            return jsonify({'error': 'Creator cannot remove themselves as moderator'}), 400
        
        user = User.query.get_or_404(user_id)
        
        if user not in community.moderators:
            return jsonify({'error': 'User is not a moderator'}), 400
        
        community.moderators.remove(user)
        db.session.commit()
        
        return jsonify({'message': 'Moderator removed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@community_bp.route('/<int:community_id>/posts', methods=['GET'])
def get_community_posts(community_id):
    """Get posts from a specific community"""
    try:
        community = Community.query.get_or_404(community_id)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        posts = Post.query.filter_by(community_id=community_id)\
            .order_by(Post.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'posts': [post.to_dict() for post in posts.items],
            'total': posts.total,
            'pages': posts.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/my-communities', methods=['GET'])
@jwt_required()
def get_my_communities():
    """Get communities that the current user is a member of"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        communities_data = []
        for community in user.communities:
            community_data = community.to_dict()
            community_data['my_role'] = 'creator' if community.created_by == current_user_id else 'moderator' if user in community.moderators else 'member'
            communities_data.append(community_data)
        
        return jsonify({'communities': communities_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/featured', methods=['GET'])
def get_featured_communities():
    """Get featured communities"""
    try:
        limit = request.args.get('limit', 6, type=int)
        
        communities = Community.query.filter_by(is_featured=True)\
            .order_by(Community.activity_score.desc())\
            .limit(limit).all()
        
        return jsonify({
            'communities': [community.to_dict() for community in communities]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@community_bp.route('/stats', methods=['GET'])
def get_community_stats():
    """Get overall community statistics"""
    try:
        total_communities = Community.query.count()
        total_members = db.session.query(db.func.sum(Community.member_count)).scalar() or 0
        total_posts = Post.query.filter(Post.community_id.isnot(None)).count()
        
        # Most active communities
        active_communities = Community.query.order_by(
            Community.activity_score.desc()
        ).limit(5).all()
        
        return jsonify({
            'total_communities': total_communities,
            'total_members': total_members,
            'total_posts': total_posts,
            'most_active': [community.to_dict() for community in active_communities]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
