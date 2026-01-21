"""
PlanExe MCP local proxy.

Runs locally over stdio and forwards tool calls to a remote PlanExe MCP server.
Downloads artifacts to disk for task_download.
"""
import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_MCP_URL = "https://your-railway-app.up.railway.app/mcp"
REPORT_FILENAME = "030-report.html"
ZIP_FILENAME = "run.zip"


class TaskCreateRequest(BaseModel):
    idea: str
    speed_vs_detail: Optional[str] = None


class TaskStatusRequest(BaseModel):
    task_id: str


class TaskStopRequest(BaseModel):
    task_id: str


class TaskDownloadRequest(BaseModel):
    task_id: str
    artifact: str = "report"


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    return value if value else default


def _get_mcp_base_url() -> str:
    raw_url = _get_env("PLANEXE_URL", DEFAULT_MCP_URL)
    if not raw_url:
        raw_url = DEFAULT_MCP_URL
    raw_url = raw_url.strip()
    parsed = urlparse(raw_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/mcp/tools/call"):
        path = path[: -len("/tools/call")]
    elif path.endswith("/mcp/tools"):
        path = path[: -len("/tools")]
    elif path.endswith("/tools/call"):
        path = path[: -len("/tools/call")]
    elif path.endswith("/tools"):
        path = path[: -len("/tools")]
    if not path.endswith("/mcp"):
        path = f"{path}/mcp".rstrip("/")
    normalized = parsed._replace(path=path, params="", query="", fragment="").geturl()
    return normalized


def _get_download_base_url() -> str:
    base_url = _get_mcp_base_url()
    if base_url.endswith("/mcp"):
        return base_url[:-4]
    return base_url


def _build_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = _get_env("PLANEXE_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _http_json_request(method: str, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method=method, headers=_build_headers())
    with urlopen(request, timeout=60) as response:
        response_body = response.read().decode("utf-8")
    return json.loads(response_body) if response_body else {}


def _http_get_bytes(url: str) -> bytes:
    request = Request(url, method="GET", headers=_build_headers())
    with urlopen(request, timeout=60) as response:
        return response.read()


def _extract_payload(content: list[dict[str, Any]]) -> dict[str, Any]:
    for item in content:
        text = item.get("text") if isinstance(item, dict) else None
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"result": text}
        if isinstance(parsed, dict):
            return parsed
        return {"result": parsed}
    return {}


def _call_remote_tool(tool: str, arguments: dict[str, Any]) -> tuple[dict[str, Any], Optional[dict[str, Any]]]:
    mcp_base_url = _get_mcp_base_url()
    url = f"{mcp_base_url}/tools/call"
    payload = {"tool": tool, "arguments": arguments}
    try:
        response = _http_json_request("POST", url, payload)
    except Exception as exc:
        logger.error("Remote MCP request failed: %s", exc)
        return {}, {"code": "REMOTE_ERROR", "message": str(exc)}
    error = response.get("error")
    if error:
        return {}, error
    content = response.get("content", [])
    return _extract_payload(content), None


def _hash_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _derive_download_url(task_id: str, artifact: str) -> str:
    if artifact == "zip":
        path = f"/download/{task_id}/{ZIP_FILENAME}"
    else:
        path = f"/download/{task_id}/{REPORT_FILENAME}"
    return urljoin(_get_download_base_url().rstrip("/") + "/", path.lstrip("/"))


def _ensure_directory(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise ValueError(f"PLANEXE_PATH is not a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _choose_output_path(task_id: str, download_url: str, artifact: str) -> Path:
    base_path = Path(_get_env("PLANEXE_PATH", str(Path.cwd()))).expanduser()
    _ensure_directory(base_path)

    basename = Path(urlparse(download_url).path).name
    if not basename:
        basename = REPORT_FILENAME if artifact == "report" else ZIP_FILENAME
    filename = f"{task_id}-{basename}"
    candidate = base_path / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    for index in range(1, 1000):
        fallback = base_path / f"{stem}-{index}{suffix}"
        if not fallback.exists():
            return fallback
    raise ValueError(f"Unable to find available filename in {base_path}")


def _download_to_path(download_url: str, destination: Path) -> int:
    content = _http_get_bytes(download_url)
    destination.write_bytes(content)
    return len(content)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: Optional[dict[str, Any]] = None


ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string"},
        "message": {"type": "string"},
    },
    "required": ["code", "message"],
}

TASK_CREATE_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "idea": {"type": "string"},
        "speed_vs_detail": {
            "type": "string",
            "enum": ["ping", "fast", "all"],
            "default": "ping",
        },
    },
    "required": ["idea"],
}

TASK_STATUS_INPUT_SCHEMA = {
    "type": "object",
    "properties": {"task_id": {"type": "string"}},
    "required": ["task_id"],
}

TASK_STOP_INPUT_SCHEMA = {
    "type": "object",
    "properties": {"task_id": {"type": "string"}},
    "required": ["task_id"],
}

TASK_DOWNLOAD_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {"type": "string"},
        "artifact": {"type": "string", "enum": ["report", "zip"], "default": "report"},
    },
    "required": ["task_id"],
}

TASK_CREATE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {"type": "string"},
        "created_at": {"type": "string"},
    },
    "required": ["task_id", "created_at"],
}

