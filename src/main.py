import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.models.models import db
from src.routes.auth import auth_bp
from src.routes.user import user_bp
from src.routes.community import community_bp
from src.routes.project import project_bp
from src.routes.post import post_bp
from src.routes.event import event_bp
from src.routes.tutorial import tutorial_bp
from src.routes.message import message_bp

def create_app():
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'student-connect-secret-key-2024')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string-student-connect-2024')
    
    # Database configuration - use PostgreSQL in production, SQLite in development
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Production database (PostgreSQL)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Development database (SQLite)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    jwt = JWTManager(app)
    CORS(app, origins="*")
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(community_bp, url_prefix='/api/communities')
    app.register_blueprint(project_bp, url_prefix='/api/projects')
    app.register_blueprint(post_bp, url_prefix='/api/posts')
    app.register_blueprint(event_bp, url_prefix='/api/events')
    app.register_blueprint(tutorial_bp, url_prefix='/api/tutorials')
    app.register_blueprint(message_bp, url_prefix='/api/messages')
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "API is running! Visit /api/auth/me to test.", 200

    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'message': 'StudentConnect API is running!'}, 200
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

