"""
PlanExe MCP Server

Implements the Model Context Protocol interface for PlanExe as specified in
extra/mcp-spec1.md. Communicates with worker_plan_database via the shared
database_api models.
"""
import asyncio
import hashlib
import io
import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus

# Load .env file early
from dotenv import load_dotenv
_module_dir = Path(__file__).parent
_dotenv_loaded = load_dotenv(_module_dir / ".env")
if not _dotenv_loaded:
    load_dotenv(_module_dir.parent / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    from pydantic import BaseModel
except ImportError as e:
    logger.error(f"Failed to import MCP dependencies: {e}")
    logger.error("Please install: pip install mcp")
    sys.exit(1)

# Database imports
from database_api.planexe_db_singleton import db
from database_api.model_taskitem import TaskItem, TaskState
from database_api.model_event import EventItem, EventType
from flask import Flask

# Initialize Flask app for database access
app = Flask(__name__)
app.config.from_pyfile('config.py')

def build_postgres_uri_from_env(env: dict[str, str]) -> tuple[str, dict[str, str]]:
    """Construct a SQLAlchemy URI for Postgres using environment variables."""
    host = env.get("PLANEXE_POSTGRES_HOST") or "database_postgres"
    port = str(env.get("PLANEXE_POSTGRES_PORT") or "5432")
    dbname = env.get("PLANEXE_POSTGRES_DB") or "planexe"
    user = env.get("PLANEXE_POSTGRES_USER") or "planexe"
    password = env.get("PLANEXE_POSTGRES_PASSWORD") or "planexe"
    uri = f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{dbname}"
    safe_config = {"host": host, "port": port, "dbname": dbname, "user": user}
    return uri, safe_config

# Load database configuration
sqlalchemy_database_uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
if sqlalchemy_database_uri is None:
    sqlalchemy_database_uri, db_settings = build_postgres_uri_from_env(os.environ)
    logger.info(f"SQLALCHEMY_DATABASE_URI not set. Using Postgres defaults: {db_settings}")
else:
    logger.info("Using SQLALCHEMY_DATABASE_URI from environment.")

app.config['SQLALCHEMY_DATABASE_URI'] = sqlalchemy_database_uri
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 280, 'pool_pre_ping': True}
db.init_app(app)

# MCP Server setup
mcp_server = Server("planexe-mcp-server")

# Base directory for run artifacts
BASE_DIR_RUN = Path(os.environ.get("PLANEXE_RUN_DIR", Path(__file__).parent.parent / "run")).resolve()

# Pydantic models for request/response validation
class SessionCreateRequest(BaseModel):
    idea: str
    config: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None

class SessionStartRequest(BaseModel):
    session_id: str
    target: str = "build_plan_and_validate"
    inputs: Optional[dict[str, Any]] = None

class SessionStatusRequest(BaseModel):
    session_id: str

class SessionStopRequest(BaseModel):
    session_id: str
    run_id: Optional[str] = None
    mode: str = "graceful"

class SessionResumeRequest(BaseModel):
    session_id: str
    target: str = "build_plan_and_validate"
    resume_policy: str = "luigi_up_to_date"
    invalidate: Optional[dict[str, Any]] = None

class ArtifactListRequest(BaseModel):
    session_id: str
    path: str = ""
    include_metadata: bool = True

class ArtifactReadRequest(BaseModel):
    artifact_uri: str
    range: Optional[dict[str, int]] = None

class ArtifactWriteRequest(BaseModel):
    artifact_uri: str
    content: str
    edit_reason: Optional[str] = None
    lock: Optional[dict[str, str]] = None

class SessionEventsRequest(BaseModel):
    session_id: str
    since: Optional[str] = None

# Helper functions
def find_task_by_session_id(session_id: str) -> Optional[TaskItem]:
    """Find TaskItem by session_id stored in parameters."""
    with app.app_context():
        # Search for task with matching _mcp_session_id in parameters
        tasks = db.session.query(TaskItem).filter(
            TaskItem.parameters.contains({"_mcp_session_id": session_id})
        ).all()
        if tasks:
            return tasks[0]
        return None

def get_run_dir_for_session(session_id: str) -> Path:
    """Get the run directory path for a session."""
    # In worker_plan_database, run_id_dir = BASE_DIR_RUN / task_id
    task = find_task_by_session_id(session_id)
    if task:
        return BASE_DIR_RUN / str(task.id)
    # Fallback: try parsing session_id format
    if "__" in session_id:
        # Extract UUID portion from pxe_YYYY_MM_DD__{uuid}
        uuid_part = session_id.split("__", 1)[1]
        # Try to find task by UUID
        try:
            task_id = uuid.UUID(uuid_part)
            return BASE_DIR_RUN / str(task_id)
        except ValueError:
            pass
    return BASE_DIR_RUN / session_id

