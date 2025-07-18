from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import json

db = SQLAlchemy()

# Association tables for many-to-many relationships
user_communities = db.Table('user_communities',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('community_id', db.Integer, db.ForeignKey('community.id'), primary_key=True)
)

user_projects = db.Table('user_projects',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True)
)

user_events = db.Table('user_events',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True)
)

community_moderators = db.Table('community_moderators',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('community_id', db.Integer, db.ForeignKey('community.id'), primary_key=True)
)

chat_room_participants = db.Table('chat_room_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('chat_room_id', db.Integer, db.ForeignKey('chat_room.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(255))
    college = db.Column(db.String(100))
    major = db.Column(db.String(100))
    year = db.Column(db.String(20))
    skills = db.Column(db.Text)  # JSON string of skills array
    github_url = db.Column(db.String(255))
    linkedin_url = db.Column(db.String(255))
    portfolio_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    
    # Enhanced fields
    reputation_score = db.Column(db.Integer, default=0)
    total_projects = db.Column(db.Integer, default=0)
    total_communities = db.Column(db.Integer, default=0)
    total_events_attended = db.Column(db.Integer, default=0)
    skill_endorsements = db.Column(db.JSON)
    location = db.Column(db.String(100))
    timezone = db.Column(db.String(50))
    is_mentor = db.Column(db.Boolean, default=False)
    mentor_categories = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy=True, cascade='all, delete-orphan')
    communities = db.relationship('Community', secondary=user_communities, lazy='subquery',
                                backref=db.backref('members', lazy=True))
    projects = db.relationship('Project', secondary=user_projects, lazy='subquery',
                             backref=db.backref('members', lazy=True))
    events = db.relationship('Event', secondary=user_events, lazy='subquery',
                           backref=db.backref('attendees', lazy=True))
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)
    
    # Enhanced relationships
    moderated_communities = db.relationship('Community', secondary=community_moderators, lazy='subquery',
                                          backref=db.backref('moderators', lazy=True))
    user_skills = db.relationship('UserSkill', backref='user', lazy=True, cascade='all, delete-orphan')
    project_roles = db.relationship('ProjectRole', backref='user', lazy=True, cascade='all, delete-orphan')
    project_applications = db.relationship('ProjectApplication', foreign_keys='ProjectApplication.applicant_id', 
                                         backref='applicant', lazy=True)
    event_registrations = db.relationship('EventRegistration', backref='user', lazy=True, cascade='all, delete-orphan')
    tutorial_progress = db.relationship('TutorialProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    chat_rooms = db.relationship('ChatRoom', secondary=chat_room_participants, lazy='subquery',
                               backref=db.backref('participants', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'college': self.college,
            'major': self.major,
            'year': self.year,
            'skills': self.skills,
            'github_url': self.github_url,
            'linkedin_url': self.linkedin_url,
            'portfolio_url': self.portfolio_url,
            'is_active': self.is_active,
            'reputation_score': self.reputation_score,
            'total_projects': self.total_projects,
            'total_communities': self.total_communities,
            'total_events_attended': self.total_events_attended,
            'location': self.location,
            'timezone': self.timezone,
            'is_mentor': self.is_mentor,
            'mentor_categories': self.mentor_categories,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Community(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    image_url = db.Column(db.String(255))
    is_private = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Enhanced fields
    tags = db.Column(db.JSON)
    rules = db.Column(db.Text)
    member_count = db.Column(db.Integer, default=0)
    post_count = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    activity_score = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='community', lazy=True, cascade='all, delete-orphan')
    creator = db.relationship('User', backref='created_communities')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'image_url': self.image_url,
            'is_private': self.is_private,
            'created_by': self.created_by,
            'tags': self.tags,
            'rules': self.rules,
            'member_count': self.member_count or len(self.members),
            'post_count': self.post_count,
            'is_featured': self.is_featured,
            'activity_score': self.activity_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'creator': self.creator.to_dict() if self.creator else None,
            'moderators': [mod.to_dict() for mod in self.moderators] if hasattr(self, 'moderators') else []
        }

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    tech_stack = db.Column(db.Text)  # JSON string of technologies
    status = db.Column(db.String(20), default='active')  # active, completed, paused
    github_url = db.Column(db.String(255))
    demo_url = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    looking_for = db.Column(db.Text)  # JSON string of roles needed
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Enhanced fields
    project_type = db.Column(db.String(50), default='open_source')  # open_source, hackathon, academic, startup
    difficulty_level = db.Column(db.String(20), default='intermediate')  # beginner, intermediate, advanced
    estimated_duration = db.Column(db.String(50))
    required_skills = db.Column(db.JSON)
    current_team_size = db.Column(db.Integer, default=1)
    max_team_size = db.Column(db.Integer, default=5)
    progress_percentage = db.Column(db.Integer, default=0)
    is_recruiting = db.Column(db.Boolean, default=True)
    tags = db.Column(db.JSON)
    featured_image = db.Column(db.String(255))
    screenshots = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref='created_projects')
    project_roles = db.relationship('ProjectRole', backref='project', lazy=True, cascade='all, delete-orphan')
    applications = db.relationship('ProjectApplication', backref='project', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'tech_stack': self.tech_stack,
            'status': self.status,
            'github_url': self.github_url,
            'demo_url': self.demo_url,
            'image_url': self.image_url,
            'looking_for': self.looking_for,
            'created_by': self.created_by,
            'project_type': self.project_type,
            'difficulty_level': self.difficulty_level,
            'estimated_duration': self.estimated_duration,
            'required_skills': self.required_skills,
            'current_team_size': self.current_team_size,
            'max_team_size': self.max_team_size,
            'progress_percentage': self.progress_percentage,
            'is_recruiting': self.is_recruiting,
            'tags': self.tags,
            'featured_image': self.featured_image,
            'screenshots': self.screenshots,
            'member_count': len(self.members),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'creator': self.creator.to_dict() if self.creator else None
        }

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(50))  # hackathon, workshop, meetup, conference
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    location = db.Column(db.String(255))
    is_virtual = db.Column(db.Boolean, default=False)
    meeting_url = db.Column(db.String(255))
    max_attendees = db.Column(db.Integer)
    registration_deadline = db.Column(db.DateTime)
    image_url = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Enhanced fields
    organizer_info = db.Column(db.JSON)
    agenda = db.Column(db.JSON)
    prerequisites = db.Column(db.JSON)
    prizes = db.Column(db.JSON)
    sponsors = db.Column(db.JSON)
    tags = db.Column(db.JSON)
    difficulty_level = db.Column(db.String(20))
    is_featured = db.Column(db.Boolean, default=False)
    registration_fee = db.Column(db.Numeric(10, 2), default=0.00)
    certificate_available = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref='created_events')
    registrations = db.relationship('EventRegistration', backref='event', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'event_type': self.event_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'is_virtual': self.is_virtual,
            'meeting_url': self.meeting_url,
            'max_attendees': self.max_attendees,
            'registration_deadline': self.registration_deadline.isoformat() if self.registration_deadline else None,
            'image_url': self.image_url,
            'created_by': self.created_by,
            'organizer_info': self.organizer_info,
            'agenda': self.agenda,
            'prerequisites': self.prerequisites,
            'prizes': self.prizes,
            'sponsors': self.sponsors,
            'tags': self.tags,
            'difficulty_level': self.difficulty_level,
            'is_featured': self.is_featured,
            'registration_fee': float(self.registration_fee) if self.registration_fee else 0.0,
            'certificate_available': self.certificate_available,
            'attendees_count': len(self.attendees),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'creator': self.creator.to_dict() if self.creator else None
        }

