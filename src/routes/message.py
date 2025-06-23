from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.models import Message, User, db

message_bp = Blueprint('message', __name__)

@message_bp.route('/', methods=['GET'])
@jwt_required()
def get_messages():
    try:
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        other_user_id = request.args.get('user_id', type=int)
        
        if other_user_id:
            # Get conversation with specific user
            messages = Message.query.filter(
                ((Message.sender_id == current_user_id) & (Message.receiver_id == other_user_id)) |
                ((Message.sender_id == other_user_id) & (Message.receiver_id == current_user_id))
            ).order_by(Message.created_at.asc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        else:
            # Get all messages for current user
            messages = Message.query.filter(
                (Message.sender_id == current_user_id) | (Message.receiver_id == current_user_id)
            ).order_by(Message.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        
        return jsonify({
            'messages': [message.to_dict() for message in messages.items],
            'total': messages.total,
            'pages': messages.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/', methods=['POST'])
@jwt_required()
def send_message():
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        if not data.get('receiver_id') or not data.get('content'):
            return jsonify({'error': 'Receiver ID and content are required'}), 400
        
        # Check if receiver exists
        receiver = User.query.get(data['receiver_id'])
        if not receiver:
            return jsonify({'error': 'Receiver not found'}), 404
        
        if not receiver.is_active:
            return jsonify({'error': 'Receiver account is deactivated'}), 400
        
        message = Message(
            content=data['content'],
            sender_id=current_user_id,
            receiver_id=data['receiver_id']
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify(message.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/<int:message_id>', methods=['GET'])
@jwt_required()
def get_message(message_id):
    try:
        current_user_id = get_jwt_identity()
        message = Message.query.get_or_404(message_id)
        
        # Check if user is sender or receiver
        if message.sender_id != current_user_id and message.receiver_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        return jsonify(message.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/<int:message_id>/read', methods=['POST'])
@jwt_required()
def mark_message_read(message_id):
    try:
        current_user_id = get_jwt_identity()
        message = Message.query.get_or_404(message_id)
        
        # Only receiver can mark message as read
        if message.receiver_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        message.is_read = True
        db.session.commit()
        
        return jsonify({'message': 'Message marked as read'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    try:
        current_user_id = get_jwt_identity()
        
        # Get latest message with each user
        subquery = db.session.query(
            db.func.max(Message.id).label('max_id')
        ).filter(
            (Message.sender_id == current_user_id) | (Message.receiver_id == current_user_id)
        ).group_by(
            db.case(
                (Message.sender_id == current_user_id, Message.receiver_id),
                else_=Message.sender_id
            )
        ).subquery()
        
        latest_messages = db.session.query(Message).filter(
            Message.id.in_(subquery)
        ).order_by(Message.created_at.desc()).all()
        
        conversations = []
        for message in latest_messages:
            other_user_id = message.receiver_id if message.sender_id == current_user_id else message.sender_id
            other_user = User.query.get(other_user_id)
            
            if other_user:
                conversations.append({
                    'user': other_user.to_dict(),
                    'last_message': message.to_dict(),
                    'unread_count': Message.query.filter_by(
                        sender_id=other_user_id,
                        receiver_id=current_user_id,
                        is_read=False
                    ).count()
                })
        
        return jsonify(conversations), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    try:
        current_user_id = get_jwt_identity()
        
        unread_count = Message.query.filter_by(
            receiver_id=current_user_id,
            is_read=False
        ).count()
        
        return jsonify({'unread_count': unread_count}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

