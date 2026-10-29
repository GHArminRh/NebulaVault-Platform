#!/usr/bin/env python3
"""Static source checks for Nebula Vault's Django-rendered public frontend.

This script deliberately avoids parsing Django templates as ordinary HTML. It
checks safe, source-level invariants and leaves runtime behavior to Playwright.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOTS = (
    ROOT / "templates",
    ROOT / "accounts" / "templates",
    ROOT / "blog" / "templates",
    ROOT / "comment" / "templates",
)
EMAIL_TEMPLATES = {
    "templates/registration/password_reset_email.html",
    "templates/registration/email_verification_email.html",
    "templates/registration/license_issued_email.html",
    "registration/password_reset_email.html",
}
IGNORED_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "staticfiles",
    "media",
    "docs",
}
ASSET_EXTENSIONS = {".css", ".js"}
INLINE_HANDLER = re.compile(
    r"\\son(?:click|submit|load|change|input|error|keydown|keyup)\\s*=",
    re.IGNORECASE,
)
MISSING_ALT = re.compile(r"<img\\b(?![^>]*\\balt\\s*=)[^>]*>", re.IGNORECASE)
UNTYPED_BUTTON = re.compile(
    r"<button\\b(?![^>]*\\btype\\s*=)[^>]*>", re.IGNORECASE
)
STATIC_TAG = re.compile(r"{%\\s*static\\s+['\"]([^'\"]+)['\"]")
STYLE_ATTRIBUTE = re.compile(r"\\sstyle\\s*=", re.IGNORECASE)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def source_files() -> list[Path]:
    allowed = {".py", ".html", ".js", ".css", ".json", ".yml", ".yaml"}
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in allowed
        and not is_ignored(path.relative_to(ROOT))
    ]


def public_templates() -> list[Path]:
    templates: list[Path] = []
    for template_root in TEMPLATE_ROOTS:
        if not template_root.exists():
            continue
        for path in template_root.rglob("*.html"):
            rel = relative(path)
            if "templates/admin/" in rel or rel.startswith("templates/admin/"):
                continue
            if rel in EMAIL_TEMPLATES:
                continue
            templates.append(path)
    return sorted(set(templates))


def static_candidates(asset_path: str) -> list[Path]:
    candidates = [ROOT / "static" / asset_path]
    for app in ROOT.iterdir():
        if not app.is_dir():
            continue
        candidates.append(app / "static" / asset_path)
    return candidates


def referenced_source_text(files: list[Path], exclude: Path) -> str:
    fragments: list[str] = []
    for path in files:
        if path == exclude or path.suffix.lower() not in {
            ".py",
            ".html",
            ".js",
            ".css",
            ".json",
            ".yml",
            ".yaml",
        }:
            continue
        if path.name in {"package-lock.json"}:
            continue
        try:
            fragments.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return "\\n".join(fragments)


def main() -> int:
    templates = public_templates()
    files = source_files()
    failures: list[str] = []
    warnings: list[str] = []
    inline_style_count = 0
    inline_handler_count = 0
    image_alt_missing = 0
    untyped_button_count = 0
    static_reference_count = 0

    for template in templates:
        rel = relative(template)
        source = template.read_text(encoding="utf-8")
        for match in STATIC_TAG.finditer(source):
            static_reference_count += 1
            asset_path = match.group(1)
            if "{{" in asset_path or "}}" in asset_path:
                continue
            if not any(candidate.is_file() for candidate in static_candidates(asset_path)):
                failures.append(
                    f"{rel}: {% static %} reference does not resolve: {asset_path}"
                )

        handlers = len(INLINE_HANDLER.findall(source))
        missing_alt = len(MISSING_ALT.findall(source))
        untyped_buttons = len(UNTYPED_BUTTON.findall(source))
        inline_styles = len(STYLE_ATTRIBUTE.findall(source))

        inline_handler_count += handlers
        image_alt_missing += missing_alt
        untyped_button_count += untyped_buttons
        inline_style_count += inline_styles

        if handlers:
            failures.append(
                f"{rel}: {handlers} inline event handler(s); move behavior to JS modules"
            )
        if missing_alt:
            failures.append(
                f"{rel}: {missing_alt} image(s) lack an explicit alt attribute"
            )
        if untyped_buttons:
            failures.append(
                f"{rel}: {untyped_buttons} button(s) omit type=button/submit/reset"
            )
        if inline_styles:
            warnings.append(
                f"{rel}: {inline_styles} inline style attribute(s); prefer component CSS"
            )

    unreferenced_assets: list[str] = []
    for directory in (
        ROOT / "static" / "portal" / "css",
        ROOT / "static" / "portal" / "js",
        ROOT / "accounts" / "static",
    ):
        if not directory.exists():
            continue
        for asset in sorted(directory.rglob("*")):
            if not asset.is_file() or asset.suffix.lower() not in ASSET_EXTENSIONS:
                continue
            references = referenced_source_text(files, asset)
            if asset.name not in references:
                unreferenced_assets.append(relative(asset))

    for asset in unreferenced_assets:
        warnings.append(
            f"{asset}: no source-code filename reference found; verify CMS/dynamic usage"
        )

    css_files = list((ROOT / "static" / "portal" / "css").glob("*.css"))
    css_important_count = sum(
        len(re.findall(r"!\\s*important\\b", path.read_text(encoding="utf-8"), re.I))
        for path in css_files
    )

    print("Nebula Vault frontend source audit")
    print(f"  Public templates checked: {len(templates)}")
    print(f"  Source files scanned: {len(files)}")
    print(f"  Django static references checked: {static_reference_count}")
    print(f"  Inline event handlers: {inline_handler_count}")
    print(f"  Images missing alt: {image_alt_missing}")
    print(f"  Buttons missing type: {untyped_button_count}")
    print(f"  Inline style attributes: {inline_style_count}")
    print(f"  CSS files checked: {len(css_files)}")
    print(f"  !important declarations: {css_important_count}")
    print(f"  Suspected unreferenced assets: {len(unreferenced_assets)}")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for failure in failures:
        print(f"ERROR: {failure}")

    if failures:
        print(f"Source audit failed with {len(failures)} error(s).", file=sys.stderr)
        return 1
    print("Source audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