class Tutorial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    category = db.Column(db.String(50))
    difficulty = db.Column(db.String(20))  # beginner, intermediate, advanced
    duration = db.Column(db.String(50))  # estimated time
    tags = db.Column(db.Text)  # JSON string of tags
    video_url = db.Column(db.String(255))
    external_url = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Enhanced fields
    source = db.Column(db.String(50), default='internal')  # internal, geeksforgeeks, external
    source_url = db.Column(db.String(255))
    prerequisites = db.Column(db.JSON)
    learning_outcomes = db.Column(db.JSON)
    code_examples = db.Column(db.JSON)
    quiz_questions = db.Column(db.JSON)
    completion_rate = db.Column(db.Float, default=0.0)
    rating = db.Column(db.Float, default=0.0)
    view_count = db.Column(db.Integer, default=0)
    bookmark_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref='created_tutorials')
    progress_records = db.relationship('TutorialProgress', backref='tutorial', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'content': self.content,
            'category': self.category,
            'difficulty': self.difficulty,
            'duration': self.duration,
            'tags': self.tags,
            'video_url': self.video_url,
            'external_url': self.external_url,
            'image_url': self.image_url,
            'created_by': self.created_by,
            'source': self.source,
            'source_url': self.source_url,
            'prerequisites': self.prerequisites,
            'learning_outcomes': self.learning_outcomes,
            'code_examples': self.code_examples,
            'quiz_questions': self.quiz_questions,
            'completion_rate': self.completion_rate,
            'rating': self.rating,
            'view_count': self.view_count,
            'bookmark_count': self.bookmark_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'creator': self.creator.to_dict() if self.creator else None
        }

