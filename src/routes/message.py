from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.enhanced_models import Message, User, ChatRoom, ChatMessage, db
from sqlalchemy import or_, and_
from datetime import datetime
import json

message_bp = Blueprint('message', __name__)

@message_bp.route('/', methods=['GET'])
@jwt_required()
def get_messages():
    """Get messages for the current user"""
    try:
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Get direct messages
        messages = Message.query.filter(
            or_(
                Message.sender_id == current_user_id,
                Message.receiver_id == current_user_id
            )
        ).order_by(Message.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        messages_data = []
        for message in messages.items:
            message_data = message.to_dict()
            message_data['sender'] = message.sender.to_dict()
            message_data['receiver'] = message.receiver.to_dict()
            messages_data.append(message_data)
        
        return jsonify({
            'messages': messages_data,
            'total': messages.total,
            'pages': messages.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """Get conversation list for the current user"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get latest message with each user
        conversations_query = db.session.query(
            Message,
            db.case(
                (Message.sender_id == current_user_id, Message.receiver_id),
                else_=Message.sender_id
            ).label('other_user_id')
        ).filter(
            or_(
                Message.sender_id == current_user_id,
                Message.receiver_id == current_user_id
            )
        ).subquery()
        
        # Get the latest message for each conversation
        latest_messages = db.session.query(
            conversations_query.c.other_user_id,
            db.func.max(conversations_query.c.created_at).label('latest_time')
        ).group_by(conversations_query.c.other_user_id).all()
        
        conversations = []
        for user_id, latest_time in latest_messages:
            other_user = User.query.get(user_id)
            if other_user:
                # Get the actual latest message
                latest_message = Message.query.filter(
                    or_(
                        and_(Message.sender_id == current_user_id, Message.receiver_id == user_id),
                        and_(Message.sender_id == user_id, Message.receiver_id == current_user_id)
                    )
                ).order_by(Message.created_at.desc()).first()
                
                # Count unread messages
                unread_count = Message.query.filter(
                    Message.sender_id == user_id,
                    Message.receiver_id == current_user_id,
                    Message.is_read == False
                ).count()
                
                conversations.append({
                    'user': other_user.to_dict(),
                    'latest_message': latest_message.to_dict() if latest_message else None,
                    'unread_count': unread_count
                })
        
        # Sort by latest message time
        conversations.sort(key=lambda x: x['latest_message']['created_at'] if x['latest_message'] else '', reverse=True)
        
        return jsonify({'conversations': conversations}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/conversation/<int:user_id>', methods=['GET'])
@jwt_required()
def get_conversation(user_id):
    """Get conversation with a specific user"""
    try:
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Get messages between current user and specified user
        messages = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user_id, Message.receiver_id == user_id),
                and_(Message.sender_id == user_id, Message.receiver_id == current_user_id)
            )
        ).order_by(Message.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Mark messages as read
        Message.query.filter(
            Message.sender_id == user_id,
            Message.receiver_id == current_user_id,
            Message.is_read == False
        ).update({'is_read': True})
        db.session.commit()
        
        messages_data = []
        for message in messages.items:
            message_data = message.to_dict()
            message_data['sender'] = message.sender.to_dict()
            messages_data.append(message_data)
        
        # Reverse to show oldest first
        messages_data.reverse()
        
        return jsonify({
            'messages': messages_data,
            'total': messages.total,
            'pages': messages.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/', methods=['POST'])
@jwt_required()
def send_message():
    """Send a direct message"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        receiver_id = data.get('receiver_id')
        content = data.get('content')
        
        if not receiver_id or not content:
            return jsonify({'error': 'Receiver ID and content are required'}), 400
        
        # Check if receiver exists
        receiver = User.query.get(receiver_id)
        if not receiver:
            return jsonify({'error': 'Receiver not found'}), 404
        
        if receiver_id == current_user_id:
            return jsonify({'error': 'Cannot send message to yourself'}), 400
        
        message = Message(
            content=content,
            sender_id=current_user_id,
            receiver_id=receiver_id,
            is_read=False
        )
        
        db.session.add(message)
        db.session.commit()
        
        message_data = message.to_dict()
        message_data['sender'] = message.sender.to_dict()
        message_data['receiver'] = message.receiver.to_dict()
        
        return jsonify({
            'message': 'Message sent successfully',
            'data': message_data
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/<int:message_id>/read', methods=['PUT'])
@jwt_required()
def mark_message_read(message_id):
    """Mark a message as read"""
    try:
        current_user_id = get_jwt_identity()
        message = Message.query.get_or_404(message_id)
        
        if message.receiver_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        message.is_read = True
        db.session.commit()
        
        return jsonify({'message': 'Message marked as read'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """Get unread message count for current user"""
    try:
        current_user_id = get_jwt_identity()
        
        unread_count = Message.query.filter(
            Message.receiver_id == current_user_id,
            Message.is_read == False
        ).count()
        
        return jsonify({'unread_count': unread_count}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Chat Room functionality
@message_bp.route('/rooms', methods=['GET'])
@jwt_required()
def get_chat_rooms():
    """Get chat rooms for the current user"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        rooms_data = []
        for room in user.chat_rooms:
            room_data = room.to_dict()
            
            # Get latest message
            latest_message = ChatMessage.query.filter_by(room_id=room.id)\
                .order_by(ChatMessage.created_at.desc()).first()
            
            if latest_message:
                room_data['latest_message'] = latest_message.to_dict()
            
            rooms_data.append(room_data)
        
        return jsonify({'rooms': rooms_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/rooms', methods=['POST'])
@jwt_required()
def create_chat_room():
    """Create a new chat room"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        name = data.get('name')
        room_type = data.get('room_type', 'group')  # direct, group, community, project
        related_id = data.get('related_id')
        participant_ids = data.get('participant_ids', [])
        
        if not name:
            return jsonify({'error': 'Room name is required'}), 400
        
        room = ChatRoom(
            name=name,
            room_type=room_type,
            related_id=related_id,
            created_by=current_user_id
        )
        
        db.session.add(room)
        db.session.flush()  # Get room ID
        
        # Add creator as participant
        creator = User.query.get(current_user_id)
        room.participants.append(creator)
        
        # Add other participants
        for participant_id in participant_ids:
            if participant_id != current_user_id:
                participant = User.query.get(participant_id)
                if participant:
                    room.participants.append(participant)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Chat room created successfully',
            'room': room.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/rooms/<int:room_id>/messages', methods=['GET'])
@jwt_required()
def get_room_messages(room_id):
    """Get messages from a chat room"""
    try:
        current_user_id = get_jwt_identity()
        room = ChatRoom.query.get_or_404(room_id)
        
        # Check if user is a participant
        user = User.query.get(current_user_id)
        if user not in room.participants:
            return jsonify({'error': 'Access denied'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        messages = ChatMessage.query.filter_by(room_id=room_id)\
            .order_by(ChatMessage.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        messages_data = []
        for message in messages.items:
            message_data = message.to_dict()
            messages_data.append(message_data)
        
        # Reverse to show oldest first
        messages_data.reverse()
        
        return jsonify({
            'messages': messages_data,
            'total': messages.total,
            'pages': messages.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/rooms/<int:room_id>/messages', methods=['POST'])
@jwt_required()
def send_room_message(room_id):
    """Send a message to a chat room"""
    try:
        current_user_id = get_jwt_identity()
        room = ChatRoom.query.get_or_404(room_id)
        
        # Check if user is a participant
        user = User.query.get(current_user_id)
        if user not in room.participants:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.json
        content = data.get('content')
        message_type = data.get('message_type', 'text')
        file_url = data.get('file_url', '')
        
        if not content:
            return jsonify({'error': 'Message content is required'}), 400
        
        message = ChatMessage(
            room_id=room_id,
            sender_id=current_user_id,
            content=content,
            message_type=message_type,
            file_url=file_url
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'message': 'Message sent successfully',
            'data': message.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/rooms/<int:room_id>/participants', methods=['GET'])
@jwt_required()
def get_room_participants(room_id):
    """Get participants of a chat room"""
    try:
        current_user_id = get_jwt_identity()
        room = ChatRoom.query.get_or_404(room_id)
        
        # Check if user is a participant
        user = User.query.get(current_user_id)
        if user not in room.participants:
            return jsonify({'error': 'Access denied'}), 403
        
        participants_data = []
        for participant in room.participants:
            participant_data = participant.to_dict()
            participant_data['is_creator'] = participant.id == room.created_by
            participants_data.append(participant_data)
        
        return jsonify({'participants': participants_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@message_bp.route('/rooms/<int:room_id>/participants', methods=['POST'])
@jwt_required()
def add_room_participant(room_id):
    """Add a participant to a chat room"""
    try:
        current_user_id = get_jwt_identity()
        room = ChatRoom.query.get_or_404(room_id)
        
        # Check if user is the creator
        if room.created_by != current_user_id:
            return jsonify({'error': 'Only room creator can add participants'}), 403
        
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        user = User.query.get_or_404(user_id)
        
        if user in room.participants:
            return jsonify({'error': 'User is already a participant'}), 400
        
        room.participants.append(user)
        db.session.commit()
        
        return jsonify({'message': 'Participant added successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@message_bp.route('/rooms/<int:room_id>/participants/<int:user_id>', methods=['DELETE'])
@jwt_required()
def remove_room_participant(room_id, user_id):
    """Remove a participant from a chat room"""
    try:
        current_user_id = get_jwt_identity()
        room = ChatRoom.query.get_or_404(room_id)
        
        # Check if user is the creator or removing themselves
        if room.created_by != current_user_id and user_id != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        if user_id == room.created_by:
            return jsonify({'error': 'Cannot remove room creator'}), 400
        
        user = User.query.get_or_404(user_id)
        
        if user not in room.participants:
            return jsonify({'error': 'User is not a participant'}), 400
        
        room.participants.remove(user)
        db.session.commit()
        
        return jsonify({'message': 'Participant removed successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
