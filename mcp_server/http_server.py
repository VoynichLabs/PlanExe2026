"""
HTTP server wrapper for PlanExe MCP Server

Provides HTTP/JSON endpoints for MCP tool calls with API key authentication.
Supports deployment to Railway and other cloud platforms.
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Header, Depends, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env file early
from dotenv import load_dotenv
_module_dir = Path(__file__).parent
_dotenv_loaded = load_dotenv(_module_dir / ".env")
if not _dotenv_loaded:
    load_dotenv(_module_dir.parent / ".env")

# Import MCP tool handlers from app.py
from mcp_server.app import (
    handle_session_create,
    handle_session_start,
    handle_session_status,
    handle_session_stop,
    handle_session_resume,
    handle_artifact_list,
    handle_artifact_read,
    handle_artifact_write,
    handle_session_events,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PlanExe MCP Server (HTTP)",
    description="HTTP wrapper for PlanExe MCP interface",
    version="1.0.0"
)

# CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key validation
REQUIRED_API_KEY = os.environ.get("PLANEXE_MCP_API_KEY")
if not REQUIRED_API_KEY:
    logger.warning("PLANEXE_MCP_API_KEY not set. API key authentication disabled (not recommended for production)")

def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key: Optional[str] = Header(None, alias="API_KEY")
):
    """Verify API key from header. Supports both X-API-Key and API_KEY headers."""
    if not REQUIRED_API_KEY:
        # No API key configured, allow all (development mode)
        return True
    
    # Support both header formats
    provided_key = x_api_key or api_key
    
    if not provided_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key or API_KEY header."
        )
    
    if provided_key != REQUIRED_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return True

# Request/Response models
class MCPToolCallRequest(BaseModel):
    tool: str
    arguments: dict[str, Any]

class MCPToolCallResponse(BaseModel):
    content: list[dict[str, Any]]
    error: Optional[dict[str, Any]] = None

def extract_text_content(text_contents: list) -> list[dict[str, Any]]:
    """Extract text content from MCP TextContent objects."""
    result = []
    for item in text_contents:
        if hasattr(item, 'text'):
            # Try to parse as JSON, fallback to plain text
            try:
                parsed = json.loads(item.text)
                result.append(parsed)
            except json.JSONDecodeError:
                result.append({"text": item.text})
        elif isinstance(item, dict):
            result.append(item)
        else:
            result.append({"text": str(item)})
    return result

def to_content_blocks(content_items: list[Any]) -> list[dict[str, Any]]:
    """Coerce content into MCP content blocks."""
    blocks: list[dict[str, Any]] = []
    for item in content_items:
        if isinstance(item, dict) and "type" in item:
            blocks.append(item)
            continue
        if isinstance(item, str):
            text = item
        else:
            try:
                text = json.dumps(item)
            except TypeError:
                text = str(item)
        blocks.append({"type": "text", "text": text})
    return blocks

async def handle_jsonrpc_request(body: dict[str, Any]) -> Response:
    """Handle JSON-RPC 2.0 MCP requests."""
    request_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})
    logger.info(f"Detected JSON-RPC 2.0 format: method={method!r}, type={type(method)}, params={params}, id={request_id}")

    # JSON-RPC notifications should not receive a response body.
    if request_id is None and isinstance(method, str) and method.startswith("notifications/"):
        logger.info(f"Ignoring JSON-RPC notification: {method}")
        return Response(status_code=204)

    # Handle MCP protocol methods
    logger.info(f"Processing JSON-RPC method: {method!r}, checking if == 'initialize': {method == 'initialize'}")
    if method == "initialize":
        # MCP initialization handshake
        logger.info("Handling initialize method")
        result = {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {
                "tools": {"listChanged": False}
            },
            "serverInfo": {
                "name": "planexe-mcp-server",
                "version": "1.0.0"
            }
        }
        response = {"jsonrpc": "2.0", "result": result, "id": request_id}
        logger.info(f"Sending initialize response: {response}")
        return JSONResponse(content=response)

    if method == "tools/list":
        # List available tools
        tools = await list_tools_internal()
        # Tools already have proper MCP format with inputSchema
        result = {"tools": tools}
        return JSONResponse(content={"jsonrpc": "2.0", "result": result, "id": request_id})

    if method == "tools/call":
        # Call a tool
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        logger.info(f"Calling tool via JSON-RPC: {tool_name} with args: {tool_args}")
        tool_result = await call_tool_internal(tool_name, tool_args)

        # Convert MCPToolCallResponse to JSON-RPC result
        # MCP tools/call expects result.content to be an array of content blocks
        if tool_result.error:
            content_items = tool_result.content or [{"error": tool_result.error}]
            result = {
                "content": to_content_blocks(content_items),
                "isError": True
            }
            return JSONResponse(content={"jsonrpc": "2.0", "result": result, "id": request_id})

        result = {
            "content": to_content_blocks(tool_result.content),
            "isError": False
        }
        return JSONResponse(content={"jsonrpc": "2.0", "result": result, "id": request_id})

    if request_id is None:
        logger.info(f"Ignoring JSON-RPC notification with unknown method: {method}")
        return Response(status_code=204)

    # Unknown method
    error_response = {
        "jsonrpc": "2.0",
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        },
        "id": request_id
    }
    return JSONResponse(content=error_response, status_code=200)  # JSON-RPC errors are 200 OK with error in body

@app.get("/mcp")
async def mcp_get_endpoint(
    request: Request,
    _: bool = Depends(verify_api_key)
):
    """
    GET endpoint for MCP (SSE or info).
    
    LM Studio may try to GET /mcp for SSE connection or to discover the endpoint.
    """
    logger.info(f"Received GET /mcp - Accept: {request.headers.get('Accept')}, Headers: {dict(request.headers)}")
    
    # Check if client wants SSE
    accept_header = request.headers.get("Accept", "")
    if "text/event-stream" in accept_header:
        logger.info("Client requested SSE stream")
        # Return SSE stream
        async def generate_sse():
            yield "data: {\"type\": \"connected\", \"message\": \"MCP Server Ready\"}\n\n"
            # Keep connection alive with periodic keepalive
            while True:
                await asyncio.sleep(30)
                yield ": keepalive\n\n"
        
        return StreamingResponse(
            generate_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable buffering for nginx
            }
        )
    
    # Return endpoint info
    return {
        "protocol": "MCP HTTP",
        "version": "1.0",
        "endpoints": {
            "tools": "/mcp/tools",
            "call": "/mcp/tools/call",
            "post": "/mcp"
        },
        "note": "Use POST /mcp with {\"tool\": \"tool_name\", \"arguments\": {...}} for tool calls"
    }

@app.post("/mcp")
async def mcp_post_endpoint(
    request: Request,
    _: bool = Depends(verify_api_key)
):
    """
    Main MCP endpoint for tool calls (POST).
    
    Compatible with MCP clients that expect a single endpoint.
    """
    try:
        # Read raw body for logging
        raw_body = await request.body()
        logger.info(f"Received POST /mcp request - Content-Type: {request.headers.get('Content-Type')}, Body length: {len(raw_body)}")
        
        if not raw_body:
            raise HTTPException(status_code=400, detail="Request body is empty")
        
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON body: {e}, raw body: {raw_body[:200]}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        
        logger.info(f"Parsed MCP request body: {json.dumps(body, indent=2)}")
        
        # Handle JSON-RPC 2.0 format (MCP protocol)
        if isinstance(body, dict) and "method" in body and "jsonrpc" in body:
            return await handle_jsonrpc_request(body)

        # Try to parse as MCPToolCallRequest
        try:
            mcp_request = MCPToolCallRequest(**body)
            logger.info(f"Calling tool: {mcp_request.tool} with arguments: {mcp_request.arguments}")
            return await call_tool_internal(mcp_request.tool, mcp_request.arguments)
        except Exception as e:
            logger.warning(f"Failed to parse as MCPToolCallRequest: {e}, body: {body}")

            # If still not parseable, return error with helpful message
            logger.error(f"Unknown request format: {body}")
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Invalid request format",
                    "expected": {
                        "tool": "string",
                        "arguments": "object"
                    },
                    "alternative_formats": [
                        {"tool": "string", "arguments": "object"},
                        {"method": "string", "params": "object", "jsonrpc": "2.0", "id": "number"}  # JSON-RPC 2.0 style
                    ],
                    "received": body
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in mcp_post_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/tools/call", response_model=MCPToolCallResponse)
async def call_tool(
    request: MCPToolCallRequest,
    _: bool = Depends(verify_api_key)
):
    """
    Call an MCP tool by name with arguments.
    
    This endpoint wraps the stdio-based MCP tool handlers for HTTP access.
    """
    return await call_tool_internal(request.tool, request.arguments)

async def call_tool_internal(tool_name: str, arguments: dict[str, Any]) -> MCPToolCallResponse:
    """Internal tool call handler."""
    try:
        # Route to appropriate handler
        if tool_name == "planexe.session.create":
            result = await handle_session_create(arguments)
        elif tool_name == "planexe.session.start":
            result = await handle_session_start(arguments)
        elif tool_name == "planexe.session.status":
            result = await handle_session_status(arguments)
        elif tool_name == "planexe.session.stop":
            result = await handle_session_stop(arguments)
        elif tool_name == "planexe.session.resume":
            result = await handle_session_resume(arguments)
        elif tool_name == "planexe.artifact.list":
            result = await handle_artifact_list(arguments)
        elif tool_name == "planexe.artifact.read":
            result = await handle_artifact_read(arguments)
        elif tool_name == "planexe.artifact.write":
            result = await handle_artifact_write(arguments)
        elif tool_name == "planexe.session.events":
            result = await handle_session_events(arguments)
        else:
            return MCPToolCallResponse(
                content=[],
                error={
                    "code": "INVALID_TOOL",
                    "message": f"Unknown tool: {tool_name}"
                }
            )
        
        # Extract text content from MCP response format
        content = extract_text_content(result)
        
        # Check if any content contains an error
        error = None
        for item in content:
            if isinstance(item, dict) and "error" in item:
                error = item["error"]
                break
        
        return MCPToolCallResponse(content=content, error=error)
        
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}", exc_info=True)
        return MCPToolCallResponse(
            content=[],
            error={
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        )

async def list_tools_internal() -> list[dict[str, Any]]:
    """Internal tool list generator with full MCP tool schemas."""
    return [
        {
            "name": "planexe.session.create",
            "description": "Creates a new session and output namespace",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "idea": {"type": "string", "description": "The idea/prompt for the plan"},
                    "config": {"type": "object", "description": "Optional configuration"},
                    "metadata": {"type": "object", "description": "Optional metadata including user_id"},
                },
                "required": ["idea"],
            },
        },
        {
            "name": "planexe.session.start",
            "description": "Starts execution for a target DAG output",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "target": {"type": "string", "default": "build_plan_and_validate"},
                    "inputs": {"type": "object"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "planexe.session.status",
            "description": "Returns run status and progress",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "planexe.session.stop",
            "description": "Stops the active run",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "run_id": {"type": "string"},
                    "mode": {"type": "string", "default": "graceful"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "planexe.session.resume",
            "description": "Resumes execution, reusing cached Luigi outputs",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "target": {"type": "string", "default": "build_plan_and_validate"},
                    "resume_policy": {"type": "string", "default": "luigi_up_to_date"},
                    "invalidate": {"type": "object"},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "planexe.artifact.list",
            "description": "Lists artifacts under output namespace",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "path": {"type": "string", "default": ""},
                    "include_metadata": {"type": "boolean", "default": True},
                },
                "required": ["session_id"],
            },
        },
        {
            "name": "planexe.artifact.read",
            "description": "Reads an artifact",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "artifact_uri": {"type": "string"},
                    "range": {"type": "object"},
                },
                "required": ["artifact_uri"],
            },
        },
        {
            "name": "planexe.artifact.write",
            "description": "Writes an artifact (enables Stop → Edit → Resume)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "artifact_uri": {"type": "string"},
                    "content": {"type": "string"},
                    "edit_reason": {"type": "string"},
                    "lock": {"type": "object"},
                },
                "required": ["artifact_uri", "content"],
            },
        },
        {
            "name": "planexe.session.events",
            "description": "Provides incremental events for a session since a cursor",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "since": {"type": "string"},
                },
                "required": ["session_id"],
            },
        },
    ]

@app.get("/mcp/tools")
async def list_tools(_: bool = Depends(verify_api_key)):
    """
    List all available MCP tools.
    """
    return {"tools": await list_tools_internal()}

@app.get("/healthcheck")
def healthcheck():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "planexe-mcp-http",
        "api_key_configured": REQUIRED_API_KEY is not None
    }

@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "service": "PlanExe MCP Server (HTTP)",
        "version": "1.0.0",
        "endpoints": {
            "mcp": "/mcp",
            "tools": "/mcp/tools",
            "call": "/mcp/tools/call",
            "health": "/healthcheck"
        },
        "documentation": "See /docs for OpenAPI documentation",
        "authentication": "X-API-Key header required (set PLANEXE_MCP_API_KEY)"
    }

if __name__ == "__main__":
    import uvicorn
    
    host = os.environ.get("PLANEXE_MCP_HTTP_HOST", "0.0.0.0")
    # Railway provides PORT env var, otherwise use PLANEXE_MCP_HTTP_PORT or default
    port = int(os.environ.get("PORT") or os.environ.get("PLANEXE_MCP_HTTP_PORT", "8001"))
    
    logger.info(f"Starting PlanExe MCP HTTP server on {host}:{port}")
    if REQUIRED_API_KEY:
        logger.info("API key authentication enabled")
    else:
        logger.warning("API key authentication disabled - set PLANEXE_MCP_API_KEY")
    
    uvicorn.run("http_server:app", host=host, port=port, reload=False)