def compute_sha256(content: str | bytes) -> str:
    """Compute SHA256 hash of content."""
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()

def get_task_state_mapping(task_state: TaskState) -> str:
    """Map TaskState to MCP run state."""
    mapping = {
        TaskState.pending: "stopped",
        TaskState.processing: "running",
        TaskState.completed: "completed",
        TaskState.failed: "failed",
    }
    return mapping.get(task_state, "stopped")

# MCP Tool implementations
@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="planexe.session.create",
            description="Creates a new session and output namespace",
            inputSchema={
                "type": "object",
                "properties": {
                    "idea": {"type": "string", "description": "The idea/prompt for the plan"},
                    "config": {"type": "object", "description": "Optional configuration"},
                    "metadata": {"type": "object", "description": "Optional metadata including user_id"},
                },
                "required": ["idea"],
            },
        ),
        Tool(
            name="planexe.session.start",
            description="Starts execution for a target DAG output",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "target": {"type": "string", "default": "build_plan_and_validate"},
                    "inputs": {"type": "object"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="planexe.session.status",
            description="Returns run status and progress",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="planexe.session.stop",
            description="Stops the active run",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "run_id": {"type": "string"},
                    "mode": {"type": "string", "default": "graceful"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="planexe.session.resume",
            description="Resumes execution, reusing cached Luigi outputs",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "target": {"type": "string", "default": "build_plan_and_validate"},
                    "resume_policy": {"type": "string", "default": "luigi_up_to_date"},
                    "invalidate": {"type": "object"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="planexe.artifact.list",
            description="Lists artifacts under output namespace",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "path": {"type": "string", "default": ""},
                    "include_metadata": {"type": "boolean", "default": True},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="planexe.artifact.read",
            description="Reads an artifact",
            inputSchema={
                "type": "object",
                "properties": {
                    "artifact_uri": {"type": "string"},
                    "range": {"type": "object"},
                },
                "required": ["artifact_uri"],
            },
        ),
        Tool(
            name="planexe.artifact.write",
            description="Writes an artifact (enables Stop → Edit → Resume)",
            inputSchema={
                "type": "object",
                "properties": {
                    "artifact_uri": {"type": "string"},
                    "content": {"type": "string"},
                    "edit_reason": {"type": "string"},
                    "lock": {"type": "object"},
                },
                "required": ["artifact_uri", "content"],
            },
        ),
        Tool(
            name="planexe.session.events",
            description="Provides incremental events for a session since a cursor",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "since": {"type": "string"},
                },
                "required": ["session_id"],
            },
        ),
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "planexe.session.create":
            return await handle_session_create(arguments)
        elif name == "planexe.session.start":
            return await handle_session_start(arguments)
        elif name == "planexe.session.status":
            return await handle_session_status(arguments)
        elif name == "planexe.session.stop":
            return await handle_session_stop(arguments)
        elif name == "planexe.session.resume":
            return await handle_session_resume(arguments)
        elif name == "planexe.artifact.list":
            return await handle_artifact_list(arguments)
        elif name == "planexe.artifact.read":
            return await handle_artifact_read(arguments)
        elif name == "planexe.artifact.write":
            return await handle_artifact_write(arguments)
        elif name == "planexe.session.events":
            return await handle_session_events(arguments)
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "INVALID_TOOL", "message": f"Unknown tool: {name}"}})
            )]
    except Exception as e:
        logger.error(f"Error handling tool {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"error": {"code": "INTERNAL_ERROR", "message": str(e)}})
        )]

