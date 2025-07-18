from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.models import Post, Comment, Like, User, Community, db

post_bp = Blueprint('post', __name__)

@post_bp.route('/', methods=['GET'])
def get_posts():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        community_id = request.args.get('community_id', type=int)
        post_type = request.args.get('type')
        
        query = Post.query
        
        if community_id:
            query = query.filter_by(community_id=community_id)
        
        if post_type:
            query = query.filter_by(post_type=post_type)
        
        posts = query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'posts': [post.to_dict() for post in posts.items],
            'total': posts.total,
            'pages': posts.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@post_bp.route('/<int:post_id>', methods=['GET'])
def get_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        return jsonify(post.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@post_bp.route('/', methods=['POST'])
@jwt_required()
def create_post():
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        if not data.get('content'):
            return jsonify({'error': 'Post content is required'}), 400
        
        post = Post(
            title=data.get('title', ''),
            content=data['content'],
            post_type=data.get('post_type', 'general'),
            image_url=data.get('image_url', ''),
            author_id=current_user_id,
            community_id=data.get('community_id')
        )
        
        db.session.add(post)
        db.session.commit()
        
        return jsonify(post.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@post_bp.route('/<int:post_id>', methods=['PUT'])
@jwt_required()
def update_post(post_id):
    try:
        current_user_id = get_jwt_identity()
        post = Post.query.get_or_404(post_id)
        
        if post.author_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        
        post.title = data.get('title', post.title)
        post.content = data.get('content', post.content)
        post.post_type = data.get('post_type', post.post_type)
        post.image_url = data.get('image_url', post.image_url)
        
        db.session.commit()
        
        return jsonify(post.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@post_bp.route('/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    try:
        current_user_id = get_jwt_identity()
        post = Post.query.get_or_404(post_id)
        
        if post.author_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        db.session.delete(post)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@post_bp.route('/<int:post_id>/like', methods=['POST'])
@jwt_required()
def like_post(post_id):
    try:
        current_user_id = get_jwt_identity()
        post = Post.query.get_or_404(post_id)
        
        # Check if user already liked the post
        existing_like = Like.query.filter_by(user_id=current_user_id, post_id=post_id).first()
        
        if existing_like:
            # Unlike the post
            db.session.delete(existing_like)
            post.likes_count = max(0, post.likes_count - 1)
            message = 'Post unliked'
        else:
            # Like the post
            like = Like(user_id=current_user_id, post_id=post_id)
            db.session.add(like)
            post.likes_count += 1
            message = 'Post liked'
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'likes_count': post.likes_count
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@post_bp.route('/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        comments = Comment.query.filter_by(post_id=post_id, parent_id=None).order_by(Comment.created_at.desc()).all()
        
        return jsonify([comment.to_dict() for comment in comments]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@post_bp.route('/<int:post_id>/comments', methods=['POST'])
@jwt_required()
def create_comment():
    try:
        current_user_id = get_jwt_identity()
        post_id = request.view_args['post_id']
        data = request.json
        
        if not data.get('content'):
            return jsonify({'error': 'Comment content is required'}), 400
        
        post = Post.query.get_or_404(post_id)
        
        comment = Comment(
            content=data['content'],
            author_id=current_user_id,
            post_id=post_id,
            parent_id=data.get('parent_id')
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify(comment.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@post_bp.route('/comments/<int:comment_id>', methods=['PUT'])
@jwt_required()
def update_comment(comment_id):
    try:
        current_user_id = get_jwt_identity()
        comment = Comment.query.get_or_404(comment_id)
        
        if comment.author_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        comment.content = data.get('content', comment.content)
        
        db.session.commit()
        
        return jsonify(comment.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@post_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    try:
        current_user_id = get_jwt_identity()
        comment = Comment.query.get_or_404(comment_id)
        
        if comment.author_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        db.session.delete(comment)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

