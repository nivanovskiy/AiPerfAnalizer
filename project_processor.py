import logging
from app import db
from models import Project, ProjectFile, Issue, ProjectStatus, IssueType
from ai_analyzer import PerformanceAnalyzer
from utils import determine_file_type
import json

logger = logging.getLogger(__name__)

class ProjectProcessor:
    """Processes projects by analyzing files and correlating issues"""
    
    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
    
    def process_project(self, project_id):
        """
        Main processing function that analyzes all files and correlates issues
        """
        try:
            logger.info(f"Начинаем обработку проекта {project_id}")
            
            with db.session.begin():
                project = Project.query.get(project_id)
                if not project:
                    logger.error(f"Проект {project_id} не найден")
                    return
                
                project.status = ProjectStatus.PROCESSING
                project.files_processed = 0
                db.session.commit()
            
            # Get all files for the project
            files = ProjectFile.query.filter_by(project_id=project_id).all()
            
            if not files:
                logger.warning(f"Нет файлов для обработки в проекте {project_id}")
                self._mark_project_completed(project_id)
                return
            
            # Step 1: Analyze each file individually
            potential_issues = []
            for file_obj in files:
                try:
                    file_issues = self._analyze_file(file_obj)
                    potential_issues.extend(file_issues)
                    
                    # Update progress
                    with db.session.begin():
                        project = Project.query.get(project_id)
                        project.files_processed += 1
                        db.session.commit()
                        
                    logger.info(f"Обработан файл {file_obj.filename}, найдено {len(file_issues)} потенциальных проблем")
                    
                except Exception as e:
                    logger.error(f"Ошибка анализа файла {file_obj.filename}: {str(e)}")
                    continue
            
            # Step 2: Correlate issues across files
            confirmed_issues = self._correlate_issues(project_id, potential_issues)
            
            # Step 3: Generate fix suggestions for all issues
            self._generate_fix_suggestions(project_id)
            
            # Step 4: Mark project as completed
            self._mark_project_completed(project_id)
            
            logger.info(f"Обработка проекта {project_id} завершена. "
                       f"Найдено {len(potential_issues)} потенциальных и {len(confirmed_issues)} подтвержденных проблем")
            
        except Exception as e:
            logger.error(f"Критическая ошибка обработки проекта {project_id}: {str(e)}")
            self._mark_project_failed(project_id, str(e))
    
    def _analyze_file(self, file_obj):
        """Analyze a single file and create Issue records"""
        try:
            file_type = determine_file_type(file_obj.filename, file_obj.content)
            
            # Get AI analysis
            analysis_result = self.analyzer.analyze_file_for_issues(
                file_obj.filename, 
                file_obj.content, 
                file_type
            )
            
            if 'error' in analysis_result:
                logger.warning(f"AI анализ файла {file_obj.filename} завершился с ошибкой: {analysis_result['error']}")
                return []
            
            issues = analysis_result.get('issues', [])
            created_issues = []
            
            for issue_data in issues:
                try:
                    # Create Issue record
                    issue = Issue(
                        project_id=file_obj.project_id,
                        file_id=file_obj.id,
                        issue_type=IssueType.POTENTIAL,  # All start as potential
                        title=issue_data.get('title', 'Неизвестная проблема'),
                        description=issue_data.get('description', 'Описание отсутствует'),
                        line_number=issue_data.get('line_number'),
                        code_snippet=issue_data.get('code_snippet', ''),
                        severity=issue_data.get('severity', 'medium'),
                        category=issue_data.get('category', 'other'),
                        related_files=json.dumps({
                            'potential_correlation': issue_data.get('potential_correlation', []),
                            'confidence': issue_data.get('confidence', 0.5)
                        })
                    )
                    
                    db.session.add(issue)
                    created_issues.append(issue)
                    
                except Exception as e:
                    logger.error(f"Ошибка создания записи проблемы: {str(e)}")
                    continue
            
            db.session.commit()
            
            # Mark file as processed
            file_obj.processed = True
            db.session.commit()
            
            return created_issues
            
        except Exception as e:
            logger.error(f"Ошибка анализа файла {file_obj.filename}: {str(e)}")
            db.session.rollback()
            return []
    
    def _correlate_issues(self, project_id, potential_issues):
        """Correlate issues across files to identify confirmed problems"""
        confirmed_issues = []
        
        try:
            # Get all potential issues for the project
            issues = Issue.query.filter_by(
                project_id=project_id, 
                issue_type=IssueType.POTENTIAL
            ).all()
            
            # Compare each issue with others to find correlations
            for i, issue1 in enumerate(issues):
                for issue2 in issues[i+1:]:
                    if issue1.file_id == issue2.file_id:
                        continue  # Skip same file comparisons
                    
                    # Check if issues might be related based on category and keywords
                    if self._should_check_correlation(issue1, issue2):
                        correlation = self._check_issue_correlation(issue1, issue2)
                        
                        if correlation and correlation.get('is_correlated', False):
                            # Create confirmed issue from correlated potential issues
                            confirmed_issue = self._create_confirmed_issue(
                                issue1, issue2, correlation, project_id
                            )
                            if confirmed_issue:
                                confirmed_issues.append(confirmed_issue)
                                
                                # Mark original issues as part of confirmed issue
                                issue1.related_files = json.dumps({
                                    'confirmed_issue_id': confirmed_issue.id,
                                    'correlation_type': 'source'
                                })
                                issue2.related_files = json.dumps({
                                    'confirmed_issue_id': confirmed_issue.id,
                                    'correlation_type': 'source'
                                })
            
            db.session.commit()
            logger.info(f"Создано {len(confirmed_issues)} подтвержденных проблем из корреляции")
            
        except Exception as e:
            logger.error(f"Ошибка корреляции проблем: {str(e)}")
            db.session.rollback()
        
        return confirmed_issues
    
    def _should_check_correlation(self, issue1, issue2):
        """Determine if two issues should be checked for correlation"""
        # Check if they have similar categories
        if issue1.category == issue2.category:
            return True
        
        # Check for related categories
        related_categories = {
            'authentication': ['database', 'api', 'network'],
            'database': ['authentication', 'memory', 'io'],
            'api': ['authentication', 'network', 'timeout'],
            'memory': ['database', 'io', 'algorithm'],
            'io': ['database', 'memory', 'network'],
            'network': ['api', 'io', 'timeout']
        }
        
        category1_related = related_categories.get(issue1.category, [])
        if issue2.category in category1_related:
            return True
        
        # Check keywords in related_files
        try:
            issue1_data = json.loads(issue1.related_files or '{}')
            issue2_data = json.loads(issue2.related_files or '{}')
            
            keywords1 = set(issue1_data.get('potential_correlation', []))
            keywords2 = set(issue2_data.get('potential_correlation', []))
            
            # If they share keywords, check correlation
            if keywords1 & keywords2:
                return True
                
        except (json.JSONDecodeError, TypeError):
            pass
        
        return False
    
    def _check_issue_correlation(self, issue1, issue2):
        """Use AI to check if two issues are correlated"""
        try:
            file1_content = issue1.file.content if issue1.file else ""
            file2_content = issue2.file.content if issue2.file else ""
            
            issue1_data = {
                'title': issue1.title,
                'description': issue1.description,
                'category': issue1.category,
                'potential_correlation': json.loads(issue1.related_files or '{}').get('potential_correlation', [])
            }
            
            issue2_data = {
                'title': issue2.title,
                'description': issue2.description,
                'category': issue2.category,
                'potential_correlation': json.loads(issue2.related_files or '{}').get('potential_correlation', [])
            }
            
            return self.analyzer.correlate_issues(
                issue1_data, issue2_data, file1_content, file2_content
            )
            
        except Exception as e:
            logger.error(f"Ошибка проверки корреляции между проблемами {issue1.id} и {issue2.id}: {str(e)}")
            return None
    
    def _create_confirmed_issue(self, issue1, issue2, correlation, project_id):
        """Create a confirmed issue from two correlated potential issues"""
        try:
            confirmed_issue = Issue(
                project_id=project_id,
                file_id=None,  # Cross-file issue
                issue_type=IssueType.CONFIRMED,
                title=correlation.get('combined_description', f"Корреляция: {issue1.title} + {issue2.title}"),
                description=f"""
Подтвержденная проблема, найденная в нескольких файлах:

Файл 1: {issue1.file.filename if issue1.file else 'Неизвестно'}
Проблема: {issue1.title}
{issue1.description}

Файл 2: {issue2.file.filename if issue2.file else 'Неизвестно'}
Проблема: {issue2.title}
{issue2.description}

Объяснение корреляции: {correlation.get('correlation_explanation', 'Автоматически обнаружена связь')}
                """.strip(),
                severity=correlation.get('combined_severity', 'medium'),
                category=issue1.category,  # Use primary issue category
                related_files=json.dumps({
                    'correlated_issues': [issue1.id, issue2.id],
                    'confidence': correlation.get('correlation_confidence', 0.8),
                    'files': [
                        issue1.file.filename if issue1.file else None,
                        issue2.file.filename if issue2.file else None
                    ]
                })
            )
            
            db.session.add(confirmed_issue)
            db.session.flush()  # Get the ID
            
            return confirmed_issue
            
        except Exception as e:
            logger.error(f"Ошибка создания подтвержденной проблемы: {str(e)}")
            return None
    
    def _generate_fix_suggestions(self, project_id):
        """Generate fix suggestions for all issues in the project"""
        try:
            issues = Issue.query.filter_by(project_id=project_id).all()
            
            for issue in issues:
                if issue.fix_suggestion:
                    continue  # Already has a suggestion
                
                try:
                    suggestion = self.analyzer.generate_fix_suggestion(
                        issue.title,
                        issue.description,
                        issue.code_snippet or "",
                        issue.category
                    )
                    
                    # Format the suggestion as readable text
                    formatted_suggestion = self._format_fix_suggestion(suggestion)
                    issue.fix_suggestion = formatted_suggestion
                    
                except Exception as e:
                    logger.error(f"Ошибка создания предложения для проблемы {issue.id}: {str(e)}")
                    issue.fix_suggestion = f"Не удалось создать автоматическое предложение по исправлению: {str(e)}"
            
            db.session.commit()
            logger.info(f"Созданы предложения по исправлению для проекта {project_id}")
            
        except Exception as e:
            logger.error(f"Ошибка создания предложений по исправлению: {str(e)}")
            db.session.rollback()
    
    def _format_fix_suggestion(self, suggestion):
        """Format AI fix suggestion into readable text"""
        try:
            formatted = "ПРЕДЛОЖЕНИЕ ПО ИСПРАВЛЕНИЮ:\n\n"
            
            # Steps
            if suggestion.get('fix_steps'):
                formatted += "Шаги для исправления:\n"
                for i, step in enumerate(suggestion['fix_steps'], 1):
                    formatted += f"{i}. {step}\n"
                formatted += "\n"
            
            # Fixed code
            if suggestion.get('fixed_code'):
                formatted += f"Пример исправленного кода:\n```\n{suggestion['fixed_code']}\n```\n\n"
            
            # Explanation
            if suggestion.get('explanation'):
                formatted += f"Объяснение улучшений:\n{suggestion['explanation']}\n\n"
            
            # Estimated improvement
            if suggestion.get('estimated_improvement'):
                formatted += f"Ожидаемое улучшение:\n{suggestion['estimated_improvement']}\n\n"
            
            # Alternatives
            if suggestion.get('alternatives'):
                formatted += "Альтернативные решения:\n"
                for alt in suggestion['alternatives']:
                    formatted += f"• {alt}\n"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Ошибка форматирования предложения: {str(e)}")
            return json.dumps(suggestion, ensure_ascii=False, indent=2)
    
    def _mark_project_completed(self, project_id):
        """Mark project as completed"""
        try:
            with db.session.begin():
                project = Project.query.get(project_id)
                if project:
                    project.status = ProjectStatus.COMPLETED
                    db.session.commit()
                    logger.info(f"Проект {project_id} отмечен как завершенный")
        except Exception as e:
            logger.error(f"Ошибка завершения проекта {project_id}: {str(e)}")
    
    def _mark_project_failed(self, project_id, error_message):
        """Mark project as failed"""
        try:
            with db.session.begin():
                project = Project.query.get(project_id)
                if project:
                    project.status = ProjectStatus.FAILED
                    project.error_message = error_message
                    db.session.commit()
                    logger.error(f"Проект {project_id} отмечен как неудачный: {error_message}")
        except Exception as e:
            logger.error(f"Ошибка пометки проекта {project_id} как неудачного: {str(e)}")
