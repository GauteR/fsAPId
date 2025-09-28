#!/usr/bin/env python3
"""
Tests for the FastAPI REST API server.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import asyncio

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import the API server
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from file_api_server import app, file_handler

class TestFastAPIServer(unittest.TestCase):
    """Test cases for FastAPI server endpoints."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.client = TestClient(app)
        
        # Patch the file handler to use temp directory
        self.handler_patcher = patch('file_api_server.file_handler')
        self.mock_handler = self.handler_patcher.start()
        self.mock_handler.base_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        self.handler_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("version", data)
        self.assertEqual(data["message"], "Docker Volume File API")
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)
    
    def test_list_files_empty_path(self):
        """Test listing files with empty path."""
        mock_files = [
            {"name": "test.txt", "path": "test.txt", "type": "file", "size": 10, "modified": 1234567890, "permissions": "644"},
            {"name": "dir", "path": "dir", "type": "directory", "size": 0, "modified": 1234567890, "permissions": "755"}
        ]
        self.mock_handler.list_files.return_value = mock_files
        
        response = self.client.get("/files")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["path"], "")
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["files"]), 2)
        self.assertEqual(data["files"][0]["name"], "test.txt")
        self.assertEqual(data["files"][1]["name"], "dir")
    
    def test_list_files_with_path(self):
        """Test listing files with specific path."""
        mock_files = [
            {"name": "nested.txt", "path": "subdir/nested.txt", "type": "file", "size": 5, "modified": 1234567890, "permissions": "644"}
        ]
        self.mock_handler.list_files.return_value = mock_files
        
        response = self.client.get("/files?path=subdir")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["path"], "subdir")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["files"][0]["name"], "nested.txt")
    
    def test_list_files_error(self):
        """Test list files with error."""
        self.mock_handler.list_files.side_effect = ValueError("Invalid path")
        
        response = self.client.get("/files?path=../../../etc")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)
    
    def test_read_file_success(self):
        """Test reading a file successfully."""
        test_content = "Hello, World!"
        self.mock_handler.read_file.return_value = test_content
        
        response = self.client.get("/files/test.txt")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["path"], "test.txt")
        self.assertEqual(data["content"], test_content)
        self.assertEqual(data["size"], len(test_content))
        self.assertIn("timestamp", data)
    
    def test_read_file_not_found(self):
        """Test reading a non-existent file."""
        self.mock_handler.read_file.side_effect = FileNotFoundError("File not found")
        
        response = self.client.get("/files/nonexistent.txt")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)
    
    def test_write_file_success(self):
        """Test writing a file successfully."""
        self.mock_handler.write_file.return_value = True
        
        request_data = {"content": "Test content"}
        response = self.client.post("/files/test.txt", json=request_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("message", data)
        self.assertIn("successfully", data["message"])
        self.assertEqual(data["path"], "test.txt")
        self.assertEqual(data["size"], len("Test content"))
    
    def test_write_file_error(self):
        """Test writing file with error."""
        self.mock_handler.write_file.side_effect = ValueError("Invalid path")
        
        request_data = {"content": "Test content"}
        response = self.client.post("/files/../../../etc/passwd", json=request_data)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)
    
    def test_delete_file_success(self):
        """Test deleting a file successfully."""
        self.mock_handler.delete_file.return_value = True
        
        response = self.client.delete("/files/test.txt")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("message", data)
        self.assertIn("successfully", data["message"])
        self.assertEqual(data["path"], "test.txt")
    
    def test_delete_file_not_found(self):
        """Test deleting a non-existent file."""
        self.mock_handler.delete_file.side_effect = FileNotFoundError("File not found")
        
        response = self.client.delete("/files/nonexistent.txt")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)
    
    def test_create_directory_success(self):
        """Test creating a directory successfully."""
        self.mock_handler.create_directory.return_value = True
        
        response = self.client.post("/directories/newdir")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("message", data)
        self.assertIn("successfully", data["message"])
        self.assertEqual(data["path"], "newdir")
    
    def test_create_directory_error(self):
        """Test creating directory with error."""
        self.mock_handler.create_directory.side_effect = ValueError("Invalid path")
        
        response = self.client.post("/directories/../../../etc")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("detail", data)
    
    def test_get_file_info_success(self):
        """Test getting file info successfully."""
        mock_info = {
            "name": "test.txt",
            "path": "test.txt",
            "type": "file",
            "size": 10,
            "modified": 1234567890,
            "permissions": "644",
            "created": 1234567890,
            "owner": 1000,
            "group": 1000
        }
        self.mock_handler.get_file_info.return_value = mock_info
        
        response = self.client.get("/files/test.txt/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["name"], "test.txt")
        self.assertEqual(data["type"], "file")
        self.assertEqual(data["size"], 10)
        self.assertEqual(data["permissions"], "644")
    
    def test_get_file_info_not_found(self):
        """Test getting info for non-existent file."""
        self.mock_handler.get_file_info.side_effect = FileNotFoundError("File not found")
        
        response = self.client.get("/files/nonexistent.txt/info")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)
    
    def test_get_stats(self):
        """Test getting statistics."""
        mock_files = [
            {"name": "file1.txt", "type": "file", "size": 100},
            {"name": "file2.txt", "type": "file", "size": 200},
            {"name": "dir1", "type": "directory", "size": 0}
        ]
        self.mock_handler.list_files.return_value = mock_files
        
        response = self.client.get("/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["total_files"], 2)
        self.assertEqual(data["total_directories"], 1)
        self.assertEqual(data["total_size_bytes"], 300)
        self.assertIn("timestamp", data)
    
    def test_get_stats_error(self):
        """Test getting stats with error."""
        self.mock_handler.list_files.side_effect = Exception("Database error")
        
        response = self.client.get("/stats")
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("detail", data)

class TestFastAPIIntegration(unittest.TestCase):
    """Integration tests for the FastAPI server."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.client = TestClient(app)
        
        # Use real file handler for integration tests
        self.original_handler = file_handler
        file_handler.base_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up integration test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        file_handler.base_path = self.original_handler.base_path
    
    def test_full_workflow(self):
        """Test complete workflow through API."""
        # Create directory
        response = self.client.post("/directories/workflow_test")
        self.assertEqual(response.status_code, 200)
        
        # Write file
        request_data = {"content": "Integration test content"}
        response = self.client.post("/files/workflow_test/test.txt", json=request_data)
        self.assertEqual(response.status_code, 200)
        
        # Read file
        response = self.client.get("/files/workflow_test/test.txt")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["content"], "Integration test content")
        
        # List files
        response = self.client.get("/files/workflow_test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["files"][0]["name"], "test.txt")
        
        # Get file info
        response = self.client.get("/files/workflow_test/test.txt/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "test.txt")
        self.assertEqual(data["type"], "file")
        
        # Delete file
        response = self.client.delete("/files/workflow_test/test.txt")
        self.assertEqual(response.status_code, 200)
        
        # Verify deletion
        response = self.client.get("/files/workflow_test")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 0)
        
        # Delete directory
        response = self.client.delete("/files/workflow_test")
        self.assertEqual(response.status_code, 200)
        
        # Verify directory deletion
        response = self.client.get("/files")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        workflow_dirs = [f for f in data["files"] if f["name"] == "workflow_test"]
        self.assertEqual(len(workflow_dirs), 0)

class TestFastAPIValidation(unittest.TestCase):
    """Test validation and edge cases."""
    
    def setUp(self):
        """Set up test environment."""
        self.client = TestClient(app)
    
    def test_invalid_json_request(self):
        """Test handling of invalid JSON in request body."""
        response = self.client.post(
            "/files/test.txt",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity
    
    def test_missing_content_field(self):
        """Test handling of missing content field."""
        request_data = {}  # Missing content field
        response = self.client.post("/files/test.txt", json=request_data)
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity
    
    def test_empty_content(self):
        """Test handling of empty content."""
        request_data = {"content": ""}
        response = self.client.post("/files/test.txt", json=request_data)
        # Should still work, just creates empty file
        self.assertEqual(response.status_code, 200)
    
    def test_large_content(self):
        """Test handling of large content."""
        large_content = "x" * 10000  # 10KB of content
        request_data = {"content": large_content}
        response = self.client.post("/files/large.txt", json=request_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["size"], 10000)
    
    def test_binary_file_read(self):
        """Test reading binary files."""
        # Mock binary data
        test_binary_data = b'\x00\x01\x02\x03\xff\xfe\xfd'
        self.mock_handler.read_file_binary.return_value = test_binary_data
        
        response = self.client.get("/files/test.bin/binary")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, test_binary_data)
        self.assertEqual(response.headers["content-type"], "application/octet-stream")
    
    def test_binary_file_write(self):
        """Test writing binary files."""
        self.mock_handler.write_file_binary.return_value = True
        
        test_binary_data = b'\x00\x01\x02\x03'
        files = {"file": ("test.bin", test_binary_data, "application/octet-stream")}
        
        response = self.client.post("/files/test.bin/binary", files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("successfully", data["message"])
        self.assertEqual(data["size"], len(test_binary_data))
    
    def test_binary_file_detection(self):
        """Test binary file detection in regular read endpoint."""
        import base64
        test_binary_data = b'\x00\x01\x02\x03'
        base64_content = base64.b64encode(test_binary_data).decode('ascii')
        
        self.mock_handler.read_file.return_value = base64_content
        
        response = self.client.get("/files/test.bin")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["content"], base64_content)
        self.assertTrue(data["is_binary"])
    
    def test_file_info_with_mime_type(self):
        """Test file info includes MIME type and binary detection."""
        mock_info = {
            "name": "test.jpg",
            "path": "test.jpg",
            "type": "file",
            "size": 1024,
            "modified": 1234567890,
            "permissions": "644",
            "created": 1234567890,
            "owner": 1000,
            "group": 1000,
            "mime_type": "image/jpeg",
            "is_binary": True
        }
        self.mock_handler.get_file_info.return_value = mock_info
        
        response = self.client.get("/files/test.jpg/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mime_type"], "image/jpeg")
        self.assertTrue(data["is_binary"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
