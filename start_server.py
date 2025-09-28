#!/usr/bin/env python3
"""
Startup script for the Docker Volume File servers.
Supports both MCP server and FastAPI REST API.
"""

import sys
import argparse
import asyncio
import uvicorn
from pathlib import Path

def run_mcp_server():
    """Run the MCP server."""
    from file_mcp_server import main
    asyncio.run(main())

def run_api_server(host="0.0.0.0", port=8000, reload=False):
    """Run the FastAPI REST API server."""
    uvicorn.run(
        "file_api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Docker Volume File Servers")
    parser.add_argument(
        "server_type",
        choices=["mcp", "api"],
        help="Type of server to run: 'mcp' for MCP server, 'api' for REST API"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (API server only, default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (API server only, default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (API server only)"
    )
    
    args = parser.parse_args()
    
    if args.server_type == "mcp":
        print("Starting MCP server...")
        run_mcp_server()
    elif args.server_type == "api":
        print(f"Starting FastAPI server on {args.host}:{args.port}...")
        run_api_server(args.host, args.port, args.reload)

if __name__ == "__main__":
    main()
