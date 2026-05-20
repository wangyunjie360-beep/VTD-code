from __future__ import annotations

from openscenario_mcp.runtime import build_runtime_from_config
from openscenario_mcp.server import build_server


def main() -> None:
    build_server(build_runtime_from_config()).run()


if __name__ == "__main__":
    main()
