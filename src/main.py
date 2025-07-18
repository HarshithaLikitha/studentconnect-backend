import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.models.enhanced_models import db

# Import enhanced routes
from src.routes.auth import auth_bp
from src.routes.enhanced_community import community_bp
from src.routes.enhanced_project import project_bp
from src.routes.post import post_bp
from src.routes.enhanced_event import event_bp
from src.routes.enhanced_tutorial import tutorial_bp
from src.routes.enhanced_message import message_bp
from src.routes.skill import skill_bp

# Import original user route (can be enhanced later)
from src.routes.user import user_bp

def create_app():
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'student-connect-secret-key-2024-enhanced')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string-student-connect-2024-enhanced')
    
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
    
    # Register blueprints with enhanced routes
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(community_bp, url_prefix='/api/communities')
    app.register_blueprint(project_bp, url_prefix='/api/projects')
    app.register_blueprint(post_bp, url_prefix='/api/posts')
    app.register_blueprint(event_bp, url_prefix='/api/events')
    app.register_blueprint(tutorial_bp, url_prefix='/api/tutorials')
    app.register_blueprint(message_bp, url_prefix='/api/messages')
    app.register_blueprint(skill_bp, url_prefix='/api/skills')
    
    # Create tables and populate default data
    with app.app_context():
        db.create_all()
        populate_default_data()
    
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
                return "Enhanced StudentConnect API is running! Visit /api/auth/me to test.", 200

    @app.route('/health')
    def health_check():
        return {
            'status': 'healthy', 
            'message': 'Enhanced StudentConnect API is running!',
            'features': [
                'Communities with moderation',
                'Collaborative Projects',
                'Events & Hackathons',
                'Tutorials with GeeksforGeeks integration',
                'Real-time Messaging',
                'Skill Development & Endorsements'
            ]
        }, 200
    
    return app

def populate_default_data():
    """Populate database with default skills and sample data"""
    from src.models.enhanced_models import Skill
    
    # Check if skills already exist
    if Skill.query.count() > 0:
        return
    
    # Default skills by category
    default_skills = {
        'Programming': [
            'Python', 'JavaScript', 'Java', 'C++', 'C#', 'PHP', 'Ruby', 'Go', 'Rust', 'Swift',
            'Kotlin', 'TypeScript', 'Scala', 'R', 'MATLAB', 'Perl', 'Dart', 'Elixir'
        ],
        'Web Development': [
            'HTML', 'CSS', 'React', 'Vue.js', 'Angular', 'Node.js', 'Express.js', 'Django',
            'Flask', 'Laravel', 'Spring Boot', 'ASP.NET', 'Bootstrap', 'Tailwind CSS',
            'jQuery', 'Webpack', 'Sass/SCSS', 'GraphQL'
        ],
        'Mobile Development': [
            'React Native', 'Flutter', 'iOS Development', 'Android Development', 'Xamarin',
            'Ionic', 'Cordova', 'Unity', 'Unreal Engine'
        ],
        'Data Science': [
            'Machine Learning', 'Deep Learning', 'Data Analysis', 'Statistics', 'Pandas',
            'NumPy', 'Scikit-learn', 'TensorFlow', 'PyTorch', 'Keras', 'Matplotlib',
            'Seaborn', 'Jupyter', 'Apache Spark', 'Hadoop'
        ],
        'Database': [
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'SQLite', 'Oracle', 'SQL Server',
            'Cassandra', 'DynamoDB', 'Elasticsearch', 'Neo4j'
        ],
        'DevOps': [
            'Docker', 'Kubernetes', 'AWS', 'Azure', 'Google Cloud', 'Jenkins', 'GitLab CI',
            'GitHub Actions', 'Terraform', 'Ansible', 'Chef', 'Puppet', 'Nginx', 'Apache'
        ],
        'Design': [
            'UI/UX Design', 'Figma', 'Adobe Photoshop', 'Adobe Illustrator', 'Sketch',
            'InVision', 'Adobe XD', 'Canva', 'Blender', '3D Modeling', 'Animation'
        ],
        'Project Management': [
            'Agile', 'Scrum', 'Kanban', 'Jira', 'Trello', 'Asana', 'Monday.com',
            'Project Planning', 'Risk Management', 'Team Leadership'
        ],
        'Cloud Computing': [
            'Amazon Web Services', 'Microsoft Azure', 'Google Cloud Platform', 'Heroku',
            'DigitalOcean', 'Linode', 'Serverless', 'Lambda Functions', 'Cloud Architecture'
        ],
        'Cybersecurity': [
            'Ethical Hacking', 'Penetration Testing', 'Network Security', 'Cryptography',
            'Security Auditing', 'Incident Response', 'Malware Analysis', 'OWASP'
        ],
        'Testing': [
            'Unit Testing', 'Integration Testing', 'Automated Testing', 'Selenium',
            'Jest', 'Cypress', 'Postman', 'Load Testing', 'Performance Testing'
        ],
        'Blockchain': [
            'Ethereum', 'Smart Contracts', 'Solidity', 'Web3', 'DeFi', 'NFT',
            'Cryptocurrency', 'Bitcoin', 'Hyperledger'
        ]
    }
    
    # Create skills
    for category, skills in default_skills.items():
        for skill_name in skills:
            skill = Skill(
                name=skill_name,
                category=category,
                description=f"{skill_name} - {category} skill"
            )
            db.session.add(skill)
    
    try:
        db.session.commit()
        print("Default skills populated successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error populating default skills: {str(e)}")

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
