#!/usr/bin/env python3
"""Format and validate public Django templates without touching Django Admin or emails."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOTS = (
    ROOT / "templates",
    ROOT / "accounts" / "templates",
    ROOT / "blog" / "templates",
    ROOT / "comment" / "templates",
)
# These templates are manually structured for readability and CMS placeholder
# semantics; djlint reformatting is not stable for their block-heavy markup.
# Keep them under the source audit and browser tests.
MANUALLY_FORMATTED_TEMPLATES = {
    "templates/portal/base.html",
    "templates/portal/_cart_nav.html",
    "templates/portal/cms_home_page.html",
}
TIMEOUT_SECONDS = 30


def public_templates() -> list[Path]:
    templates: list[Path] = []
    for template_root in TEMPLATE_ROOTS:
        if not template_root.exists():
            continue
        for path in template_root.rglob("*.html"):
            relative = path.relative_to(ROOT).as_posix()
            parts = path.relative_to(ROOT).parts
            # Django Admin must keep its own default look; email HTML is
            # intentionally excluded because inline styles are email-client critical.
            if "admin" in parts or "registration" in parts:
                continue
            if relative in MANUALLY_FORMATTED_TEMPLATES:
                continue
            templates.append(path)
    return sorted(set(templates))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reformat",
        action="store_true",
        help="Format the public templates instead of checking their formatting.",
    )
    args = parser.parse_args()

    executable = shutil.which("djlint")
    if executable is None:
        print("ERROR: djlint is not installed; install requirements-dev.txt.", file=sys.stderr)
        return 2

    templates = public_templates()
    action = "--reformat" if args.reformat else "--check"
    print(f"{'Formatting' if args.reformat else 'Checking'} {len(templates)} public templates.")
    failures: list[str] = []

    for template in templates:
        relative = template.relative_to(ROOT).as_posix()
        print(f"  {action[2:].capitalize()}: {relative}", flush=True)
        try:
            command = [executable, action, "--profile=django", "--indent=2"]
            if args.reformat:
                command.extend(["--warn", "--quiet"])
            command.append(str(template))
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            print(
                f"ERROR: djlint took longer than {TIMEOUT_SECONDS}s on {relative}.",
                file=sys.stderr,
            )
            return 1

        if result.returncode:
            failures.append(relative)
            detail = (result.stdout + "\n" + result.stderr).strip()
            if detail:
                print(detail, file=sys.stderr)

    if failures:
        print(
            f"Template {'formatting' if args.reformat else 'check'} failed for "
            f"{len(failures)} file(s):",
            file=sys.stderr,
        )
        for relative in failures:
            print(f"  - {relative}", file=sys.stderr)
        return 1

    print("Public template formatting passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
