#!/usr/bin/env python3
"""
Tests for the Docker Volume File MCP Server.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import asyncio

# Import the server components
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from file_mcp_server import DockerVolumeFileHandler, app

class TestDockerVolumeFileHandler(unittest.TestCase):
    """Test cases for DockerVolumeFileHandler."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.handler = DockerVolumeFileHandler(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validate_path_security(self):
        """Test that path validation prevents directory traversal."""
        with self.assertRaises(ValueError):
            self.handler._validate_path("../../../etc/passwd")
        
        with self.assertRaises(ValueError):
            self.handler._validate_path("/etc/passwd")
    
    def test_create_directory(self):
        """Test directory creation."""
        test_path = "test_dir"
        result = self.handler.create_directory(test_path)
        self.assertTrue(result)
        self.assertTrue((Path(self.temp_dir) / test_path).exists())
        self.assertTrue((Path(self.temp_dir) / test_path).is_dir())
    
    def test_write_and_read_file(self):
        """Test file writing and reading."""
        test_path = "test_file.txt"
        test_content = "Hello, Docker Volume!"
        
        # Write file
        result = self.handler.write_file(test_path, test_content)
        self.assertTrue(result)
        
        # Read file
        content = self.handler.read_file(test_path)
        self.assertEqual(content, test_content)
    
    def test_binary_file_handling(self):
        """Test binary file handling."""
        test_path = "test_binary.bin"
        test_binary_data = b'\x00\x01\x02\x03\xff\xfe\xfd'
        
        # Write binary file
        result = self.handler.write_file_binary(test_path, test_binary_data)
        self.assertTrue(result)
        
        # Read binary file
        content = self.handler.read_file_binary(test_path)
        self.assertEqual(content, test_binary_data)
        
        # Read as text (should return base64)
        text_content = self.handler.read_file(test_path)
        import base64
        decoded_content = base64.b64decode(text_content)
        self.assertEqual(decoded_content, test_binary_data)
    
    def test_base64_encoded_write(self):
        """Test writing base64 encoded content."""
        test_path = "test_base64.bin"
        test_binary_data = b'\x00\x01\x02\x03'
        import base64
        base64_content = base64.b64encode(test_binary_data).decode('ascii')
        
        # Write base64 content
        result = self.handler.write_file(test_path, base64_content)
        self.assertTrue(result)
        
        # Read as binary
        content = self.handler.read_file_binary(test_path)
        self.assertEqual(content, test_binary_data)
    
    def test_list_files(self):
        """Test file listing functionality."""
        # Create test files and directories
        self.handler.create_directory("test_dir")
        self.handler.write_file("test_file.txt", "content")
        self.handler.write_file("test_dir/nested_file.txt", "nested content")
        
        # List root directory
        files = self.handler.list_files("")
        self.assertEqual(len(files), 2)  # test_dir and test_file.txt
        
        # Check that we have both file and directory
        file_types = [f["type"] for f in files]
        self.assertIn("file", file_types)
        self.assertIn("directory", file_types)
        
        # List subdirectory
        nested_files = self.handler.list_files("test_dir")
        self.assertEqual(len(nested_files), 1)
        self.assertEqual(nested_files[0]["name"], "nested_file.txt")
    
    def test_get_file_info(self):
        """Test getting file information."""
        test_path = "info_test.txt"
        test_content = "Test content for info"
        
        self.handler.write_file(test_path, test_content)
        info = self.handler.get_file_info(test_path)
        
        self.assertEqual(info["name"], "info_test.txt")
        self.assertEqual(info["type"], "file")
        self.assertGreater(info["size"], 0)
        self.assertIn("permissions", info)
        self.assertIn("modified", info)
        self.assertIn("mime_type", info)
        self.assertIn("is_binary", info)
        self.assertFalse(info["is_binary"])  # Text file should not be binary
    
    def test_get_binary_file_info(self):
        """Test getting binary file information."""
        test_path = "info_test.bin"
        test_binary_data = b'\x00\x01\x02\x03'
        
        self.handler.write_file_binary(test_path, test_binary_data)
        info = self.handler.get_file_info(test_path)
        
        self.assertEqual(info["name"], "info_test.bin")
        self.assertEqual(info["type"], "file")
        self.assertGreater(info["size"], 0)
        self.assertIn("permissions", info)
        self.assertIn("modified", info)
        self.assertIn("mime_type", info)
        self.assertIn("is_binary", info)
        self.assertTrue(info["is_binary"])  # Binary file should be marked as binary
    
    def test_delete_file(self):
        """Test file deletion."""
        test_path = "delete_test.txt"
        self.handler.write_file(test_path, "content")
        
        # Verify file exists
        self.assertTrue((Path(self.temp_dir) / test_path).exists())
        
        # Delete file
        result = self.handler.delete_file(test_path)
        self.assertTrue(result)
        
        # Verify file is deleted
        self.assertFalse((Path(self.temp_dir) / test_path).exists())
    
    def test_delete_directory(self):
        """Test directory deletion."""
        test_dir = "delete_dir"
        self.handler.create_directory(test_dir)
        self.handler.write_file(f"{test_dir}/file.txt", "content")
        
        # Verify directory exists
        self.assertTrue((Path(self.temp_dir) / test_dir).exists())
        
        # Delete directory
        result = self.handler.delete_file(test_dir)
        self.assertTrue(result)
        
        # Verify directory is deleted
        self.assertFalse((Path(self.temp_dir) / test_dir).exists())
    
    def test_file_not_found_errors(self):
        """Test error handling for non-existent files."""
        with self.assertRaises(FileNotFoundError):
            self.handler.read_file("nonexistent.txt")
        
        with self.assertRaises(FileNotFoundError):
            self.handler.get_file_info("nonexistent.txt")
        
        with self.assertRaises(FileNotFoundError):
            self.handler.delete_file("nonexistent.txt")

