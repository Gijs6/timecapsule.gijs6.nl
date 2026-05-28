#!/usr/bin/env python3

import argparse
import glob
import os
import re
import sys


def convert_query_to_filename(path, query):
    path = path.lstrip("/") or "index"
    base, ext = os.path.splitext(path)

    if query:
        query_part = query.replace("=", "_").replace("&", "_")
        return f"{base}_{query_part}.html"
    elif not ext:
        return f"{path}.html"
    return path


def fix_html_paths(file_path, version_name):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    base_path = f"/versions/{version_name}"

    content = re.sub(r'(href|src)="/static/', rf'\1="{base_path}/static/', content)

    def replace_query_link(match):
        filename = convert_query_to_filename(match.group(2), match.group(3))
        return f'{match.group(1)}="{base_path}/{filename}"'

    content = re.sub(r'(href|src)="(/[^"?]*)\?([^"]+)"', replace_query_link, content)

    current_base = os.path.basename(file_path).split("_lang_")[0].replace(".html", "")

    content = re.sub(
        r'href="\?([^"]+)"',
        lambda m: f'href="{convert_query_to_filename(current_base, m.group(1))}"',
        content,
    )

    content = re.sub(r'href="/"(\s|>)', rf'href="{base_path}/index.html"\1', content)
    content = re.sub(
        r'href="/(?!versions/)([^"?]+)"', rf'href="{base_path}/\1"', content
    )

    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Fix relative paths in versioned HTML files"
    )
    parser.add_argument("version", help="Version name to process (e.g. v4)")
    parser.add_argument("--versions-dir", default="site/versions")
    args = parser.parse_args()

    version_dir = os.path.join(args.versions_dir, args.version)
    if not os.path.isdir(version_dir):
        print(f"Error: {version_dir} does not exist")
        sys.exit(1)

    print(f"Fixing paths: {args.version}\n")

    html_files = glob.glob(os.path.join(version_dir, "**", "*.html"), recursive=True)
    if not html_files:
        print(f"No HTML files found in {version_dir}")
        return

    modified = 0
    for html_file in html_files:
        rel = os.path.relpath(html_file, args.versions_dir)
        if fix_html_paths(html_file, args.version):
            print(f"  [ok] Fixed: {rel}")
            modified += 1
        else:
            print(f"  - No changes: {rel}")

    print(f"\n[ok] Done! Modified {modified}/{len(html_files)} files in {args.version}")


if __name__ == "__main__":
    main()
