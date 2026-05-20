# Codex MCP Registration

Add this server entry to `C:\Users\EDY\.codex\config.toml`:

```toml
[mcp_servers.openscenario]
command = "D:\\wyj\\OPenscenario\\scripts\\start_mcp_server.cmd"
```

The launcher prefers `py -3.14` and falls back to `C:\Python314\python.exe` so Codex uses the local interpreter that already has `mcp` installed on this machine.

Start a new Codex session after saving the config so the `openscenario` MCP server is discovered. The benchmark tasks later in the plan assume this registration is already present.
