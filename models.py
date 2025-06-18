from app import db
from datetime import datetime
from sqlalchemy import Enum
import enum

class ProjectStatus(enum.Enum):
    INITIALIZING = "initializing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class IssueType(enum.Enum):
    CONFIRMED = "confirmed"
    POTENTIAL = "potential"

class Project(db.Model):
    """Represents a performance testing project being analyzed"""
    id = db.Column(db.Integer, primary_key=True)
    total_files = db.Column(db.Integer, nullable=False)
    files_processed = db.Column(db.Integer, default=0)
    status = db.Column(Enum(ProjectStatus), default=ProjectStatus.INITIALIZING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = db.Column(db.Text)
    
    # Relationships
    files = db.relationship('ProjectFile', backref='project', lazy=True, cascade='all, delete-orphan')
    issues = db.relationship('Issue', backref='project', lazy=True, cascade='all, delete-orphan')

class ProjectFile(db.Model):
    """Represents a file in the performance testing project"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_type = db.Column(db.String(50))  # e.g., 'python', 'jmx', 'yaml', etc.
    processed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    issues = db.relationship('Issue', backref='file', lazy=True)

class Issue(db.Model):
    """Represents a performance issue found in the code"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('project_file.id'), nullable=True)
    issue_type = db.Column(Enum(IssueType), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    line_number = db.Column(db.Integer)
    code_snippet = db.Column(db.Text)
    severity = db.Column(db.String(20))  # 'low', 'medium', 'high', 'critical'
    category = db.Column(db.String(100))  # e.g., 'authentication', 'database', 'memory'
    fix_suggestion = db.Column(db.Text)
    related_files = db.Column(db.JSON)  # List of related file IDs for cross-file issues
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CorrelationRule(db.Model):
    """Represents rules for correlating issues across files"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    pattern_1 = db.Column(db.String(255), nullable=False)  # Pattern to look for in first file
    pattern_2 = db.Column(db.String(255), nullable=False)  # Pattern to look for in second file
    category = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
