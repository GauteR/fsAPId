# Docker Volume File Servers

A Model Context Protocol (MCP) server and FastAPI REST API for handling file operations on Docker volumes.

## Features

- **MCP Server**: Model Context Protocol server for AI tool integration
- **REST API**: FastAPI-based RESTful API with JSON responses
- **File Operations**: List, read, write, delete files and directories
- **Binary File Support**: Handle all file types including images, videos, executables
- **File Type Detection**: Automatic MIME type detection and binary classification
- **Security**: Path validation to prevent directory traversal attacks
- **Docker Ready**: Containerized deployment support

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the MCP server:
```bash
python start_server.py mcp
```

3. Run the REST API server:
```bash
python start_server.py api
```

## MCP Server

The MCP server provides the following tools with universal file type support:

- `list_files`: List files and directories (includes MIME types and binary classification)
- `read_file`: Read contents of any file (auto-detects text vs binary, returns base64 for binary)
- `write_file`: Write content to any file (auto-detects base64 vs text content)
- `delete_file`: Delete a file or directory from Docker volumes
- `create_directory`: Create a directory in Docker volumes
- `get_file_info`: Get detailed information including MIME type and binary classification

## REST API

The FastAPI server provides the following endpoints:

### File Operations
- `GET /files` - List files and directories (with MIME types)
- `GET /files/{path}` - Read file contents (auto-detects text/binary)
- `GET /files/{path}/binary` - Read binary files as raw data
- `POST /files/{path}` - Write content to file (auto-detects base64/text)
- `POST /files/{path}/binary` - Upload binary files
- `DELETE /files/{path}` - Delete file or directory
- `GET /files/{path}/info` - Get file information (includes MIME type)

### Directory Operations
- `POST /directories/{path}` - Create directory

### System
- `GET /` - API information
- `GET /health` - Health check
- `GET /stats` - Volume statistics

### API Documentation
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Example API Usage

```bash
# List files (shows MIME types and binary classification)
curl http://localhost:8000/files

# Read text files (XML, HTML, etc.)
curl http://localhost:8000/files/document.xml

# Read binary files (EPUB, images, etc.) - returns base64 encoded
curl http://localhost:8000/files/book.epub

# Read binary files as raw data
curl http://localhost:8000/files/image.jpg/binary

# Write text content
curl -X POST http://localhost:8000/files/page.html \
  -H "Content-Type: application/json" \
  -d '{"content": "<html><body>Hello World</body></html>"}'

# Write binary content (base64 encoded)
curl -X POST http://localhost:8000/files/image.jpg \
  -H "Content-Type: application/json" \
  -d '{"content": "base64_encoded_image_data"}'

# Upload binary files
curl -X POST http://localhost:8000/files/document.pdf/binary \
  -F "file=@document.pdf"

# Create directory
curl -X POST http://localhost:8000/directories/newdir

# Get file info (includes MIME type and binary classification)
curl http://localhost:8000/files/book.epub/info

# Delete file
curl -X DELETE http://localhost:8000/files/test.txt
```

### Supported File Types

The servers handle **all file types** including:

**Documents:**
- EPUB (`.epub`) - `application/epub+zip`
- PDF (`.pdf`) - `application/pdf`
- DOCX (`.docx`) - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

**Web Files:**
- HTML (`.html`) - `text/html`
- XML (`.xml`) - `text/xml`
- CSS (`.css`) - `text/css`
- JavaScript (`.js`) - `application/javascript`

**Images:**
- JPEG (`.jpg`, `.jpeg`) - `image/jpeg`
- PNG (`.png`) - `image/png`
- GIF (`.gif`) - `image/gif`
- SVG (`.svg`) - `image/svg+xml`

**Archives:**
- ZIP (`.zip`) - `application/zip`
- TAR (`.tar`) - `application/x-tar`
- RAR (`.rar`) - `application/vnd.rar`

**And any other file type** - automatic MIME type detection

## Configuration

The servers can be configured using environment variables:

- `DOCKER_VOLUMES_PATH` - Path to the Docker volumes directory (default: `/var/lib/docker/volumes`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

For Docker Compose, copy `env.example` to `.env` and modify as needed:

```bash
cp env.example .env
# Edit .env file with your preferred settings
```

## Docker Deployment

### Using Docker Compose (Recommended)

The easiest way to run the servers is with Docker Compose, which sets up a proper Docker volume:

```bash
# Start both API and MCP servers (default)
docker-compose up -d

# Start only the API server
docker-compose up -d file-api-server

# Start only the MCP server
docker-compose up -d file-mcp-server

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

The docker-compose setup:
- ✅ **Runs both servers by default** - API server and MCP server in parallel
- ✅ **Creates a Docker volume** (`file-volume`) for persistent file storage
- ✅ **Mounts volume to `/app/data`** inside the container
- ✅ **Sets environment variables** for proper configuration
- ✅ **Includes health checks** for the API server
- ✅ **Creates local directory** `./data` for volume data

### Using Docker directly

```bash
# Build image
docker build -t file-mcp-server .

# Run API server with volume
docker run -p 8000:8000 \
  -v $(pwd)/docker-volume-data:/app/data \
  -e DOCKER_VOLUMES_PATH=/app/data \
  file-mcp-server

# Run MCP server with volume
docker run \
  -v $(pwd)/docker-volume-data:/app/data \
  -e DOCKER_VOLUMES_PATH=/app/data \
  file-mcp-server python start_server.py mcp
```

## Security

Both servers include path validation to prevent directory traversal attacks and ensure all operations are contained within the specified Docker volumes directory.

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

Or run individual test files:
```bash
python tests/test_file_mcp_server.py
python tests/test_file_api_server.py
```
