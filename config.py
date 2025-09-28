# Configuration for Docker Volume File MCP Server

# Base path for Docker volumes (default: /var/lib/docker/volumes)
DOCKER_VOLUMES_PATH = "/var/lib/docker/volumes"

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = "INFO"

# Maximum file size for reading (in bytes, default: 10MB)
MAX_FILE_SIZE = 10485760

# Allowed file extensions (empty list means all files allowed)
ALLOWED_EXTENSIONS = []

# Enable/disable directory traversal protection
ENABLE_PATH_VALIDATION = true