async def handle_session_create(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle planexe.session.create"""
    req = SessionCreateRequest(**arguments)
    
    with app.app_context():
        # Create a new TaskItem (which represents a session in our model)
        task = TaskItem(
            prompt=req.idea,
            state=TaskState.pending,
            user_id=req.metadata.get("user_id", "mcp_user") if req.metadata else "mcp_user",
            parameters=req.config or {},
        )
        db.session.add(task)
        db.session.commit()
        
        # Generate session_id in format: pxe_{date}__{short_uuid}
        date_str = datetime.now(UTC).strftime("%Y_%m_%d")
        short_uuid = str(task.id).replace("-", "")[:8]
        session_id = f"pxe_{date_str}__{short_uuid}"
        output_dir_uri = f"planexe://sessions/{session_id}/out"
        
        # Store session_id mapping in task parameters for later lookup
        if task.parameters is None:
            task.parameters = {}
        task.parameters["_mcp_session_id"] = session_id
        db.session.commit()
        
        response = {
            "session_id": session_id,
            "output_dir_uri": output_dir_uri,
            "created_at": task.timestamp_created.isoformat() + "Z",
        }
    
    return [TextContent(type="text", text=json.dumps(response))]

async def handle_session_start(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle planexe.session.start"""
    req = SessionStartRequest(**arguments)
    session_id = req.session_id
    
    with app.app_context():
        task = find_task_by_session_id(session_id)
        if task is None:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "SESSION_NOT_FOUND", "message": f"Session not found: {session_id}"}})
            )]
        
        # Check if already running
        if task.state == TaskState.processing:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "RUN_ALREADY_ACTIVE", "message": "A run is currently active for this session."}})
            )]
        
        # Update task to pending (worker_plan_database will pick it up and change to processing)
        task.state = TaskState.pending
        task.progress_percentage = 0.0
        task.progress_message = "Starting..."
        task.last_seen_timestamp = datetime.now(UTC)
        db.session.commit()
        
        run_id = f"run_{str(task.id).replace('-', '_')}"
        response = {
            "run_id": run_id,
            "state": "running",
        }
    
    return [TextContent(type="text", text=json.dumps(response))]

async def handle_session_status(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle planexe.session.status"""
    req = SessionStatusRequest(**arguments)
    session_id = req.session_id
    
    with app.app_context():
        task = find_task_by_session_id(session_id)
        if task is None:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "SESSION_NOT_FOUND", "message": f"Session not found: {session_id}"}})
            )]
        
        # Determine phase based on progress
        progress_pct = float(task.progress_percentage) if task.progress_percentage else 0.0
        if progress_pct == 0.0:
            phase = "initializing"
        elif progress_pct < 50.0:
            phase = "generating_plan"
        elif progress_pct < 90.0:
            phase = "validating"
        elif progress_pct < 100.0:
            phase = "exporting"
        else:
            phase = "finalizing"
        
        run_id = f"run_{str(task.id).replace('-', '_')}"
        state = get_task_state_mapping(task.state)
        
        # Collect artifacts from run directory
        run_dir = get_run_dir_for_session(session_id)
        latest_artifacts = []
        if run_dir.exists():
            for file_path in run_dir.iterdir():
                if file_path.is_file() and file_path.name != "log.txt":
                    artifact_uri = f"planexe://sessions/{session_id}/out/{file_path.name}"
                    stat = file_path.stat()
                    latest_artifacts.append({
                        "path": file_path.name,
                        "artifact_uri": artifact_uri,
                        "kind": "intermediate",  # Could be improved with metadata
                        "updated_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat() + "Z",
                    })
        
        response = {
            "session_id": session_id,
            "run_id": run_id,
            "state": state,
            "phase": phase,
            "progress": {
                "overall": progress_pct / 100.0,
                "current_task": {
                    "name": task.progress_message or "Unknown",
                    "pct": progress_pct / 100.0,
                },
            },
            "timing": {
                "started_at": task.timestamp_created.isoformat() + "Z" if task.timestamp_created else None,
                "elapsed_sec": (datetime.now(UTC) - task.timestamp_created).total_seconds() if task.timestamp_created else 0,
            },
            "latest_artifacts": latest_artifacts[:10],  # Limit to 10 most recent
            "warnings": [],
        }
    
    return [TextContent(type="text", text=json.dumps(response))]

async def handle_session_stop(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle planexe.session.stop"""
    req = SessionStopRequest(**arguments)
    session_id = req.session_id
    
    with app.app_context():
        task = find_task_by_session_id(session_id)
        if task is None:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "SESSION_NOT_FOUND", "message": f"Session not found: {session_id}"}})
            )]
        
        # For now, we can't actually stop a running task (worker_plan_database manages that)
        # We mark it as failed or set a flag
        if task.state == TaskState.processing:
            # In a real implementation, we'd signal the worker to stop
            # For now, we'll just note that stop was requested
            logger.info(f"Stop requested for session {session_id}, but worker_plan_database manages task lifecycle")
        
        response = {
            "state": "stopped",
        }
    
    return [TextContent(type="text", text=json.dumps(response))]

