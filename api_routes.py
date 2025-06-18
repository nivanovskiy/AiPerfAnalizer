from flask import Blueprint, request, jsonify
from app import db
from models import Project, ProjectFile, Issue, ProjectStatus, IssueType
from project_processor import ProjectProcessor
import logging
import threading

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# Global processor instance
processor = ProjectProcessor()

@api_bp.route('/initialize', methods=['POST'])
def initialize_project():
    """Initialize a new project with the expected number of files"""
    try:
        data = request.get_json()
        if not data or 'file_count' not in data:
            return jsonify({
                'error': 'Отсутствует обязательное поле file_count',
                'message': 'file_count is required'
            }), 400
        
        file_count = data['file_count']
        if not isinstance(file_count, int) or file_count <= 0:
            return jsonify({
                'error': 'file_count должен быть положительным целым числом',
                'message': 'file_count must be a positive integer'
            }), 400
        
        # Create new project
        project = Project(total_files=file_count)
        db.session.add(project)
        db.session.commit()
        
        logger.info(f"Инициализирован проект {project.id} с {file_count} файлами")
        
        return jsonify({
            'project_id': project.id,
            'message': f'Проект инициализирован. Ожидается {file_count} файлов.',
            'status': 'initialized'
        }), 201
        
    except Exception as e:
        logger.error(f"Ошибка инициализации проекта: {str(e)}")
        db.session.rollback()
        return jsonify({
            'error': 'Внутренняя ошибка сервера при инициализации проекта',
            'message': str(e)
        }), 500

@api_bp.route('/upload/<int:project_id>', methods=['POST'])
def upload_file(project_id):
    """Upload a file to an existing project"""
    try:
        # Verify project exists
        project = Project.query.get(project_id)
        if not project:
            return jsonify({
                'error': f'Проект с ID {project_id} не найден',
                'message': 'Project not found'
            }), 404
        
        # Check if project is in correct state
        if project.status not in [ProjectStatus.INITIALIZING, ProjectStatus.PROCESSING]:
            return jsonify({
                'error': f'Проект находится в состоянии {project.status.value}, загрузка файлов невозможна',
                'message': 'Project is not accepting file uploads'
            }), 400
        
        data = request.get_json()
        if not data or 'filename' not in data or 'content' not in data:
            return jsonify({
                'error': 'Отсутствуют обязательные поля filename и content',
                'message': 'filename and content are required'
            }), 400
        
        filename = data['filename']
        content = data['content']
        file_type = data.get('file_type', 'unknown')
        
        if not filename or not content:
            return jsonify({
                'error': 'filename и content не могут быть пустыми',
                'message': 'filename and content cannot be empty'
            }), 400
        
        # Check if we've already received this file
        existing_file = ProjectFile.query.filter_by(
            project_id=project_id, 
            filename=filename
        ).first()
        
        if existing_file:
            return jsonify({
                'error': f'Файл {filename} уже загружен в этот проект',
                'message': 'File already uploaded'
            }), 409
        
        # Check if we're not exceeding expected file count
        current_file_count = ProjectFile.query.filter_by(project_id=project_id).count()
        if current_file_count >= project.total_files:
            return jsonify({
                'error': f'Превышено ожидаемое количество файлов ({project.total_files})',
                'message': 'File count exceeded'
            }), 400
        
        # Create and save file
        project_file = ProjectFile(
            project_id=project_id,
            filename=filename,
            content=content,
            file_type=file_type
        )
        db.session.add(project_file)
        
        # Update project status
        if project.status == ProjectStatus.INITIALIZING:
            project.status = ProjectStatus.PROCESSING
        
        db.session.commit()
        
        # Check if all files have been uploaded
        updated_file_count = ProjectFile.query.filter_by(project_id=project_id).count()
        if updated_file_count == project.total_files:
            # Start processing in background
            logger.info(f"Все файлы загружены для проекта {project_id}, начинаем обработку")
            thread = threading.Thread(
                target=processor.process_project,
                args=(project_id,)
            )
            thread.daemon = True
            thread.start()
        
        logger.info(f"Файл {filename} загружен в проект {project_id}")
        
        return jsonify({
            'message': f'Файл {filename} успешно загружен',
            'files_uploaded': updated_file_count,
            'total_files': project.total_files,
            'status': 'uploaded'
        }), 201
        
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {str(e)}")
        db.session.rollback()
        return jsonify({
            'error': 'Внутренняя ошибка сервера при загрузке файла',
            'message': str(e)
        }), 500

