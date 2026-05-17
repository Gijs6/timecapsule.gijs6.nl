#!/usr/bin/env python3

import argparse
import os
import re
import sys

def convert_query_to_filename(path, query):
    if path.startswith('/'):
        path = path[1:]

    if not path:
        path = 'index'

    if query:
        query_part = query.replace('=', '_').replace('&', '_')
        base, ext = os.path.splitext(path)
        if ext:
            return "{}_{}.html".format(base, query_part)
        else:
            return "{}_{}.html".format(path, query_part)
    else:
        if not os.path.splitext(path)[1]:
            return "{}.html".format(path)
        return path

def fix_html_paths(file_path, version_name):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    base_path = "/versions/{}".format(version_name)

    content = re.sub(
        r'(href|src)="/static/',
        r'\1="' + base_path + r'/static/',
        content
    )

    def replace_query_link(match):
        prefix = match.group(1)
        path = match.group(2)
        query = match.group(3)

        filename = convert_query_to_filename(path, query)
        return '{}="{}/{}"'.format(prefix, base_path, filename)

    content = re.sub(
        r'(href|src)="(/[^"?]*)\?([^"]+)"',
        replace_query_link,
        content
    )

    current_file = os.path.basename(file_path)
    current_base = current_file.split('_lang_')[0] if '_lang_' in current_file else current_file.replace('.html', '')

    def replace_relative_query(match):
        query = match.group(1)
        filename = convert_query_to_filename(current_base, query)
        return 'href="{}"'.format(filename)

    content = re.sub(
        r'href="\?([^"]+)"',
        replace_relative_query,
        content
    )

    content = re.sub(
        r'href="/"(\s|>)',
        r'href="' + base_path + r'/index.html"\1',
        content
    )

    content = re.sub(
        r'href="/(?!versions/)([^"?]+)"',
        r'href="' + base_path + r'/\1"',
        content
    )

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def find_html_files(directory):
    html_files = []
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.html'):
                html_files.append(os.path.join(root, filename))
    return html_files

def list_available_versions(versions_dir):
    versions = []
    if os.path.exists(versions_dir):
        for item in os.listdir(versions_dir):
            item_path = os.path.join(versions_dir, item)
            if os.path.isdir(item_path):
                versions.append(item)
    return sorted(versions)

def main():
    parser = argparse.ArgumentParser(
        description='Fix relative paths in versioned HTML files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s v4
  %(prog)s v4 --versions-dir site/versions
        """
    )
    parser.add_argument('version', nargs='?', help='Version name to process (e.g. v4)')
    parser.add_argument('--versions-dir', default='site/versions',
                        help='Directory containing version subdirectories (default: site/versions)')

    args = parser.parse_args()
    versions_dir = args.versions_dir

    if not os.path.exists(versions_dir):
        print("Error: {} does not exist".format(versions_dir))
        sys.exit(1)

    if args.version:
        version_name = args.version
    else:
        available_versions = list_available_versions(versions_dir)

        if not available_versions:
            print("Error: No version directories found in {}".format(versions_dir))
            sys.exit(1)

        print("Available versions:")
        for version in available_versions:
            print("  - {}".format(version))

        version_name = input("\nEnter version name to process: ").strip()

    version_dir = os.path.join(versions_dir, version_name)

    if not os.path.exists(version_dir):
        print("Error: Version directory {} does not exist".format(version_dir))
        sys.exit(1)

    if not os.path.isdir(version_dir):
        print("Error: {} is not a directory".format(version_dir))
        sys.exit(1)

    print("Fixing paths: {}".format(version_name))
    print("  Versions dir: {}".format(versions_dir))
    print()

    html_files = find_html_files(version_dir)

    if not html_files:
        print("No HTML files found in {}".format(version_dir))
        return

    modified_count = 0
    for html_file in html_files:
        rel_path = os.path.relpath(html_file, versions_dir)

        if fix_html_paths(html_file, version_name):
            print("  [ok] Fixed: {}".format(rel_path))
            modified_count += 1
        else:
            print("  - No changes: {}".format(rel_path))

    print()
    print("[ok] Done! Modified {}/{} files in {}".format(modified_count, len(html_files), version_name))

if __name__ == '__main__':
    main()
