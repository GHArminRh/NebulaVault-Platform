#!/usr/bin/env python3
"""Assemble and validate deterministic CSS bundles from ordered feature modules."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Module order is the cascade contract. Keep these lists explicit and review
# changes to them together with the stylesheet order in templates/portal/base.html.
BUNDLES = {
    "static/portal/css/site.css": (
        "frontend/css/site/01-global-shell.css",
        "frontend/css/site/02-home-hero.css",
        "frontend/css/site/03-home-sections.css",
        "frontend/css/site/04-catalog-pages.css",
        "frontend/css/site/05-dashboard.css",
        "frontend/css/site/06-authentication-and-messages.css",
        "frontend/css/site/07-responsive-and-rtl.css",
        "frontend/css/site/08-authentication-polish.css",
        "frontend/css/site/09-storefront-polish.css",
        "frontend/css/site/10-dashboard-refinements.css",
        "frontend/css/site/11-commerce-and-account.css",
        "frontend/css/site/12-visual-utilities.css",
    ),
    "static/portal/css/unified-experience.css": (
        "frontend/css/experience/01-storefront.css",
        "frontend/css/experience/02-authentication.css",
        "frontend/css/experience/03-dashboard.css",
        "frontend/css/experience/04-navigation-and-effects.css",
        "frontend/css/experience/05-responsive-layouts.css",
        "frontend/css/experience/06-navigation-responsive.css",
        "frontend/css/experience/07-dashboard-responsive.css",
        "frontend/css/experience/08-dashboard-shell-and-progress.css",
        "frontend/css/experience/09-header-effects.css",
    ),
}


def assemble(module_paths: tuple[str, ...]) -> str:
    """Read CSS modules in declared order without rewriting their contents."""
    parts: list[str] = []
    for relative_path in module_paths:
        path = ROOT / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"CSS source module is missing: {relative_path}")

        content = path.read_text(encoding="utf-8")
        if content and not content.endswith("\n"):
            raise ValueError(f"CSS source module must end with a newline: {relative_path}")
        parts.append(content)

    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Regenerate committed CSS bundles.")
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail when a committed bundle differs from its ordered source modules.",
    )
    args = parser.parse_args()
    write = args.write

    failures: list[str] = []
    for output_name, module_paths in BUNDLES.items():
        output_path = ROOT / output_name
        try:
            expected = assemble(module_paths)
        except (OSError, UnicodeError, ValueError) as error:
            failures.append(str(error))
            continue

        if write:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(expected, encoding="utf-8", newline="\n")
            print(f"Updated {output_name} ({len(expected)} characters).")
            continue

        try:
            actual = output_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            failures.append(f"Generated CSS bundle is missing: {output_name}")
            continue
        except (OSError, UnicodeError) as error:
            failures.append(f"Cannot read {output_name}: {error}")
            continue

        if actual != expected:
            failures.append(
                f"{output_name} is out of date. Run: python scripts/build_frontend_css.py --write"
            )
        else:
            print(f"Verified {output_name} ({len(expected)} characters).")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print("CSS bundle validation passed." if not write else "CSS bundle generation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
