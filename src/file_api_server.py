#!/usr/bin/env python3
"""
FastAPI REST API server for handling files in Docker volumes.
Provides RESTful endpoints for file operations.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Path as FastAPIPath, File, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
import uvicorn
import base64

# Import the file handler from the MCP server
from file_mcp_server import DockerVolumeFileHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Docker Volume File API",
    description="RESTful API for handling files in Docker volumes",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize the file handler
file_handler = DockerVolumeFileHandler()

# Pydantic models for request/response
class FileWriteRequest(BaseModel):
    content: str = Field(..., description="Content to write to the file")

class FileInfo(BaseModel):
    name: str
    path: str
    type: str
    size: int
    modified: float
    permissions: str
    created: Optional[float] = None
    owner: Optional[int] = None
    group: Optional[int] = None
    mime_type: Optional[str] = None
    is_binary: Optional[bool] = None

class FileListResponse(BaseModel):
    files: List[FileInfo]
    path: str
    count: int

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.now().isoformat()
        ).dict()
    )

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Docker Volume File API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/files", response_model=FileListResponse)
async def list_files(
    path: str = Query("", description="Path within Docker volumes (empty for root)")
):
    """List files and directories in the specified path."""
    try:
        files_data = file_handler.list_files(path)
        
        # Convert to FileInfo objects
        files = []
        for file_data in files_data:
            files.append(FileInfo(
                name=file_data["name"],
                path=file_data["path"],
                type=file_data["type"],
                size=file_data["size"],
                modified=file_data["modified"],
                permissions=file_data["permissions"],
                created=file_data.get("created"),
                owner=file_data.get("owner"),
                group=file_data.get("group"),
                mime_type=file_data.get("mime_type"),
                is_binary=file_data.get("is_binary")
            ))
        
        return FileListResponse(
            files=files,
            path=path,
            count=len(files)
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing files in {path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list files")

@app.get("/files/{file_path:path}", response_model=Dict[str, Any])
async def read_file(
    file_path: str = FastAPIPath(..., description="Path to the file to read")
):
    """Read contents of a file (text or base64 encoded binary)."""
    try:
        content = file_handler.read_file(file_path)
        
        # Check if content is base64 encoded binary
        is_binary = False
        try:
            base64.b64decode(content)
            is_binary = True
        except Exception:
            pass
        
        return {
            "path": file_path,
            "content": content,
            "size": len(content),
            "is_binary": is_binary,
            "timestamp": datetime.now().isoformat()
        }
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read file")

@app.get("/files/{file_path:path}/binary")
async def read_file_binary(
    file_path: str = FastAPIPath(..., description="Path to the binary file to read")
):
    """Read contents of a binary file."""
    try:
        binary_data = file_handler.read_file_binary(file_path)
        return Response(
            content=binary_data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={Path(file_path).name}"}
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reading binary file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read binary file")

@app.post("/files/{file_path:path}/binary")
async def write_file_binary(
    file_path: str = FastAPIPath(..., description="Path where to write the binary file"),
    file: UploadFile = File(...)
):
    """Write binary content to a file."""
    try:
        binary_content = await file.read()
        success = file_handler.write_file_binary(file_path, binary_content)
        if success:
            return {
                "message": f"Binary file written successfully: {file_path}",
                "path": file_path,
                "size": len(binary_content),
                "filename": file.filename,
                "content_type": file.content_type,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to write binary file: {file_path}")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error writing binary file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to write binary file")

@app.post("/files/{file_path:path}", response_model=Dict[str, str])
async def write_file(
    file_path: str = FastAPIPath(..., description="Path where to write the file"),
    request: FileWriteRequest = ...
):
    """Write content to a file."""
    try:
        success = file_handler.write_file(file_path, request.content)
        if success:
            return {
                "message": f"File written successfully: {file_path}",
                "path": file_path,
                "size": len(request.content),
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to write file: {file_path}")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to write file")

@app.delete("/files/{file_path:path}", response_model=Dict[str, str])
async def delete_file(
    file_path: str = FastAPIPath(..., description="Path to the file or directory to delete")
):
    """Delete a file or directory."""
    try:
        success = file_handler.delete_file(file_path)
        if success:
            return {
                "message": f"File/directory deleted successfully: {file_path}",
                "path": file_path,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete: {file_path}")
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")

@app.post("/directories/{dir_path:path}", response_model=Dict[str, str])
async def create_directory(
    dir_path: str = FastAPIPath(..., description="Path where to create the directory")
):
    """Create a directory."""
    try:
        success = file_handler.create_directory(dir_path)
        if success:
            return {
                "message": f"Directory created successfully: {dir_path}",
                "path": dir_path,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to create directory: {dir_path}")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating directory {dir_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create directory")

@app.get("/files/{file_path:path}/info", response_model=FileInfo)
async def get_file_info(
    file_path: str = FastAPIPath(..., description="Path to the file or directory")
):
    """Get detailed information about a file or directory."""
    try:
        info_data = file_handler.get_file_info(file_path)
        return FileInfo(
            name=info_data["name"],
            path=info_data["path"],
            type=info_data["type"],
            size=info_data["size"],
            modified=info_data["modified"],
            permissions=info_data["permissions"],
            created=info_data.get("created"),
            owner=info_data.get("owner"),
            group=info_data.get("group"),
            mime_type=info_data.get("mime_type"),
            is_binary=info_data.get("is_binary")
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {file_path} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file info")

@app.get("/stats", response_model=Dict[str, Any])
async def get_stats():
    """Get statistics about the Docker volumes."""
    try:
        # Get root directory listing
        files = file_handler.list_files("")
        
        total_files = len([f for f in files if f["type"] == "file"])
        total_dirs = len([f for f in files if f["type"] == "directory"])
        total_size = sum(f["size"] for f in files if f["type"] == "file")
        
        return {
            "total_files": total_files,
            "total_directories": total_dirs,
            "total_size_bytes": total_size,
            "base_path": str(file_handler.base_path),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

if __name__ == "__main__":
    uvicorn.run(
        "file_api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
