#!/usr/bin/env python3
"""Delegated access token via Microsoft Entra device-code flow (local dev only).

Not shipped in the API container. Requires a public client app (e.g. quack-client) with
API permissions to your Quack API and admin consent.

  pip install -e ".[dev]"
  python scripts/dev_entra_access_token.py \\
    --tenant <tenant-id> \\
    --client-id <quack-client-app-id> \\
    --scope api://<api-app-id>/.default

Env fallbacks: ENTRA_TENANT_ID or AZURE_TENANT_ID, QUACK_ENTRA_PUBLIC_CLIENT_ID, QUACK_API_SCOPE.

If `python` is Cursor's AppImage, the script re-execs with `.venv/bin/python` (Linux).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _reexec_via_repo_venv_if_bundled_python() -> None:
    """Cursor's Linux build often runs `python` as the AppImage; re-exec with ./.venv/bin/python."""
    if "AppImage" not in sys.executable:
        return
    script = Path(__file__).resolve()
    root = script.parent.parent
    for name in ("python3", "python"):
        venv_python = root / ".venv" / "bin" / name
        if venv_python.is_file():
            argv = [str(venv_python), str(script), *sys.argv[1:]]
            os.execv(str(venv_python), argv)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--tenant",
        default=os.environ.get("ENTRA_TENANT_ID") or os.environ.get("AZURE_TENANT_ID") or "",
        help="Directory (tenant) ID",
    )
    p.add_argument(
        "--client-id",
        default=os.environ.get("QUACK_ENTRA_PUBLIC_CLIENT_ID") or "",
        help="Public client application (client) ID, e.g. quack-client",
    )
    p.add_argument(
        "--scope",
        default=os.environ.get("QUACK_API_SCOPE") or "",
        help="Single scope, e.g. api://<api-client-id>/.default or .../access_as_user",
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Print only the access token (for pipes)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print full token result as JSON (not with --quiet)",
    )
    return p.parse_args()


def main() -> None:
    _reexec_via_repo_venv_if_bundled_python()
    try:
        import msal
    except ImportError as exc:
        exe = sys.executable
        extra = ""
        if "AppImage" in exe or "cursor" in exe.lower():
            extra = (
                "\nYour `python` is the editor/AppImage interpreter, not the project venv.\n"
                "From the repo root run:\n"
                "  .venv/bin/python scripts/dev_entra_access_token.py ...\n"
            )
        print(
            f"Cannot import msal ({exc!s}).\n"
            f"Interpreter: {exe}\n"
            "Fix: use the same Python your venv uses, e.g.\n"
            "  .venv/bin/python -m pip install -e \".[dev]\"\n"
            "  .venv/bin/python scripts/dev_entra_access_token.py ...\n"
            "Or: python3 -m pip / python3 (if that points at the venv).\n"
            "Or: python3 -m pip install msal"
            f"{extra}",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    args = _parse_args()
    if not args.tenant or not args.client_id or not args.scope:
        print(
            "Provide --tenant, --client-id, and --scope "
            "(or ENTRA_TENANT_ID / QUACK_ENTRA_PUBLIC_CLIENT_ID / QUACK_API_SCOPE).",
            file=sys.stderr,
        )
        raise SystemExit(2)

    authority = f"https://login.microsoftonline.com/{args.tenant}"
    app = msal.PublicClientApplication(args.client_id, authority=authority)
    flow = app.initiate_device_flow(scopes=[args.scope])
    if "user_code" not in flow:
        print(flow.get("error_description") or flow, file=sys.stderr)
        raise SystemExit(1)

    if not args.quiet:
        print(flow["message"], file=sys.stderr)

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        if not args.quiet:
            print(json.dumps(result, indent=2), file=sys.stderr)
        raise SystemExit(1)

    if args.quiet:
        print(result["access_token"])
    elif args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["access_token"])
        print(
            '\n# export TOKEN=<paste above> && curl -sS -X POST "https://<host>/auth/validate" '
            '-H "Authorization: Bearer $TOKEN"',
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
