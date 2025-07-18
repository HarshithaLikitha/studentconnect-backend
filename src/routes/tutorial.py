from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.enhanced_models import Tutorial, User, TutorialProgress, db
from sqlalchemy import or_, and_
from datetime import datetime
import json
import requests
from bs4 import BeautifulSoup
import re

tutorial_bp = Blueprint('tutorial', __name__)

# GeeksforGeeks content categories and topics
GFG_CATEGORIES = {
    'programming': [
        'python', 'java', 'cpp', 'javascript', 'c', 'csharp', 'php', 'ruby', 'go', 'rust'
    ],
    'data-structures': [
        'array', 'linked-list', 'stack', 'queue', 'tree', 'graph', 'heap', 'hash'
    ],
    'algorithms': [
        'sorting', 'searching', 'dynamic-programming', 'greedy', 'backtracking', 'divide-conquer'
    ],
    'web-development': [
        'html', 'css', 'react', 'nodejs', 'express', 'mongodb', 'sql', 'bootstrap'
    ],
    'machine-learning': [
        'python-ml', 'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy'
    ],
    'system-design': [
        'scalability', 'databases', 'caching', 'load-balancing', 'microservices'
    ]
}

def scrape_gfg_tutorial(topic, category='programming'):
    """Scrape tutorial content from GeeksforGeeks"""
    try:
        # Construct GeeksforGeeks URL
        base_url = "https://www.geeksforgeeks.org"
        search_url = f"{base_url}/{topic}/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        title = title_elem.get_text().strip() if title_elem else f"{topic.replace('-', ' ').title()} Tutorial"
        
        # Extract description from meta description or first paragraph
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')
        else:
            first_p = soup.find('p')
            if first_p:
                description = first_p.get_text().strip()[:200] + "..."
        
        # Extract main content
        content = ""
        content_div = soup.find('div', class_='text') or soup.find('article') or soup.find('main')
        if content_div:
            # Remove script and style elements
            for script in content_div(["script", "style"]):
                script.decompose()
            content = content_div.get_text().strip()[:2000] + "..."
        
        # Extract code examples
        code_examples = []
        code_blocks = soup.find_all('pre') or soup.find_all('code')
        for i, code_block in enumerate(code_blocks[:3]):  # Limit to 3 examples
            code_examples.append({
                'title': f'Example {i+1}',
                'code': code_block.get_text().strip(),
                'language': 'python'  # Default, could be improved with detection
            })
        
        return {
            'title': title,
            'description': description,
            'content': content,
            'source_url': search_url,
            'code_examples': code_examples,
            'category': category,
            'difficulty': 'intermediate',
            'tags': [topic, 'geeksforgeeks', category],
            'prerequisites': [],
            'learning_outcomes': [
                f"Understand {topic.replace('-', ' ')} concepts",
                f"Learn practical applications of {topic.replace('-', ' ')}",
                "Solve related programming problems"
            ]
        }
    except Exception as e:
        print(f"Error scraping GFG content for {topic}: {str(e)}")
        return None

