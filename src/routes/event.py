from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.enhanced_models import Event, User, EventRegistration, db
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
import json

event_bp = Blueprint('event', __name__)

@event_bp.route('/', methods=['GET'])
def get_events():
    """Get all events with filtering and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        event_type = request.args.get('event_type')
        difficulty = request.args.get('difficulty')
        search = request.args.get('search')
        upcoming = request.args.get('upcoming', 'true').lower() == 'true'
        featured_only = request.args.get('featured', type=bool)
        is_virtual = request.args.get('virtual', type=bool)
        
        query = Event.query
        
        # Apply filters
        if event_type:
            query = query.filter_by(event_type=event_type)
        
        if difficulty:
            query = query.filter_by(difficulty_level=difficulty)
        
        if search:
            query = query.filter(
                or_(
                    Event.title.ilike(f'%{search}%'),
                    Event.description.ilike(f'%{search}%')
                )
            )
        
        if upcoming:
            query = query.filter(Event.start_date >= datetime.utcnow())
        
        if featured_only:
            query = query.filter_by(is_featured=True)
        
        if is_virtual is not None:
            query = query.filter_by(is_virtual=is_virtual)
        
        # Order by featured status, start date
        query = query.order_by(
            Event.is_featured.desc(),
            Event.start_date.asc()
        )
        
        events = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'events': [event.to_dict() for event in events.items],
            'total': events.total,
            'pages': events.pages,
            'current_page': page,
            'has_next': events.has_next,
            'has_prev': events.has_prev
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/types', methods=['GET'])
def get_event_types():
    """Get all available event types"""
    try:
        types = [
            'hackathon', 'workshop', 'meetup', 'conference', 
            'webinar', 'competition', 'networking', 'career_fair'
        ]
        return jsonify({'types': types}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get a specific event with detailed information"""
    try:
        event = Event.query.get_or_404(event_id)
        
        # Get registration statistics
        total_registrations = EventRegistration.query.filter_by(event_id=event_id).count()
        confirmed_registrations = EventRegistration.query.filter_by(
            event_id=event_id, payment_status='confirmed'
        ).count()
        
        event_data = event.to_dict()
        event_data['registration_stats'] = {
            'total_registrations': total_registrations,
            'confirmed_registrations': confirmed_registrations,
            'available_spots': (event.max_attendees - confirmed_registrations) if event.max_attendees else None
        }
        
        return jsonify(event_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/', methods=['POST'])
@jwt_required()
def create_event():
    """Create a new event"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Event title is required'}), 400
        
        if not data.get('description'):
            return jsonify({'error': 'Event description is required'}), 400
        
        if not data.get('start_date'):
            return jsonify({'error': 'Event start date is required'}), 400
        
        if not data.get('event_type'):
            return jsonify({'error': 'Event type is required'}), 400
        
        # Parse dates
        try:
            start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid start date format'}), 400
        
        end_date = None
        if data.get('end_date'):
            try:
                end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid end date format'}), 400
        
        registration_deadline = None
        if data.get('registration_deadline'):
            try:
                registration_deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid registration deadline format'}), 400
        
        # Validate dates
        if start_date <= datetime.utcnow():
            return jsonify({'error': 'Event start date must be in the future'}), 400
        
        if end_date and end_date <= start_date:
            return jsonify({'error': 'Event end date must be after start date'}), 400
        
        if registration_deadline and registration_deadline >= start_date:
            return jsonify({'error': 'Registration deadline must be before event start date'}), 400
        
        event = Event(
            title=data['title'],
            description=data['description'],
            event_type=data['event_type'],
            start_date=start_date,
            end_date=end_date,
            location=data.get('location', ''),
            is_virtual=data.get('is_virtual', False),
            meeting_url=data.get('meeting_url', ''),
            max_attendees=data.get('max_attendees'),
            registration_deadline=registration_deadline,
            image_url=data.get('image_url', ''),
            created_by=current_user_id,
            
            # Enhanced fields
            organizer_info=data.get('organizer_info', {}),
            agenda=data.get('agenda', []),
            prerequisites=data.get('prerequisites', []),
            prizes=data.get('prizes', []),
            sponsors=data.get('sponsors', []),
            tags=data.get('tags', []),
            difficulty_level=data.get('difficulty_level', 'intermediate'),
            is_featured=False,  # Only admins can set featured
            registration_fee=data.get('registration_fee', 0.0),
            certificate_available=data.get('certificate_available', False)
        )
        
        db.session.add(event)
        db.session.flush()  # Get the event ID
        
        # Create registration for creator
        creator_registration = EventRegistration(
            event_id=event.id,
            user_id=current_user_id,
            registration_data={'role': 'organizer'},
            payment_status='confirmed',
            attendance_status='confirmed'
        )
        
        db.session.add(creator_registration)
        
        # Add creator as attendee
        creator = User.query.get(current_user_id)
        event.attendees.append(creator)
        
        db.session.commit()
        
        return jsonify(event.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>', methods=['PUT'])
@jwt_required()
def update_event(event_id):
    """Update an event (only by creator)"""
    try:
        current_user_id = get_jwt_identity()
        event = Event.query.get_or_404(event_id)
        
        if event.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        
        # Update basic fields
        if 'title' in data:
            event.title = data['title']
        if 'description' in data:
            event.description = data['description']
        if 'event_type' in data:
            event.event_type = data['event_type']
        if 'location' in data:
            event.location = data['location']
        if 'is_virtual' in data:
            event.is_virtual = data['is_virtual']
        if 'meeting_url' in data:
            event.meeting_url = data['meeting_url']
        if 'max_attendees' in data:
            event.max_attendees = data['max_attendees']
        if 'image_url' in data:
            event.image_url = data['image_url']
        
        # Update enhanced fields
        if 'organizer_info' in data:
            event.organizer_info = data['organizer_info']
        if 'agenda' in data:
            event.agenda = data['agenda']
        if 'prerequisites' in data:
            event.prerequisites = data['prerequisites']
        if 'prizes' in data:
            event.prizes = data['prizes']
        if 'sponsors' in data:
            event.sponsors = data['sponsors']
        if 'tags' in data:
            event.tags = data['tags']
        if 'difficulty_level' in data:
            event.difficulty_level = data['difficulty_level']
        if 'registration_fee' in data:
            event.registration_fee = data['registration_fee']
        if 'certificate_available' in data:
            event.certificate_available = data['certificate_available']
        
        # Update dates if provided
        if 'start_date' in data:
            try:
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
                if start_date <= datetime.utcnow():
                    return jsonify({'error': 'Event start date must be in the future'}), 400
                event.start_date = start_date
            except ValueError:
                return jsonify({'error': 'Invalid start date format'}), 400
        
        if 'end_date' in data:
            try:
                end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
                if end_date <= event.start_date:
                    return jsonify({'error': 'Event end date must be after start date'}), 400
                event.end_date = end_date
            except ValueError:
                return jsonify({'error': 'Invalid end date format'}), 400
        
        if 'registration_deadline' in data:
            try:
                registration_deadline = datetime.fromisoformat(data['registration_deadline'].replace('Z', '+00:00'))
                if registration_deadline >= event.start_date:
                    return jsonify({'error': 'Registration deadline must be before event start date'}), 400
                event.registration_deadline = registration_deadline
            except ValueError:
                return jsonify({'error': 'Invalid registration deadline format'}), 400
        
        db.session.commit()
        
        return jsonify(event.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>', methods=['DELETE'])
@jwt_required()
def delete_event(event_id):
    """Delete an event (only by creator)"""
    try:
        current_user_id = get_jwt_identity()
        event = Event.query.get_or_404(event_id)
        
        if event.created_by != current_user_id:
            return jsonify({'error': 'Only the event creator can delete it'}), 403
        
        # Update attendee counts
        for attendee in event.attendees:
            attendee.total_events_attended = max(0, (attendee.total_events_attended or 1) - 1)
        
        db.session.delete(event)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>/register', methods=['POST'])
@jwt_required()
def register_for_event(event_id):
    """Register for an event"""
    try:
        current_user_id = get_jwt_identity()
        event = Event.query.get_or_404(event_id)
        user = User.query.get(current_user_id)
        
        # Check if already registered
        existing_registration = EventRegistration.query.filter_by(
            event_id=event_id, user_id=current_user_id
        ).first()
        
        if existing_registration:
            return jsonify({'error': 'Already registered for this event'}), 400
        
        # Check if registration is still open
        if event.registration_deadline and datetime.utcnow() > event.registration_deadline:
            return jsonify({'error': 'Registration deadline has passed'}), 400
        
        # Check if event is full
        if event.max_attendees:
            confirmed_count = EventRegistration.query.filter_by(
                event_id=event_id, payment_status='confirmed'
            ).count()
            if confirmed_count >= event.max_attendees:
                return jsonify({'error': 'Event is full'}), 400
        
        data = request.json or {}
        
        # Create registration
        registration = EventRegistration(
            event_id=event_id,
            user_id=current_user_id,
            registration_data=data.get('registration_data', {}),
            payment_status='pending' if event.registration_fee > 0 else 'confirmed',
            attendance_status='registered'
        )
        
        db.session.add(registration)
        
        # Add to attendees if payment not required
        if event.registration_fee == 0:
            event.attendees.append(user)
            user.total_events_attended = (user.total_events_attended or 0) + 1
        
        db.session.commit()
        
        return jsonify({
            'message': 'Successfully registered for event',
            'registration': registration.to_dict(),
            'payment_required': event.registration_fee > 0
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>/unregister', methods=['POST'])
@jwt_required()
def unregister_from_event(event_id):
    """Unregister from an event"""
    try:
        current_user_id = get_jwt_identity()
        event = Event.query.get_or_404(event_id)
        user = User.query.get(current_user_id)
        
        if event.created_by == current_user_id:
            return jsonify({'error': 'Event creator cannot unregister'}), 400
        
        # Find registration
        registration = EventRegistration.query.filter_by(
            event_id=event_id, user_id=current_user_id
        ).first()
        
        if not registration:
            return jsonify({'error': 'Not registered for this event'}), 400
        
        # Check if event has already started
        if datetime.utcnow() >= event.start_date:
            return jsonify({'error': 'Cannot unregister after event has started'}), 400
        
        # Remove from attendees
        if user in event.attendees:
            event.attendees.remove(user)
            user.total_events_attended = max(0, (user.total_events_attended or 1) - 1)
        
        # Delete registration
        db.session.delete(registration)
        db.session.commit()
        
        return jsonify({'message': 'Successfully unregistered from event'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>/registrations', methods=['GET'])
@jwt_required()
def get_event_registrations(event_id):
    """Get event registrations (only for event creator)"""
    try:
        current_user_id = get_jwt_identity()
        event = Event.query.get_or_404(event_id)
        
        if event.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status')
        
        query = EventRegistration.query.filter_by(event_id=event_id)
        
        if status_filter:
            query = query.filter_by(payment_status=status_filter)
        
        registrations = query.order_by(EventRegistration.registered_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'registrations': [reg.to_dict() for reg in registrations.items],
            'total': registrations.total,
            'pages': registrations.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>/attendees', methods=['GET'])
def get_event_attendees(event_id):
    """Get event attendees"""
    try:
        event = Event.query.get_or_404(event_id)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Get confirmed attendees
        confirmed_registrations = EventRegistration.query.filter_by(
            event_id=event_id, payment_status='confirmed'
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        attendees_data = []
        for registration in confirmed_registrations.items:
            attendee_data = registration.user.to_dict()
            attendee_data['registration_info'] = {
                'registered_at': registration.registered_at.isoformat() if registration.registered_at else None,
                'attendance_status': registration.attendance_status
            }
            attendees_data.append(attendee_data)
        
        return jsonify({
            'attendees': attendees_data,
            'total': confirmed_registrations.total,
            'pages': confirmed_registrations.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/my-events', methods=['GET'])
@jwt_required()
def get_my_events():
    """Get events that the current user is attending or organizing"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get events user is attending
        attending_events = Event.query.join(EventRegistration).filter(
            EventRegistration.user_id == current_user_id,
            EventRegistration.payment_status == 'confirmed'
        ).all()
        
        # Get events user is organizing
        organizing_events = Event.query.filter_by(created_by=current_user_id).all()
        
        events_data = {
            'attending': [event.to_dict() for event in attending_events],
            'organizing': [event.to_dict() for event in organizing_events]
        }
        
        return jsonify(events_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/my-registrations', methods=['GET'])
@jwt_required()
def get_my_registrations():
    """Get current user's event registrations"""
    try:
        current_user_id = get_jwt_identity()
        
        registrations = EventRegistration.query.filter_by(
            user_id=current_user_id
        ).order_by(EventRegistration.registered_at.desc()).all()
        
        registrations_data = []
        for reg in registrations:
            reg_data = reg.to_dict()
            reg_data['event'] = reg.event.to_dict()
            registrations_data.append(reg_data)
        
        return jsonify({'registrations': registrations_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/upcoming', methods=['GET'])
def get_upcoming_events():
    """Get upcoming events"""
    try:
        limit = request.args.get('limit', 6, type=int)
        
        events = Event.query.filter(
            Event.start_date >= datetime.utcnow()
        ).order_by(Event.start_date.asc()).limit(limit).all()
        
        return jsonify({
            'events': [event.to_dict() for event in events]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/featured', methods=['GET'])
def get_featured_events():
    """Get featured events"""
    try:
        limit = request.args.get('limit', 6, type=int)
        
        events = Event.query.filter_by(is_featured=True)\
            .filter(Event.start_date >= datetime.utcnow())\
            .order_by(Event.start_date.asc())\
            .limit(limit).all()
        
        return jsonify({
            'events': [event.to_dict() for event in events]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/stats', methods=['GET'])
def get_event_stats():
    """Get overall event statistics"""
    try:
        total_events = Event.query.count()
        upcoming_events = Event.query.filter(Event.start_date >= datetime.utcnow()).count()
        total_registrations = EventRegistration.query.count()
        
        # Events by type
        event_types = db.session.query(
            Event.event_type, 
            db.func.count(Event.id)
        ).group_by(Event.event_type).all()
        
        return jsonify({
            'total_events': total_events,
            'upcoming_events': upcoming_events,
            'total_registrations': total_registrations,
            'events_by_type': [{'type': et[0], 'count': et[1]} for et in event_types]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@event_bp.route('/<int:event_id>/check-in/<int:user_id>', methods=['POST'])
@jwt_required()
def check_in_attendee(event_id, user_id):
    """Check in an attendee (only for event creator)"""
    try:
        current_user_id = get_jwt_identity()
        event = Event.query.get_or_404(event_id)
        
        if event.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        registration = EventRegistration.query.filter_by(
            event_id=event_id, user_id=user_id
        ).first()
        
        if not registration:
            return jsonify({'error': 'User is not registered for this event'}), 400
        
        registration.attendance_status = 'attended'
        db.session.commit()
        
        return jsonify({'message': 'Attendee checked in successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
