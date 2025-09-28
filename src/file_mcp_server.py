#!/usr/bin/env python3
"""
MCP Server for handling files in Docker volumes.
Provides file operations like read, write, list, delete for Docker volume paths.
"""

import json
import os
import shutil
import stat
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio
import logging

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
    ServerCapabilities
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MCP server
app = Server("file-mcp-server")

class DockerVolumeFileHandler:
    """Handler for file operations on Docker volumes."""
    
    def __init__(self, base_path: str = "/var/lib/docker/volumes"):
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            logger.warning(f"Base path {base_path} does not exist, creating it")
            self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _validate_path(self, path: str) -> Path:
        """Validate and normalize a path within Docker volumes."""
        full_path = self.base_path / path.lstrip('/')
        
        # Security check: ensure path is within base_path
        try:
            full_path.resolve().relative_to(self.base_path.resolve())
        except ValueError:
            raise ValueError(f"Path {path} is outside allowed directory")
        
        return full_path
    
    def list_files(self, path: str = "") -> List[Dict[str, Any]]:
        """List files and directories in the specified path."""
        try:
            target_path = self._validate_path(path)
            
            if not target_path.exists():
                return []
            
            items = []
            for item in target_path.iterdir():
                stat_info = item.stat()
                items.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.base_path)),
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat_info.st_size,
                    "modified": stat_info.st_mtime,
                    "permissions": oct(stat_info.st_mode)[-3:]
                })
            
            return sorted(items, key=lambda x: (x["type"], x["name"]))
        except Exception as e:
            logger.error(f"Error listing files in {path}: {e}")
            raise
    
    def read_file(self, path: str, encoding: str = 'utf-8') -> str:
        """Read contents of a file."""
        try:
            target_path = self._validate_path(path)
            
            if not target_path.exists():
                raise FileNotFoundError(f"File {path} not found")
            
            if not target_path.is_file():
                raise ValueError(f"Path {path} is not a file")
            
            # Try to read as text first
            try:
                with open(target_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                # If text decoding fails, return base64 encoded binary
                import base64
                with open(target_path, 'rb') as f:
                    binary_data = f.read()
                    return base64.b64encode(binary_data).decode('ascii')
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            raise
    
    def read_file_binary(self, path: str) -> bytes:
        """Read contents of a file as binary data."""
        try:
            target_path = self._validate_path(path)
            
            if not target_path.exists():
                raise FileNotFoundError(f"File {path} not found")
            
            if not target_path.is_file():
                raise ValueError(f"Path {path} is not a file")
            
            with open(target_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading binary file {path}: {e}")
            raise
    
    def write_file(self, path: str, content: str, encoding: str = 'utf-8') -> bool:
        """Write content to a file."""
        try:
            target_path = self._validate_path(path)
            
            # Create parent directories if they don't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if content is base64 encoded binary
            try:
                import base64
                # Try to decode as base64, if successful, write as binary
                binary_data = base64.b64decode(content)
                with open(target_path, 'wb') as f:
                    f.write(binary_data)
            except Exception:
                # If not base64, write as text
                with open(target_path, 'w', encoding=encoding) as f:
                    f.write(content)
            
            return True
        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            raise
    
    def write_file_binary(self, path: str, content: bytes) -> bool:
        """Write binary content to a file."""
        try:
            target_path = self._validate_path(path)
            
            # Create parent directories if they don't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_path, 'wb') as f:
                f.write(content)
            
            return True
        except Exception as e:
            logger.error(f"Error writing binary file {path}: {e}")
            raise
    
    def delete_file(self, path: str) -> bool:
        """Delete a file or directory."""
        try:
            target_path = self._validate_path(path)
            
            if not target_path.exists():
                raise FileNotFoundError(f"Path {path} not found")
            
            if target_path.is_file():
                target_path.unlink()
            elif target_path.is_dir():
                shutil.rmtree(target_path)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting {path}: {e}")
            raise
    
    def create_directory(self, path: str) -> bool:
        """Create a directory."""
        try:
            target_path = self._validate_path(path)
            target_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {path}: {e}")
            raise
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get detailed information about a file or directory."""
        try:
            target_path = self._validate_path(path)
            
            if not target_path.exists():
                raise FileNotFoundError(f"Path {path} not found")
            
            stat_info = target_path.stat()
            file_type = "directory" if target_path.is_dir() else "file"
            
            # Get MIME type for files
            mime_type = None
            is_binary = False
            if file_type == "file":
                mime_type, _ = mimetypes.guess_type(str(target_path))
                if mime_type:
                    is_binary = not mime_type.startswith('text/')
            
            return {
                "name": target_path.name,
                "path": str(target_path.relative_to(self.base_path)),
                "type": file_type,
                "size": stat_info.st_size,
                "modified": stat_info.st_mtime,
                "created": stat_info.st_ctime,
                "permissions": oct(stat_info.st_mode)[-3:],
                "owner": stat_info.st_uid,
                "group": stat_info.st_gid,
                "mime_type": mime_type,
                "is_binary": is_binary
            }
        except Exception as e:
            logger.error(f"Error getting file info for {path}: {e}")
            raise

# Initialize the file handler
file_handler = DockerVolumeFileHandler(
    base_path=os.getenv('DOCKER_VOLUMES_PATH', '/var/lib/docker/volumes')
)

@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="list_files",
            description="List files and directories in a Docker volume path",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path within Docker volumes (empty for root)",
                        "default": ""
                    }
                }
            }
        ),
        Tool(
            name="read_file",
            description="Read contents of a file from Docker volumes",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="write_file",
            description="Write content to a file in Docker volumes",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path where to write the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        ),
        Tool(
            name="delete_file",
            description="Delete a file or directory from Docker volumes",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file or directory to delete"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="create_directory",
            description="Create a directory in Docker volumes",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path where to create the directory"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="get_file_info",
            description="Get detailed information about a file or directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file or directory"
                    }
                },
                "required": ["path"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "list_files":
            path = arguments.get("path", "")
            files = file_handler.list_files(path)
            return [TextContent(
                type="text",
                text=json.dumps(files, indent=2, default=str)
            )]
        
        elif name == "read_file":
            path = arguments["path"]
            content = file_handler.read_file(path)
            return [TextContent(
                type="text",
                text=content
            )]
        
        elif name == "write_file":
            path = arguments["path"]
            content = arguments["content"]
            success = file_handler.write_file(path, content)
            return [TextContent(
                type="text",
                text=f"File written successfully: {path}" if success else f"Failed to write file: {path}"
            )]
        
        elif name == "delete_file":
            path = arguments["path"]
            success = file_handler.delete_file(path)
            return [TextContent(
                type="text",
                text=f"File/directory deleted successfully: {path}" if success else f"Failed to delete: {path}"
            )]
        
        elif name == "create_directory":
            path = arguments["path"]
            success = file_handler.create_directory(path)
            return [TextContent(
                type="text",
                text=f"Directory created successfully: {path}" if success else f"Failed to create directory: {path}"
            )]
        
        elif name == "get_file_info":
            path = arguments["path"]
            info = file_handler.get_file_info(path)
            return [TextContent(
                type="text",
                text=json.dumps(info, indent=2, default=str)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    
    except Exception as e:
        logger.error(f"Error handling tool {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    """Main entry point for the MCP server."""
    logger.info("Starting MCP server...")
    
    # Check if we're running in Docker without proper stdio
    import sys
    if not sys.stdin.isatty() and not sys.stdout.isatty():
        logger.info("Detected non-interactive environment, checking stdio availability...")
    
    try:
        logger.info("Setting up stdio server...")
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Stdio server established, starting MCP app...")
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="file-mcp-server",
                    server_version="1.0.0",
                    capabilities=ServerCapabilities()
                )
            )
            logger.info("MCP app.run() completed")
    except Exception as e:
        logger.error(f"MCP server error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # In Docker, we might want to keep the server running even if stdio fails
        # This allows the container to stay up for debugging
        logger.info("MCP server failed to start with stdio, keeping container alive for debugging")
        import time
        while True:
            time.sleep(60)
            logger.info("MCP server container still alive")

if __name__ == "__main__":
    asyncio.run(main())