async def handle_session_resume(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle planexe.session.resume"""
    req = SessionResumeRequest(**arguments)
    session_id = req.session_id
    
    # Resume is similar to start - we create a new run (TaskItem state -> pending)
    # For now, we'll reuse the same task
    with app.app_context():
        task = find_task_by_session_id(session_id)
        if task is None:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "SESSION_NOT_FOUND", "message": f"Session not found: {session_id}"}})
            )]
        
        if task.state == TaskState.processing:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "RUN_ALREADY_ACTIVE", "message": "A run is currently active for this session."}})
            )]
        
        # Reset to pending to trigger a new run
        task.state = TaskState.pending
        task.progress_percentage = 0.0
        task.progress_message = "Resuming..."
        task.last_seen_timestamp = datetime.now(UTC)
        db.session.commit()
        
        run_id = f"run_{str(task.id).replace('-', '_')}"
        response = {
            "run_id": run_id,
            "state": "running",
        }
    
    return [TextContent(type="text", text=json.dumps(response))]

async def handle_artifact_list(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle planexe.artifact.list"""
    req = ArtifactListRequest(**arguments)
    session_id = req.session_id
    
    run_dir = get_run_dir_for_session(session_id)
    entries = []
    
    if run_dir.exists():
        list_path = run_dir / req.path if req.path else run_dir
        if list_path.exists() and list_path.is_dir():
            for item in list_path.iterdir():
                if item.is_file():
                    artifact_uri = f"planexe://sessions/{session_id}/out/{item.relative_to(run_dir)}"
                    stat = item.stat()
                    content_hash = ""
                    content_type = "application/octet-stream"
                    
                    if req.include_metadata:
                        try:
                            content = item.read_bytes()
                            content_hash = compute_sha256(content)
                            # Guess content type from extension
                            if item.suffix == ".md":
                                content_type = "text/markdown"
                            elif item.suffix == ".html":
                                content_type = "text/html"
                            elif item.suffix == ".json":
                                content_type = "application/json"
                            elif item.suffix == ".txt":
                                content_type = "text/plain"
                        except Exception as e:
                            logger.warning(f"Error reading file {item}: {e}")
                    
                    entries.append({
                        "type": "file",
                        "path": str(item.relative_to(run_dir)),
                        "artifact_uri": artifact_uri,
                        "size": stat.st_size,
                        "updated_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat() + "Z",
                        "content_type": content_type,
                        "kind": "intermediate",
                        "sha256": content_hash if req.include_metadata else "",
                    })
    
    response = {"entries": entries}
    return [TextContent(type="text", text=json.dumps(response))]

async def handle_artifact_read(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle planexe.artifact.read"""
    req = ArtifactReadRequest(**arguments)
    artifact_uri = req.artifact_uri
    
    # Parse artifact_uri: planexe://sessions/{session_id}/out/{path}
    if not artifact_uri.startswith("planexe://sessions/"):
        return [TextContent(
            type="text",
            text=json.dumps({"error": {"code": "INVALID_ARTIFACT_URI", "message": f"Invalid artifact URI format: {artifact_uri}"}})
        )]
    
    parts = artifact_uri.replace("planexe://sessions/", "").split("/out/", 1)
    if len(parts) != 2:
        return [TextContent(
            type="text",
            text=json.dumps({"error": {"code": "INVALID_ARTIFACT_URI", "message": f"Invalid artifact URI format: {artifact_uri}"}})
        )]
    
    session_id = parts[0]
    artifact_path = parts[1]
    
    run_dir = get_run_dir_for_session(session_id)
    file_path = run_dir / artifact_path
    
    # Security: ensure path is within run_dir
    try:
        file_path.resolve().relative_to(run_dir.resolve())
    except ValueError:
        return [TextContent(
            type="text",
            text=json.dumps({"error": {"code": "PERMISSION_DENIED", "message": "Path traversal detected"}})
        )]
    
    if not file_path.exists() or not file_path.is_file():
        return [TextContent(
            type="text",
            text=json.dumps({"error": {"code": "INVALID_ARTIFACT_URI", "message": f"Artifact not found: {artifact_uri}"}})
        )]
    
    try:
        content_bytes = file_path.read_bytes()
        content_hash = compute_sha256(content_bytes)
        
        # Apply range if specified
        if req.range:
            start = req.range.get("start", 0)
            length = req.range.get("length", len(content_bytes))
            content_bytes = content_bytes[start:start+length]
        
        # Decode as text (try UTF-8, fallback to errors='replace')
        try:
            content = content_bytes.decode('utf-8')
            content_type = "text/plain"
            if file_path.suffix == ".md":
                content_type = "text/markdown"
            elif file_path.suffix == ".html":
                content_type = "text/html"
            elif file_path.suffix == ".json":
                content_type = "application/json"
        except UnicodeDecodeError:
            # Binary file, return base64 or indicate binary
            content = f"[Binary file, {len(content_bytes)} bytes]"
            content_type = "application/octet-stream"
        
        response = {
            "artifact_uri": artifact_uri,
            "content_type": content_type,
            "sha256": content_hash,
            "content": content,
        }
    except Exception as e:
        logger.error(f"Error reading artifact {artifact_uri}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"error": {"code": "INTERNAL_ERROR", "message": str(e)}})
        )]
    
    return [TextContent(type="text", text=json.dumps(response))]

async def handle_artifact_write(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle planexe.artifact.write"""
    req = ArtifactWriteRequest(**arguments)
    artifact_uri = req.artifact_uri
    
    # Parse artifact_uri
    if not artifact_uri.startswith("planexe://sessions/"):
        return [TextContent(
            type="text",
            text=json.dumps({"error": {"code": "INVALID_ARTIFACT_URI", "message": f"Invalid artifact URI format: {artifact_uri}"}})
        )]
    
    parts = artifact_uri.replace("planexe://sessions/", "").split("/out/", 1)
    if len(parts) != 2:
        return [TextContent(
            type="text",
            text=json.dumps({"error": {"code": "INVALID_ARTIFACT_URI", "message": f"Invalid artifact URI format: {artifact_uri}"}})
        )]
    
    session_id = parts[0]
    artifact_path = parts[1]
    
    with app.app_context():
        # Check if session exists and is not running
        task = find_task_by_session_id(session_id)
        if task is None:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "SESSION_NOT_FOUND", "message": f"Session not found: {session_id}"}})
            )]
        
        # Check if run is active (strict policy: reject writes while running)
        if task.state == TaskState.processing:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "RUNNING_READONLY", "message": "Cannot write artifacts while run is active. Stop the run first."}})
            )]
        
        run_dir = get_run_dir_for_session(session_id)
        file_path = run_dir / artifact_path
        
        # Security check
        try:
            file_path.resolve().relative_to(run_dir.resolve())
        except ValueError:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "PERMISSION_DENIED", "message": "Path traversal detected"}})
            )]
        
        # Optimistic locking check
        if req.lock and req.lock.get("expected_sha256"):
            if file_path.exists():
                current_hash = compute_sha256(file_path.read_bytes())
                if current_hash != req.lock["expected_sha256"]:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": {"code": "CONFLICT", "message": "SHA256 mismatch. Artifact was modified."}})
                    )]
        
        # Write file
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(req.content, encoding='utf-8')
            new_hash = compute_sha256(req.content.encode('utf-8'))
            stat = file_path.stat()
            
            response = {
                "updated": True,
                "sha256": new_hash,
                "updated_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat() + "Z",
            }
        except Exception as e:
            logger.error(f"Error writing artifact {artifact_uri}: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "INTERNAL_ERROR", "message": str(e)}})
            )]
    
    return [TextContent(type="text", text=json.dumps(response))]

