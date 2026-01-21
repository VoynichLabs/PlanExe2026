# PlanExe MCP locally

Model Context Protocol (MCP) interface for PlanExe. 

This runs on the users own computer, so it has disk access disk.
Unlike the `PlanExe/mcp_server` that runs in the cloud and has no disk access.

## Tools

`task_create` - Initiate creation of a plan.
`task_status` - Get status and progress about the creation of a plan.
`task_stop` - Abort creation of a plan.
`task_download` - Download the plan, either html report or a zip with everything, and saves it to disk.

Here is what I imagine what it will be like:

### Development on localhost

```json
"planexe": {
  "command": "uv",
  "args": [
    "run",
    "--with",
    "mcp",
    "/absolute/path/to/planexe/v1/mcp.py"
  ],
  "env": {
    "PLANEXE_URL": "http://localhost:8001/v1/api",
    "PLANEXE_API_KEY": "insert-your-api-key-here",
    "PLANEXE_PATH": "/User/your-name/Desktop",
  }
}
```


### Connect to docker on localhost

```json
"planexe": {
  "command": "uvx",
  "args": [
    "-y",
    "@planexe/v1/mcp"
  ],
  "env": {
    "PLANEXE_URL": "http://localhost:8001/v1/api",
    "PLANEXE_API_KEY": "insert-your-api-key-here",
    "PLANEXE_PATH": "/User/your-name/Desktop",
  }
}
```

### Connect to PlanExe server hosted on Railway

When omitting `PLANEXE_URL`, the mcp server connects with the server in the cloud.

```json
"planexe": {
  "command": "uvx",
  "args": [
    "-y",
    "@planexe/v1/mcp"
  ],
  "env": {
    "PLANEXE_API_KEY": "insert-your-api-key-here",
    "PLANEXE_PATH": "/User/your-name/Desktop",
  }
}
```
