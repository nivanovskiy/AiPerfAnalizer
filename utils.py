import os
import re
import logging

logger = logging.getLogger(__name__)

def determine_file_type(filename, content):
    """
    Determine the type of file based on filename and content
    """
    filename_lower = filename.lower()
    
    # Check by extension
    if filename_lower.endswith('.py'):
        return 'python'
    elif filename_lower.endswith('.java'):
        return 'java'
    elif filename_lower.endswith('.js') or filename_lower.endswith('.ts'):
        return 'javascript'
    elif filename_lower.endswith('.jmx'):
        return 'jmeter'
    elif filename_lower.endswith('.yaml') or filename_lower.endswith('.yml'):
        return 'yaml'
    elif filename_lower.endswith('.json'):
        return 'json'
    elif filename_lower.endswith('.xml'):
        return 'xml'
    elif filename_lower.endswith('.sh') or filename_lower.endswith('.bash'):
        return 'shell'
    elif filename_lower.endswith('.sql'):
        return 'sql'
    elif filename_lower.endswith('.properties'):
        return 'properties'
    elif filename_lower.endswith('.conf') or filename_lower.endswith('.config'):
        return 'config'
    elif filename_lower.endswith('.dockerfile') or filename_lower == 'dockerfile':
        return 'dockerfile'
    elif filename_lower.endswith('.go'):
        return 'go'
    elif filename_lower.endswith('.rb'):
        return 'ruby'
    elif filename_lower.endswith('.php'):
        return 'php'
    elif filename_lower.endswith('.cs'):
        return 'csharp'
    elif filename_lower.endswith('.scala'):
        return 'scala'
    elif filename_lower.endswith('.kt'):
        return 'kotlin'
    
    # Check by content patterns if extension doesn't help
    if content:
        content_sample = content[:1000].lower()  # First 1000 chars
        
        # Python patterns
        if re.search(r'def\s+\w+\s*\(|import\s+\w+|from\s+\w+\s+import', content_sample):
            return 'python'
        
        # Java patterns
        if re.search(r'public\s+class|private\s+\w+|import\s+java\.|package\s+\w+', content_sample):
            return 'java'
        
        # JavaScript patterns
        if re.search(r'function\s+\w+\s*\(|var\s+\w+|let\s+\w+|const\s+\w+|console\.log', content_sample):
            return 'javascript'
        
        # JMeter XML patterns
        if '<jmeterTestPlan' in content_sample or '<TestPlan' in content_sample:
            return 'jmeter'
        
        # YAML patterns
        if re.search(r'^\s*\w+:\s*$', content_sample, re.MULTILINE):
            return 'yaml'
        
        # JSON patterns
        if content_sample.strip().startswith('{') and '"' in content_sample:
            return 'json'
        
        # XML patterns
        if content_sample.strip().startswith('<?xml') or re.search(r'<\w+[^>]*>', content_sample):
            return 'xml'
        
        # Shell script patterns
        if content_sample.startswith('#!') and ('bash' in content_sample or 'sh' in content_sample):
            return 'shell'
        
        # SQL patterns
        if re.search(r'\b(select|insert|update|delete|create|alter|drop)\b', content_sample):
            return 'sql'
    
    return 'unknown'