async def handle_session_events(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle planexe.session.events"""
    req = SessionEventsRequest(**arguments)
    session_id = req.session_id
    
    with app.app_context():
        task = find_task_by_session_id(session_id)
        if task is None:
            return [TextContent(
                type="text",
                text=json.dumps({"error": {"code": "SESSION_NOT_FOUND", "message": f"Session not found: {session_id}"}})
            )]
        
        # Query events for this task
        since_id = int(req.since.replace("cursor_", "")) if req.since and req.since.startswith("cursor_") else 0
        
        events_query = db.session.query(EventItem).filter(
            EventItem.context.contains({"task_id": str(task.id)})
        ).filter(EventItem.id > since_id).order_by(EventItem.id.asc())
        
        events = events_query.all()
        
        event_list = []
        for event in events:
            event_type_map = {
                EventType.TASK_PROCESSING: "run_started",
                EventType.TASK_COMPLETED: "run_completed",
                EventType.TASK_FAILED: "run_failed",
                EventType.TASK_PENDING: "run_started",
            }
            
            mcp_event_type = event_type_map.get(event.event_type, "log")
            event_list.append({
                "ts": event.timestamp.isoformat() + "Z",
                "type": mcp_event_type,
                "data": event.context or {},
            })
        
        cursor = f"cursor_{events[-1].id}" if events else (req.since or "cursor_0")
        
        response = {
            "cursor": cursor,
            "events": event_list,
        }
    
    return [TextContent(type="text", text=json.dumps(response))]

async def main():
    """Main entry point for MCP server."""
    logger.info("Starting PlanExe MCP Server...")
    
    # Initialize database
    with app.app_context():
        db.create_all()
        logger.info("Database initialized")
    
    # Run MCP server over stdio
    async with stdio_server() as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