@tutorial_bp.route('/', methods=['GET'])
def get_tutorials():
    """Get all tutorials with filtering and pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        category = request.args.get('category')
        difficulty = request.args.get('difficulty')
        source = request.args.get('source')
        search = request.args.get('search')
        
        query = Tutorial.query
        
        # Apply filters
        if category:
            query = query.filter_by(category=category)
        
        if difficulty:
            query = query.filter_by(difficulty=difficulty)
        
        if source:
            query = query.filter_by(source=source)
        
        if search:
            query = query.filter(
                or_(
                    Tutorial.title.ilike(f'%{search}%'),
                    Tutorial.description.ilike(f'%{search}%'),
                    Tutorial.tags.ilike(f'%{search}%')
                )
            )
        
        # Order by rating, view count, and creation date
        query = query.order_by(
            Tutorial.rating.desc(),
            Tutorial.view_count.desc(),
            Tutorial.created_at.desc()
        )
        
        tutorials = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'tutorials': [tutorial.to_dict() for tutorial in tutorials.items],
            'total': tutorials.total,
            'pages': tutorials.pages,
            'current_page': page,
            'has_next': tutorials.has_next,
            'has_prev': tutorials.has_prev
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/categories', methods=['GET'])
def get_tutorial_categories():
    """Get all available tutorial categories"""
    try:
        # Get categories from database
        db_categories = db.session.query(Tutorial.category).distinct().filter(
            Tutorial.category.isnot(None),
            Tutorial.category != ''
        ).all()
        
        db_category_list = [cat[0] for cat in db_categories if cat[0]]
        
        # Combine with predefined categories
        all_categories = list(set(db_category_list + list(GFG_CATEGORIES.keys())))
        
        return jsonify({
            'categories': all_categories,
            'gfg_categories': GFG_CATEGORIES
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/gfg-topics/<category>', methods=['GET'])
def get_gfg_topics(category):
    """Get GeeksforGeeks topics for a specific category"""
    try:
        topics = GFG_CATEGORIES.get(category, [])
        return jsonify({'topics': topics}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/<int:tutorial_id>', methods=['GET'])
def get_tutorial(tutorial_id):
    """Get a specific tutorial with detailed information"""
    try:
        tutorial = Tutorial.query.get_or_404(tutorial_id)
        
        # Increment view count
        tutorial.view_count = (tutorial.view_count or 0) + 1
        db.session.commit()
        
        tutorial_data = tutorial.to_dict()
        
        # Get user progress if authenticated
        current_user_id = None
        try:
            current_user_id = get_jwt_identity()
        except:
            pass
        
        if current_user_id:
            progress = TutorialProgress.query.filter_by(
                tutorial_id=tutorial_id, user_id=current_user_id
            ).first()
            
            if progress:
                tutorial_data['user_progress'] = progress.to_dict()
        
        return jsonify(tutorial_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/', methods=['POST'])
@jwt_required()
def create_tutorial():
    """Create a new tutorial"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Tutorial title is required'}), 400
        
        if not data.get('description'):
            return jsonify({'error': 'Tutorial description is required'}), 400
        
        if not data.get('category'):
            return jsonify({'error': 'Tutorial category is required'}), 400
        
        tutorial = Tutorial(
            title=data['title'],
            description=data['description'],
            content=data.get('content', ''),
            category=data['category'],
            difficulty=data.get('difficulty', 'beginner'),
            duration=data.get('duration', ''),
            tags=json.dumps(data.get('tags', [])),
            video_url=data.get('video_url', ''),
            external_url=data.get('external_url', ''),
            image_url=data.get('image_url', ''),
            created_by=current_user_id,
            
            # Enhanced fields
            source=data.get('source', 'internal'),
            source_url=data.get('source_url', ''),
            prerequisites=data.get('prerequisites', []),
            learning_outcomes=data.get('learning_outcomes', []),
            code_examples=data.get('code_examples', []),
            quiz_questions=data.get('quiz_questions', []),
            completion_rate=0.0,
            rating=0.0,
            view_count=0,
            bookmark_count=0
        )
        
        db.session.add(tutorial)
        db.session.commit()
        
        return jsonify(tutorial.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/import-gfg', methods=['POST'])
@jwt_required()
def import_gfg_tutorial():
    """Import a tutorial from GeeksforGeeks"""
    try:
        current_user_id = get_jwt_identity()
        data = request.json
        
        topic = data.get('topic')
        category = data.get('category', 'programming')
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        # Check if tutorial already exists
        existing_tutorial = Tutorial.query.filter_by(
            source='geeksforgeeks',
            source_url=f"https://www.geeksforgeeks.org/{topic}/"
        ).first()
        
        if existing_tutorial:
            return jsonify({
                'message': 'Tutorial already exists',
                'tutorial': existing_tutorial.to_dict()
            }), 200
        
        # Scrape content from GeeksforGeeks
        gfg_content = scrape_gfg_tutorial(topic, category)
        
        if not gfg_content:
            return jsonify({'error': 'Failed to fetch content from GeeksforGeeks'}), 400
        
        # Create tutorial from scraped content
        tutorial = Tutorial(
            title=gfg_content['title'],
            description=gfg_content['description'],
            content=gfg_content['content'],
            category=gfg_content['category'],
            difficulty=gfg_content['difficulty'],
            duration=data.get('duration', '30-60 minutes'),
            tags=json.dumps(gfg_content['tags']),
            created_by=current_user_id,
            
            # Enhanced fields
            source='geeksforgeeks',
            source_url=gfg_content['source_url'],
            prerequisites=gfg_content['prerequisites'],
            learning_outcomes=gfg_content['learning_outcomes'],
            code_examples=gfg_content['code_examples'],
            completion_rate=0.0,
            rating=0.0,
            view_count=0,
            bookmark_count=0
        )
        
        db.session.add(tutorial)
        db.session.commit()
        
        return jsonify({
            'message': 'Tutorial imported successfully from GeeksforGeeks',
            'tutorial': tutorial.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/<int:tutorial_id>', methods=['PUT'])
@jwt_required()
def update_tutorial(tutorial_id):
    """Update a tutorial (only by creator)"""
    try:
        current_user_id = get_jwt_identity()
        tutorial = Tutorial.query.get_or_404(tutorial_id)
        
        if tutorial.created_by != current_user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        data = request.json
        
        # Update fields
        if 'title' in data:
            tutorial.title = data['title']
        if 'description' in data:
            tutorial.description = data['description']
        if 'content' in data:
            tutorial.content = data['content']
        if 'category' in data:
            tutorial.category = data['category']
        if 'difficulty' in data:
            tutorial.difficulty = data['difficulty']
        if 'duration' in data:
            tutorial.duration = data['duration']
        if 'tags' in data:
            tutorial.tags = json.dumps(data['tags'])
        if 'video_url' in data:
            tutorial.video_url = data['video_url']
        if 'external_url' in data:
            tutorial.external_url = data['external_url']
        if 'image_url' in data:
            tutorial.image_url = data['image_url']
        if 'prerequisites' in data:
            tutorial.prerequisites = data['prerequisites']
        if 'learning_outcomes' in data:
            tutorial.learning_outcomes = data['learning_outcomes']
        if 'code_examples' in data:
            tutorial.code_examples = data['code_examples']
        if 'quiz_questions' in data:
            tutorial.quiz_questions = data['quiz_questions']
        
        tutorial.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(tutorial.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/<int:tutorial_id>', methods=['DELETE'])
@jwt_required()
def delete_tutorial(tutorial_id):
    """Delete a tutorial (only by creator)"""
    try:
        current_user_id = get_jwt_identity()
        tutorial = Tutorial.query.get_or_404(tutorial_id)
        
        if tutorial.created_by != current_user_id:
            return jsonify({'error': 'Only the tutorial creator can delete it'}), 403
        
        db.session.delete(tutorial)
        db.session.commit()
        
        return '', 204
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/<int:tutorial_id>/progress', methods=['POST'])
@jwt_required()
def update_progress(tutorial_id):
    """Update user's progress on a tutorial"""
    try:
        current_user_id = get_jwt_identity()
        tutorial = Tutorial.query.get_or_404(tutorial_id)
        
        data = request.json
        progress_percentage = data.get('progress_percentage', 0)
        completed_sections = data.get('completed_sections', [])
        time_spent = data.get('time_spent', 0)
        
        # Find or create progress record
        progress = TutorialProgress.query.filter_by(
            tutorial_id=tutorial_id, user_id=current_user_id
        ).first()
        
        if not progress:
            progress = TutorialProgress(
                tutorial_id=tutorial_id,
                user_id=current_user_id,
                progress_percentage=0,
                completed_sections=[],
                time_spent=0,
                is_completed=False
            )
            db.session.add(progress)
        
        # Update progress
        progress.progress_percentage = progress_percentage
        progress.completed_sections = completed_sections
        progress.time_spent = (progress.time_spent or 0) + time_spent
        
        if progress_percentage >= 100:
            progress.is_completed = True
            progress.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Update tutorial completion rate
        total_users = TutorialProgress.query.filter_by(tutorial_id=tutorial_id).count()
        completed_users = TutorialProgress.query.filter_by(
            tutorial_id=tutorial_id, is_completed=True
        ).count()
        
        if total_users > 0:
            tutorial.completion_rate = (completed_users / total_users) * 100
            db.session.commit()
        
        return jsonify({
            'message': 'Progress updated successfully',
            'progress': progress.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/<int:tutorial_id>/bookmark', methods=['POST'])
@jwt_required()
def bookmark_tutorial(tutorial_id):
    """Bookmark or unbookmark a tutorial"""
    try:
        current_user_id = get_jwt_identity()
        tutorial = Tutorial.query.get_or_404(tutorial_id)
        
        # This would require a TutorialBookmark model, but for simplicity
        # we'll just increment/decrement the bookmark count
        action = request.json.get('action', 'bookmark')  # bookmark or unbookmark
        
        if action == 'bookmark':
            tutorial.bookmark_count = (tutorial.bookmark_count or 0) + 1
            message = 'Tutorial bookmarked successfully'
        else:
            tutorial.bookmark_count = max(0, (tutorial.bookmark_count or 1) - 1)
            message = 'Tutorial unbookmarked successfully'
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'bookmark_count': tutorial.bookmark_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/my-progress', methods=['GET'])
@jwt_required()
def get_my_progress():
    """Get current user's tutorial progress"""
    try:
        current_user_id = get_jwt_identity()
        
        progress_records = TutorialProgress.query.filter_by(
            user_id=current_user_id
        ).order_by(TutorialProgress.started_at.desc()).all()
        
        progress_data = []
        for progress in progress_records:
            progress_info = progress.to_dict()
            progress_info['tutorial'] = progress.tutorial.to_dict()
            progress_data.append(progress_info)
        
        return jsonify({'progress': progress_data}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/popular', methods=['GET'])
def get_popular_tutorials():
    """Get popular tutorials based on views and ratings"""
    try:
        limit = request.args.get('limit', 6, type=int)
        
        tutorials = Tutorial.query.order_by(
            Tutorial.view_count.desc(),
            Tutorial.rating.desc()
        ).limit(limit).all()
        
        return jsonify({
            'tutorials': [tutorial.to_dict() for tutorial in tutorials]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/recent', methods=['GET'])
def get_recent_tutorials():
    """Get recently added tutorials"""
    try:
        limit = request.args.get('limit', 6, type=int)
        
        tutorials = Tutorial.query.order_by(
            Tutorial.created_at.desc()
        ).limit(limit).all()
        
        return jsonify({
            'tutorials': [tutorial.to_dict() for tutorial in tutorials]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/stats', methods=['GET'])
def get_tutorial_stats():
    """Get overall tutorial statistics"""
    try:
        total_tutorials = Tutorial.query.count()
        gfg_tutorials = Tutorial.query.filter_by(source='geeksforgeeks').count()
        internal_tutorials = Tutorial.query.filter_by(source='internal').count()
        total_progress_records = TutorialProgress.query.count()
        completed_tutorials = TutorialProgress.query.filter_by(is_completed=True).count()
        
        # Tutorials by category
        categories = db.session.query(
            Tutorial.category, 
            db.func.count(Tutorial.id)
        ).group_by(Tutorial.category).all()
        
        return jsonify({
            'total_tutorials': total_tutorials,
            'gfg_tutorials': gfg_tutorials,
            'internal_tutorials': internal_tutorials,
            'total_progress_records': total_progress_records,
            'completed_tutorials': completed_tutorials,
            'completion_rate': (completed_tutorials / total_progress_records * 100) if total_progress_records > 0 else 0,
            'tutorials_by_category': [{'category': cat[0], 'count': cat[1]} for cat in categories]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tutorial_bp.route('/search', methods=['GET'])
def search_tutorials():
    """Search tutorials with advanced filtering"""
    try:
        query = request.args.get('q', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        category = request.args.get('category')
        difficulty = request.args.get('difficulty')
        source = request.args.get('source')
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        search_query = Tutorial.query.filter(
            or_(
                Tutorial.title.ilike(f'%{query}%'),
                Tutorial.description.ilike(f'%{query}%'),
                Tutorial.tags.ilike(f'%{query}%')
            )
        )
        
        # Apply additional filters
        if category:
            search_query = search_query.filter_by(category=category)
        
        if difficulty:
            search_query = search_query.filter_by(difficulty=difficulty)
        
        if source:
            search_query = search_query.filter_by(source=source)
        
        tutorials = search_query.order_by(
            Tutorial.rating.desc(),
            Tutorial.view_count.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'tutorials': [tutorial.to_dict() for tutorial in tutorials.items],
            'total': tutorials.total,
            'pages': tutorials.pages,
            'current_page': page,
            'query': query
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