TASK_STATUS_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {"type": ["string", "null"]},
        "state": {"type": ["string", "null"]},
        "progress_percentage": {"type": ["number", "null"]},
    },
}

TASK_STOP_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "state": {"type": "string"},
        "error": ERROR_SCHEMA,
    },
}

TASK_DOWNLOAD_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "content_type": {"type": "string"},
        "sha256": {"type": "string"},
        "download_size": {"type": "integer"},
        "download_url": {"type": "string"},
        "saved_path": {"type": "string"},
        "error": ERROR_SCHEMA,
    },
    "additionalProperties": False,
}

TOOL_DEFINITIONS = [
    ToolDefinition(
        name="task_create",
        description="Create a new task in the remote PlanExe MCP server.",
        input_schema=TASK_CREATE_INPUT_SCHEMA,
        output_schema=TASK_CREATE_OUTPUT_SCHEMA,
    ),
    ToolDefinition(
        name="task_status",
        description="Fetch task status from the remote PlanExe MCP server.",
        input_schema=TASK_STATUS_INPUT_SCHEMA,
        output_schema=TASK_STATUS_OUTPUT_SCHEMA,
    ),
    ToolDefinition(
        name="task_stop",
        description="Stop a task in the remote PlanExe MCP server.",
        input_schema=TASK_STOP_INPUT_SCHEMA,
        output_schema=TASK_STOP_OUTPUT_SCHEMA,
    ),
    ToolDefinition(
        name="task_download",
        description="Download report or zip for a task and save it locally.",
        input_schema=TASK_DOWNLOAD_INPUT_SCHEMA,
        output_schema=TASK_DOWNLOAD_OUTPUT_SCHEMA,
    ),
]

mcp_server = Server("planexe-mcp-local")


@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name=definition.name,
            description=definition.description,
            inputSchema=definition.input_schema,
            outputSchema=definition.output_schema,
        )
        for definition in TOOL_DEFINITIONS
    ]


def _wrap_response(payload: dict[str, Any], is_error: bool = False) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload))],
        structuredContent=payload,
        isError=is_error,
    )


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        response = {"error": {"code": "INVALID_TOOL", "message": f"Unknown tool: {name}"}}
        return [TextContent(type="text", text=json.dumps(response))]
    result = await handler(arguments)
    return result.content


async def handle_task_create(arguments: dict[str, Any]) -> CallToolResult:
    req = TaskCreateRequest(**arguments)
    payload, error = _call_remote_tool(
        "task_create",
        {"idea": req.idea, "speed_vs_detail": req.speed_vs_detail} if req.speed_vs_detail else {"idea": req.idea},
    )
    if error:
        return _wrap_response({"error": error}, is_error=True)
    return _wrap_response(payload)


async def handle_task_status(arguments: dict[str, Any]) -> CallToolResult:
    req = TaskStatusRequest(**arguments)
    payload, error = _call_remote_tool("task_status", {"task_id": req.task_id})
    if error:
        return _wrap_response({"error": error}, is_error=True)
    return _wrap_response(payload)


async def handle_task_stop(arguments: dict[str, Any]) -> CallToolResult:
    req = TaskStopRequest(**arguments)
    payload, error = _call_remote_tool("task_stop", {"task_id": req.task_id})
    if error:
        return _wrap_response({"error": error}, is_error=True)
    return _wrap_response(payload)


async def handle_task_download(arguments: dict[str, Any]) -> CallToolResult:
    req = TaskDownloadRequest(**arguments)
    artifact = (req.artifact or "report").strip().lower()
    if artifact not in ("report", "zip"):
        artifact = "report"

    payload, error = _call_remote_tool(
        "task_file_info",
        {"task_id": req.task_id, "artifact": artifact},
    )
    if error:
        return _wrap_response({"error": error}, is_error=True)
    if not payload:
        return _wrap_response(payload)

    download_url = payload.get("download_url")
    if isinstance(download_url, str) and download_url.startswith("/"):
        download_url = urljoin(_get_download_base_url().rstrip("/") + "/", download_url.lstrip("/"))
    if not download_url:
        download_url = _derive_download_url(req.task_id, artifact)

    try:
        destination = _choose_output_path(req.task_id, download_url, artifact)
        downloaded_size = _download_to_path(download_url, destination)
    except Exception as exc:
        return _wrap_response(
            {"error": {"code": "DOWNLOAD_FAILED", "message": str(exc)}},
            is_error=True,
        )

    payload["download_url"] = download_url
    payload["saved_path"] = str(destination)

    sha256 = payload.get("sha256")
    if isinstance(sha256, str):
        actual_sha = _hash_sha256(destination.read_bytes())
        if sha256 != actual_sha:
            logger.warning("SHA256 mismatch for %s (expected %s, got %s)", destination, sha256, actual_sha)

    size_value = payload.get("download_size")
    if isinstance(size_value, (int, float)) and int(size_value) != downloaded_size:
        logger.warning(
            "Download size mismatch for %s (expected %s, got %s)",
            destination,
            size_value,
            downloaded_size,
        )

    return _wrap_response(payload)


TOOL_HANDLERS = {
    "task_create": handle_task_create,
    "task_status": handle_task_status,
    "task_stop": handle_task_stop,
    "task_download": handle_task_download,
}


async def main() -> None:
    logger.info("Starting PlanExe MCP local proxy using %s", _get_mcp_base_url())
    async with stdio_server() as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