# Keep existing models for compatibility
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.String(20), default='general')  # general, blog, announcement
    image_url = db.Column(db.String(255))
    likes_count = db.Column(db.Integer, default=0)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    community_id = db.Column(db.Integer, db.ForeignKey('community.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='post', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'post_type': self.post_type,
            'image_url': self.image_url,
            'likes_count': self.likes_count,
            'author_id': self.author_id,
            'community_id': self.community_id,
            'comments_count': len(self.comments),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'author': self.author.to_dict() if self.author else None
        }

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'))  # For nested comments
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'author_id': self.author_id,
            'post_id': self.post_id,
            'parent_id': self.parent_id,
            'replies_count': len(self.replies),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'author': self.author.to_dict() if self.author else None
        }

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate likes
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50))  # message, event, community, project
    related_id = db.Column(db.Integer)  # ID of related object
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type,
            'related_id': self.related_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# New enhanced models
class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50))  # programming, design, management, etc.
    description = db.Column(db.Text)
    icon_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'icon_url': self.icon_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class UserSkill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    proficiency_level = db.Column(db.String(20))  # beginner, intermediate, advanced, expert
    years_experience = db.Column(db.Integer)
    endorsement_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    skill = db.relationship('Skill', backref='user_skills')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'skill_id': self.skill_id,
            'proficiency_level': self.proficiency_level,
            'years_experience': self.years_experience,
            'endorsement_count': self.endorsement_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'skill': self.skill.to_dict() if self.skill else None
        }

class SkillEndorsement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endorser_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    endorsed_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skill.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    endorser = db.relationship('User', foreign_keys=[endorser_id], backref='given_endorsements')
    endorsed_user = db.relationship('User', foreign_keys=[endorsed_user_id], backref='received_endorsements')
    skill = db.relationship('Skill', backref='endorsements')

    def to_dict(self):
        return {
            'id': self.id,
            'endorser_id': self.endorser_id,
            'endorsed_user_id': self.endorsed_user_id,
            'skill_id': self.skill_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ProjectRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_name = db.Column(db.String(100), nullable=False)  # Frontend Dev, Designer, etc.
    responsibilities = db.Column(db.Text)
    is_lead = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role_name': self.role_name,
            'responsibilities': self.responsibilities,
            'is_lead': self.is_lead,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'user': self.user.to_dict() if self.user else None
        }

class ProjectApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_applied_for = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_applications')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'applicant_id': self.applicant_id,
            'role_applied_for': self.role_applied_for,
            'message': self.message,
            'status': self.status,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': self.reviewed_by,
            'applicant': self.applicant.to_dict() if self.applicant else None
        }

class EventRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    registration_data = db.Column(db.JSON)  # Additional registration info
    payment_status = db.Column(db.String(20), default='pending')
    attendance_status = db.Column(db.String(20), default='registered')
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'registration_data': self.registration_data,
            'payment_status': self.payment_status,
            'attendance_status': self.attendance_status,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'user': self.user.to_dict() if self.user else None
        }

class TutorialProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tutorial_id = db.Column(db.Integer, db.ForeignKey('tutorial.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    progress_percentage = db.Column(db.Integer, default=0)
    completed_sections = db.Column(db.JSON)  # Array of completed section IDs
    time_spent = db.Column(db.Integer, default=0)  # Time in minutes
    is_completed = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'tutorial_id': self.tutorial_id,
            'user_id': self.user_id,
            'progress_percentage': self.progress_percentage,
            'completed_sections': self.completed_sections,
            'time_spent': self.time_spent,
            'is_completed': self.is_completed,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class ChatRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    room_type = db.Column(db.String(20))  # direct, group, community, project
    related_id = db.Column(db.Integer)  # ID of related community/project
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref='created_chat_rooms')
    messages = db.relationship('ChatMessage', backref='room', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'room_type': self.room_type,
            'related_id': self.related_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'participant_count': len(self.participants)
        }

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, image, file
    file_url = db.Column(db.String(255))
    is_edited = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime)
    
    # Relationships
    sender = db.relationship('User', backref='chat_messages')

    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'message_type': self.message_type,
            'file_url': self.file_url,
            'is_edited': self.is_edited,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'sender': self.sender.to_dict() if self.sender else None
        }