@api_bp.route('/results/<int:project_id>', methods=['GET'])
def get_results(project_id):
    """Get analysis results for a project"""
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({
                'error': f'Проект с ID {project_id} не найден',
                'message': 'Project not found'
            }), 404
        
        # If processing is not complete, return 202
        if project.status == ProjectStatus.PROCESSING:
            return jsonify({
                'message': 'Анализ еще выполняется, попробуйте позже',
                'status': 'processing',
                'progress': {
                    'files_processed': project.files_processed,
                    'total_files': project.total_files,
                    'percentage': round((project.files_processed / project.total_files) * 100, 2) if project.total_files > 0 else 0
                }
            }), 202
        
        if project.status == ProjectStatus.INITIALIZING:
            return jsonify({
                'message': 'Проект еще инициализируется',
                'status': 'initializing',
                'files_uploaded': len(project.files),
                'total_files': project.total_files
            }), 202
        
        if project.status == ProjectStatus.FAILED:
            return jsonify({
                'error': 'Анализ завершился с ошибкой',
                'message': project.error_message or 'Processing failed',
                'status': 'failed'
            }), 500
        
        # Get all issues for the project
        issues = Issue.query.filter_by(project_id=project_id).all()
        
        # Group issues by type
        confirmed_issues = []
        potential_issues = []
        
        for issue in issues:
            issue_data = {
                'id': issue.id,
                'title': issue.title,
                'description': issue.description,
                'severity': issue.severity,
                'category': issue.category,
                'file_name': issue.file.filename if issue.file else None,
                'line_number': issue.line_number,
                'code_snippet': issue.code_snippet,
                'fix_suggestion': issue.fix_suggestion,
                'related_files': issue.related_files
            }
            
            if issue.issue_type == IssueType.CONFIRMED:
                confirmed_issues.append(issue_data)
            else:
                potential_issues.append(issue_data)
        
        # Get project statistics
        stats = {
            'total_files_analyzed': len(project.files),
            'total_issues_found': len(issues),
            'confirmed_issues': len(confirmed_issues),
            'potential_issues': len(potential_issues),
            'analysis_completed_at': project.updated_at.isoformat() if project.updated_at else None
        }
        
        logger.info(f"Возвращены результаты для проекта {project_id}")
        
        return jsonify({
            'project_id': project_id,
            'status': 'completed',
            'statistics': stats,
            'confirmed_issues': confirmed_issues,
            'potential_issues': potential_issues,
            'message': 'Анализ завершен успешно'
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения результатов: {str(e)}")
        return jsonify({
            'error': 'Внутренняя ошибка сервера при получении результатов',
            'message': str(e)
        }), 500

@api_bp.route('/projects', methods=['GET'])
def list_projects():
    """List all projects with their status"""
    try:
        projects = Project.query.order_by(Project.created_at.desc()).all()
        
        project_list = []
        for project in projects:
            project_data = {
                'id': project.id,
                'total_files': project.total_files,
                'files_processed': project.files_processed,
                'status': project.status.value,
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat() if project.updated_at else None,
                'error_message': project.error_message
            }
            project_list.append(project_data)
        
        return jsonify({
            'projects': project_list,
            'total_count': len(project_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка получения списка проектов: {str(e)}")
        return jsonify({
            'error': 'Внутренняя ошибка сервера при получении списка проектов',
            'message': str(e)
        }), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Сервис анализа производительности работает'
    }), 200
