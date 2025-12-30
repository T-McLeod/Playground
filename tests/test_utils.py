"""
Tests for utility functions in app/utils.py
"""
import unittest
import sys
import os
import importlib.util

# Load utils module directly without importing app package
utils_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'utils.py')
spec = importlib.util.spec_from_file_location("utils", utils_path)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

sanitize_filename = utils.sanitize_filename


class TestSanitizeFilename(unittest.TestCase):
    """Test cases for the sanitize_filename function"""
    
    def test_normal_filename(self):
        """Test that normal filenames pass through unchanged"""
        self.assertEqual(sanitize_filename("normal_file.txt"), "normal_file.txt")
        self.assertEqual(sanitize_filename("document.pdf"), "document.pdf")
        self.assertEqual(sanitize_filename("image_2024.png"), "image_2024.png")
    
    def test_path_traversal_protection(self):
        """Test that path traversal attempts are blocked"""
        # Relative path traversal
        result = sanitize_filename("../../../etc/passwd")
        self.assertNotIn("..", result)
        self.assertNotIn("/", result)
        
        # Another path traversal attempt
        result = sanitize_filename("../../secret.txt")
        self.assertEqual(result, "secret.txt")
    
    def test_absolute_path_removal(self):
        """Test that absolute paths are stripped to just the filename"""
        self.assertEqual(sanitize_filename("/absolute/path/file.pdf"), "file.pdf")
        self.assertEqual(sanitize_filename("C:\\Windows\\system32\\file.exe"), "file.exe")
    
    def test_special_character_removal(self):
        """Test that dangerous special characters are removed/replaced"""
        result = sanitize_filename("file<>name.pdf")
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)
        self.assertTrue(result.endswith(".pdf"))
        
        result = sanitize_filename("file|name?.pdf")
        self.assertNotIn("|", result)
        self.assertNotIn("?", result)
        self.assertTrue(result.endswith(".pdf"))
    
    def test_null_byte_removal(self):
        """Test that null bytes are removed"""
        result = sanitize_filename("test\x00file.txt")
        self.assertNotIn("\x00", result)
        self.assertEqual(result, "testfile.txt")
    
    def test_empty_filename(self):
        """Test that empty filenames get a default value"""
        self.assertEqual(sanitize_filename(""), "unnamed_file")
        self.assertEqual(sanitize_filename("..."), "unnamed_file")
    
    def test_windows_reserved_names(self):
        """Test that Windows reserved names are prefixed"""
        self.assertEqual(sanitize_filename("CON"), "file_CON")
        self.assertEqual(sanitize_filename("PRN"), "file_PRN")
        self.assertEqual(sanitize_filename("AUX"), "file_AUX")
        self.assertEqual(sanitize_filename("NUL"), "file_NUL")
        self.assertEqual(sanitize_filename("COM1"), "file_COM1")
        self.assertEqual(sanitize_filename("LPT1"), "file_LPT1")
    
    def test_spaces_replaced_with_underscores(self):
        """Test that spaces are replaced with underscores"""
        self.assertEqual(sanitize_filename("file with spaces.doc"), "file_with_spaces.doc")
    
    def test_multiple_consecutive_chars(self):
        """Test that multiple consecutive spaces/underscores collapse to one"""
        result = sanitize_filename("file   with   spaces.txt")
        self.assertNotIn("  ", result)  # No double spaces
        
    def test_length_truncation(self):
        """Test that long filenames are truncated while preserving extension"""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name, max_length=255)
        self.assertLessEqual(len(result), 255)
        self.assertTrue(result.endswith(".txt"))
    
    def test_leading_trailing_dots_removed(self):
        """Test that leading/trailing dots are removed"""
        result = sanitize_filename("..file..txt..")
        self.assertFalse(result.startswith("."))
        self.assertFalse(result.endswith("."))


if __name__ == '__main__':
    unittest.main()