def extract_function_names(content, file_type):
    """
    Extract function/method names from code content
    """
    functions = []
    
    try:
        if file_type == 'python':
            # Python function pattern: def function_name(
            pattern = r'def\s+(\w+)\s*\('
            functions = re.findall(pattern, content)
        
        elif file_type == 'java':
            # Java method pattern: public/private/protected method_name(
            pattern = r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\('
            functions = re.findall(pattern, content)
        
        elif file_type == 'javascript':
            # JavaScript function patterns
            patterns = [
                r'function\s+(\w+)\s*\(',  # function name()
                r'(\w+)\s*:\s*function\s*\(',  # name: function()
                r'const\s+(\w+)\s*=\s*\(',  # const name = ()
                r'let\s+(\w+)\s*=\s*\(',  # let name = ()
                r'var\s+(\w+)\s*=\s*function'  # var name = function
            ]
            for pattern in patterns:
                functions.extend(re.findall(pattern, content))
        
        elif file_type == 'go':
            # Go function pattern: func function_name(
            pattern = r'func\s+(\w+)\s*\('
            functions = re.findall(pattern, content)
        
    except Exception as e:
        logger.error(f"Ошибка извлечения имен функций для типа {file_type}: {str(e)}")
    
    return list(set(functions))  # Remove duplicates

def extract_imports(content, file_type):
    """
    Extract import statements from code
    """
    imports = []
    
    try:
        if file_type == 'python':
            # Python import patterns
            patterns = [
                r'import\s+(\w+(?:\.\w+)*)',  # import module
                r'from\s+(\w+(?:\.\w+)*)\s+import',  # from module import
            ]
            for pattern in patterns:
                imports.extend(re.findall(pattern, content))
        
        elif file_type == 'java':
            # Java import pattern
            pattern = r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*);'
            imports = re.findall(pattern, content)
        
        elif file_type == 'javascript':
            # JavaScript import patterns
            patterns = [
                r'import.*from\s+[\'"]([^\'"]+)[\'"]',  # import ... from 'module'
                r'require\s*\(\s*[\'"]([^\'"]+)[\'"]',  # require('module')
            ]
            for pattern in patterns:
                imports.extend(re.findall(pattern, content))
        
    except Exception as e:
        logger.error(f"Ошибка извлечения импортов для типа {file_type}: {str(e)}")
    
    return list(set(imports))  # Remove duplicates

def find_potential_performance_keywords(content):
    """
    Find keywords that might indicate performance-related code
    """
    keywords = []
    content_lower = content.lower()
    
    # Performance-related keywords to look for
    performance_keywords = [
        # Authentication related
        'auth', 'login', 'authenticate', 'token', 'session', 'oauth',
        
        # Database related
        'connection', 'database', 'query', 'sql', 'cursor', 'transaction',
        'commit', 'rollback', 'pool', 'datasource',
        
        # Network/API related
        'request', 'response', 'http', 'api', 'rest', 'soap', 'client',
        'timeout', 'retry', 'circuit', 'breaker',
        
        # Concurrency related
        'thread', 'async', 'await', 'parallel', 'concurrent', 'lock',
        'synchronize', 'mutex', 'semaphore',
        
        # Memory related
        'cache', 'memory', 'heap', 'gc', 'garbage', 'collection',
        'buffer', 'pool',
        
        # I/O related
        'file', 'read', 'write', 'stream', 'io', 'disk', 'network',
        
        # Performance testing related
        'test', 'load', 'stress', 'benchmark', 'performance', 'throughput',
        'latency', 'response_time', 'rps', 'tps'
    ]
    
    for keyword in performance_keywords:
        if keyword in content_lower:
            keywords.append(keyword)
    
    return keywords

def sanitize_filename(filename):
    """
    Sanitize filename for safe storage
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace potentially dangerous characters
    safe_chars = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Limit length
    if len(safe_chars) > 255:
        name, ext = os.path.splitext(safe_chars)
        safe_chars = name[:250] + ext
    
    return safe_chars

def validate_content_size(content, max_size_mb=10):
    """
    Validate that content size is within limits
    """
    content_size = len(content.encode('utf-8'))
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if content_size > max_size_bytes:
        raise ValueError(f"Размер файла ({content_size} байт) превышает лимит {max_size_mb}MB")
    
    return True

def truncate_content_for_ai(content, max_chars=8000):
    """
    Truncate content to fit within AI token limits while preserving structure
    """
    if len(content) <= max_chars:
        return content
    
    # Try to truncate at logical boundaries
    lines = content.split('\n')
    truncated_lines = []
    current_length = 0
    
    for line in lines:
        if current_length + len(line) + 1 > max_chars:
            break
        truncated_lines.append(line)
        current_length += len(line) + 1
    
    truncated_content = '\n'.join(truncated_lines)
    
    # Add truncation notice
    if len(truncated_content) < len(content):
        truncated_content += f"\n\n[... ФАЙЛ ОБРЕЗАН, ПОКАЗАНО {len(truncated_content)} из {len(content)} символов ...]"
    
    return truncated_content
