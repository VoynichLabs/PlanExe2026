# Inspector

Inspecting PlanExe's MCP server. 

This is my (Simon Strandgaard) preferred way to troubleshoot MCP. Whenever there is a problem with MCP, the **inspector** is the **HAMMER**.

[Github](https://github.com/modelcontextprotocol/inspector)

[Documentation](https://modelcontextprotocol.io/docs/tools/inspector)

## Overview of PlanExe's MCP servers

PlanExe has multiple MCP servers that can be connected to.

|#|Difficulty|Description|
|-|----------|-----------|
| 1 | Beginner | MCP server at [mcp.planexe.org/](https://mcp.planexe.org/) and cost credits to use. Manage your credits via this page: [home.planexe.org](https://home.planexe.org) |
| 2 | Medium | MCP server inside docker on your own computer. |
| 3 | Expert | MCP server as a python program on your own computer. |

## Approach 1. MCP server at mcp.planexe.org

### Purchase credits

1. Open [home.planexe.org](https://home.planexe.org)
2. Sign in with Google
3. Buy credits for 1 USD.
4. Click `Generate new API key` and copy it to clipboard. You will need this API key, in order to connect to the server.

### Connect to MCP Server

```bash
npx @modelcontextprotocol/inspector --transport http --server-url https://mcp.planexe.org/mcp/
```

In the left sidebar:

1. Click **Open Auth Settings** (or expand the `Authentication` section).
2. **Do not use OAuth** – PlanExe uses API keys, not OAuth. The OAuth flow will fail with "Failed to discover OAuth metadata".
3. Use **Custom Headers** instead: click `+ Add` inside the Custom Headers section.
4. In `Header Name`, insert `X-API-Key`.
5. In `Header Value`, insert your API key (e.g. `pex_...`).
6. Click **Connect**.

If connect fails, then please report your issue on [Discord](https://planexe.org/discord). 

6. In the topbar; Click on the `Tools` tab.
7. In the `Tools` panel; Click on the `List Tools` button.

Now there should be a list with tool names and descriptions:
```
prompt_examples
task_create
task_status
task_stop
task_file_info
```

1. In the `Tools` panel; Click on the `prompt_examples` tool.
2. In the `prompt_examples` right sidepanel; Click on `Run Tool`. This should show a list of list of example prompts.


## Approach 2. MCP server inside docker

## Approach 3. MCP server as a python program

