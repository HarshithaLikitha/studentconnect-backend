from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.models import Event, User, db
from datetime import datetime

event_bp = Blueprint('event', __name__)

@event_bp.route('/', methods=['GET'])
def get_events():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        event_type = request.args.get('type')
        upcoming = request.args.get('upcoming', 'true').lower() == 'true'
        
        query = Event.query
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        
        if upcoming:
            query = query.filter(Event.start_date >= datetime.utcnow())
        
        events = query.order_by(Event.start_date.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'events': [event.to_dict() for event in events.items],
            'total': events.total,
            'pages': events.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    try:
        event = Event.query.get_or_404(event_id)
        return jsonify(event.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/', methods=['POST'])
@jwt_required()
def create_event():
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        if not data.get('title') or not data.get('start_date'):
            return jsonify({'error': 'Event title and start date are required'}), 400
        
        # Parse dates
        start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        end_date = None
        if data.get('end_date'):
            end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
        
        registration_deadline = None
        if data.get('registration_deadline'):
            registration_deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '+00:00'))
        
        event = Event(
            title=data['title'],
            description=data.get('description', ''),
            event_type=data.get('event_type', 'meetup'),
            start_date=start_date,
            end_date=end_date,
            location=data.get('location', ''),
            is_virtual=data.get('is_virtual', False),
            meeting_url=data.get('meeting_url', ''),
            max_attendees=data.get('max_attendees'),
            registration_deadline=registration_deadline,
            image_url=data.get('image_url', ''),
            created_by=current_user_id
        )
        
        db.session.add(event)
        db.session.commit()
        
        # Add creator as an attendee
        creator = User.query.get(current_user_id)
        event.attendees.append(creator)
        db.session.commit()
        
        return jsonify(event.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>', methods=['PUT'])
@jwt_required()
def update_event(event_id):
    try:
        current_user_id = get_jwt_identity()
        event = Event.query.get_or_404(event_id)
        
        if event.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        
        event.title = data.get('title', event.title)
        event.description = data.get('description', event.description)
        event.event_type = data.get('event_type', event.event_type)
        event.location = data.get('location', event.location)
        event.is_virtual = data.get('is_virtual', event.is_virtual)
        event.meeting_url = data.get('meeting_url', event.meeting_url)
        event.max_attendees = data.get('max_attendees', event.max_attendees)
        event.image_url = data.get('image_url', event.image_url)
        
        # Update dates if provided
        if data.get('start_date'):
            event.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        
        if data.get('end_date'):
            event.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
        
        if data.get('registration_deadline'):
            event.registration_deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '+00:00'))
        
        db.session.commit()
        
        return jsonify(event.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>', methods=['DELETE'])
@jwt_required()
def delete_event(event_id):
    try:
        current_user_id = get_jwt_identity()
        event = Event.query.get_or_404(event_id)
        
        if event.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        db.session.delete(event)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>/register', methods=['POST'])
@jwt_required()
def register_for_event(event_id):
    try:
        current_user_id = get_jwt_identity()
        event = Event.query.get_or_404(event_id)
        user = User.query.get(current_user_id)
        
        if user in event.attendees:
            return jsonify({'error': 'Already registered for this event'}), 400
        
        # Check if registration is still open
        if event.registration_deadline and datetime.utcnow() > event.registration_deadline:
            return jsonify({'error': 'Registration deadline has passed'}), 400
        
        # Check if event is full
        if event.max_attendees and len(event.attendees) >= event.max_attendees:
            return jsonify({'error': 'Event is full'}), 400
        
        event.attendees.append(user)
        db.session.commit()
        
        return jsonify({'message': 'Successfully registered for event'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>/unregister', methods=['POST'])
@jwt_required()
def unregister_from_event(event_id):
    try:
        current_user_id = get_jwt_identity()
        event = Event.query.get_or_404(event_id)
        user = User.query.get(current_user_id)
        
        if user not in event.attendees:
            return jsonify({'error': 'Not registered for this event'}), 400
        
        if event.created_by == current_user_id:
            return jsonify({'error': 'Event creator cannot unregister'}), 400
        
        event.attendees.remove(user)
        db.session.commit()
        
        return jsonify({'message': 'Successfully unregistered from event'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>/attendees', methods=['GET'])
def get_event_attendees(event_id):
    try:
        event = Event.query.get_or_404(event_id)
        return jsonify([attendee.to_dict() for attendee in event.attendees]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