class TestMCPServer(unittest.TestCase):
    """Test cases for MCP server functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        # Patch the file handler to use temp directory
        self.handler_patcher = patch('file_mcp_server.file_handler')
        self.mock_handler = self.handler_patcher.start()
        self.mock_handler.base_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        self.handler_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_list_tools(self):
        """Test that list_tools returns expected tools."""
        tools = await app.list_tools()
        
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "list_files", "read_file", "write_file", 
            "delete_file", "create_directory", "get_file_info"
        ]
        
        for expected_tool in expected_tools:
            self.assertIn(expected_tool, tool_names)
    
    async def test_call_tool_list_files(self):
        """Test list_files tool call."""
        mock_files = [
            {"name": "test.txt", "type": "file", "size": 10},
            {"name": "dir", "type": "directory", "size": 0}
        ]
        self.mock_handler.list_files.return_value = mock_files
        
        result = await app.call_tool("list_files", {"path": ""})
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        returned_data = json.loads(result[0].text)
        self.assertEqual(len(returned_data), 2)
    
    async def test_call_tool_read_file(self):
        """Test read_file tool call."""
        test_content = "Test file content"
        self.mock_handler.read_file.return_value = test_content
        
        result = await app.call_tool("read_file", {"path": "test.txt"})
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertEqual(result[0].text, test_content)
    
    async def test_call_tool_write_file(self):
        """Test write_file tool call."""
        self.mock_handler.write_file.return_value = True
        
        result = await app.call_tool("write_file", {
            "path": "test.txt", 
            "content": "test content"
        })
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("successfully", result[0].text)
    
    async def test_call_tool_error_handling(self):
        """Test error handling in tool calls."""
        self.mock_handler.read_file.side_effect = FileNotFoundError("File not found")
        
        result = await app.call_tool("read_file", {"path": "nonexistent.txt"})
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("Error:", result[0].text)
    
    async def test_call_tool_unknown_tool(self):
        """Test handling of unknown tool calls."""
        result = await app.call_tool("unknown_tool", {})
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].type, "text")
        self.assertIn("Unknown tool", result[0].text)

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete MCP server."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.handler = DockerVolumeFileHandler(self.temp_dir)
    
    def tearDown(self):
        """Clean up integration test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_workflow(self):
        """Test complete workflow: create dir, write file, read file, list files, delete."""
        # Create directory
        self.handler.create_directory("workflow_test")
        
        # Write file
        content = "Integration test content"
        self.handler.write_file("workflow_test/test.txt", content)
        
        # Read file
        read_content = self.handler.read_file("workflow_test/test.txt")
        self.assertEqual(read_content, content)
        
        # List files
        files = self.handler.list_files("workflow_test")
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["name"], "test.txt")
        
        # Get file info
        info = self.handler.get_file_info("workflow_test/test.txt")
        self.assertEqual(info["name"], "test.txt")
        self.assertEqual(info["type"], "file")
        
        # Delete file
        self.handler.delete_file("workflow_test/test.txt")
        
        # Verify deletion
        files_after = self.handler.list_files("workflow_test")
        self.assertEqual(len(files_after), 0)
        
        # Delete directory
        self.handler.delete_file("workflow_test")
        
        # Verify directory deletion
        root_files = self.handler.list_files("")
        workflow_dirs = [f for f in root_files if f["name"] == "workflow_test"]
        self.assertEqual(len(workflow_dirs), 0)

if __name__ == "__main__":
    # Run async tests
    async def run_async_tests():
        test_suite = unittest.TestLoader().loadTestsFromTestCase(TestMCPServer)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run async test methods
        for test_case in test_suite:
            if hasattr(test_case, 'setUp'):
                test_case.setUp()
            
            for test_method in test_case:
                if asyncio.iscoroutinefunction(test_method):
                    await test_method()
                else:
                    test_method()
            
            if hasattr(test_case, 'tearDown'):
                test_case.tearDown()
    
    # Run synchronous tests
    unittest.main(verbosity=2)
