import argparse
import json
import sys
from pathlib import Path
from .planner import build_plan, ConfigurationError

def main(argv=None):
    parser = argparse.ArgumentParser(prog="simpleipa")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="validate configuration and print a dry-run plan")
    plan.add_argument("config", type=Path)
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        result = build_plan(config)
    except (OSError, json.JSONDecodeError, ConfigurationError) as exc:
        print(f"simpleipa: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "mode": "dry-run",
        "role": result.role,
        "platform": result.platform,
        "features": list(result.features),
        "actions": list(result.actions),
        "system_modified": False,
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
