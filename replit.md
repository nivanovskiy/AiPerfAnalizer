# replit.md

## Overview

This is a Flask-based AI-powered performance analysis application that analyzes code files for performance issues. The system uses OpenAI's GPT-4o model to identify potential bottlenecks and performance problems in various programming languages and file types.

## System Architecture

The application follows a modular Flask architecture with the following key components:

- **Flask Web Application**: RESTful API server built with Flask
- **SQLAlchemy ORM**: Database abstraction layer with declarative models
- **AI Analysis Engine**: OpenAI GPT-4o integration for intelligent code analysis
- **Project Processing Pipeline**: Asynchronous file processing and analysis workflow
- **PostgreSQL Database**: Persistent storage for projects, files, and analysis results

## Key Components

### Backend Components

1. **Flask Application (`app.py`)**
   - Main application factory with database configuration
   - SQLAlchemy integration with PostgreSQL
   - Blueprint registration for API routes
   - ProxyFix middleware for deployment compatibility

2. **API Routes (`api_routes.py`)**
   - REST endpoints for project initialization and file processing
   - Handles project lifecycle management
   - Error handling and validation for incoming requests

3. **AI Analysis Engine (`ai_analyzer.py`)**
   - OpenAI GPT-4o integration for performance analysis
   - Configurable model selection (defaulting to "gpt-4o")
   - Russian language support for analysis output
   - JSON-structured response format

4. **Project Processing (`project_processor.py`)**
   - Orchestrates file analysis workflows
   - Manages project status transitions
   - Coordinates between file analysis and issue correlation

5. **Database Models (`models.py`)**
   - Project: Tracks analysis projects with status and progress
   - ProjectFile: Stores uploaded files with metadata
   - Issue: Records identified performance problems
   - Enums for ProjectStatus and IssueType

6. **Utilities (`utils.py`)**
   - File type detection based on extensions and content
   - Supports multiple programming languages and configuration formats

### Database Schema

The system uses three main entities:
- **Projects**: Track overall analysis sessions with progress and status
- **ProjectFiles**: Store individual files with content and metadata
- **Issues**: Record performance problems found during analysis

Each project can have multiple files, and files can have multiple associated issues. The system supports both confirmed and potential issue classifications.

## Data Flow

1. **Project Initialization**: Client creates a new project specifying expected file count
2. **File Upload**: Files are uploaded and associated with the project
3. **AI Analysis**: Each file is analyzed by OpenAI GPT-4o for performance issues
4. **Issue Correlation**: Results are processed and stored as structured issues
5. **Status Updates**: Project status is updated throughout the pipeline
6. **Result Retrieval**: Clients can query for analysis results and project status

## External Dependencies

### AI Services
- **OpenAI API**: GPT-4o model for intelligent code analysis
- **API Key**: Required via `OPENAI_API_KEY` environment variable

### Database
- **PostgreSQL**: Primary data storage (configured via `DATABASE_URL`)
- **Connection Pooling**: Configured with pool recycling and pre-ping

### Python Dependencies
- **Flask**: Web framework with SQLAlchemy extension
- **OpenAI**: Official Python client for OpenAI API
- **Gunicorn**: WSGI HTTP server for production deployment
- **psycopg2-binary**: PostgreSQL adapter for Python

## Deployment Strategy

### Production Deployment
- **WSGI Server**: Gunicorn with autoscaling deployment target
- **Port Configuration**: Binds to 0.0.0.0:5000 with port reuse
- **Proxy Support**: ProxyFix middleware for reverse proxy compatibility
- **Environment Variables**: Database URL and OpenAI API key configuration

### Development Environment
- **Replit Integration**: Configured for Replit's Python 3.11 environment
- **Auto-reload**: Gunicorn configured with reload for development
- **Debug Mode**: Flask debug mode enabled for local development

### Database Management
- **Automatic Schema Creation**: Tables created automatically on startup
- **Migration Support**: SQLAlchemy declarative base for schema evolution
- **Connection Management**: Pool recycling and health checks configured

## Changelog

- June 18, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.