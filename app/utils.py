"""
Utility functions for the application.
"""
import os
import re
import unicodedata


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    r"""
    Sanitizes a filename to prevent path traversal attacks and remove dangerous characters.
    
    This function:
    1. Removes path traversal sequences (../, ../../, etc.)
    2. Removes absolute path indicators (/ at start, C:\ on Windows, etc.)
    3. Removes or replaces dangerous characters
    4. Normalizes unicode characters
    5. Ensures the filename is not empty after sanitization
    6. Truncates to max_length while preserving file extension
    
    Args:
        filename: The original filename to sanitize
        max_length: Maximum length for the sanitized filename (default: 255)
        
    Returns:
        A sanitized filename safe for storage and display
        
    Examples:
        >>> sanitize_filename("../../../etc/passwd")
        'passwd'
        >>> sanitize_filename("file<>name.pdf")
        'file_name.pdf'
        >>> sanitize_filename("normal_file.txt")
        'normal_file.txt'
    """
    if not filename:
        return "unnamed_file"
    
    # Normalize unicode characters (e.g., convert accented characters)
    filename = unicodedata.normalize('NFKD', filename)
    
    # Remove any path components - split by both / and \ and take only the last part
    filename = os.path.basename(filename.replace('\\', '/'))
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Remove or replace dangerous characters
    # Allow: alphanumeric, underscore, hyphen, period
    # Replace other characters (including spaces) with underscore
    filename = re.sub(r'[^\w.\-]', '_', filename)
    
    # Remove leading/trailing underscores and dots (which can be problematic)
    filename = filename.strip('._')
    
    # Replace multiple consecutive underscores with single underscore
    filename = re.sub(r'_+', '_', filename)
    
    # Handle reserved names on Windows (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    name_without_ext = os.path.splitext(filename)[0]
    if name_without_ext.upper() in reserved_names:
        filename = f"file_{filename}"
    
    # If filename is empty after sanitization, use default
    if not filename or filename == '.':
        return "unnamed_file"
    
    # Truncate if too long while preserving extension
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        # Reserve space for extension plus a dot
        max_name_length = max_length - len(ext)
        if max_name_length > 0:
            filename = name[:max_name_length] + ext
        else:
            # Extension itself is too long, truncate the whole thing
            filename = filename[:max_length]
    
    return filename
