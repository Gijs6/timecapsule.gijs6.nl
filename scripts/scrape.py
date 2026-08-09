#!/usr/bin/env python3

import argparse
import os
import sys
from urllib.parse import urljoin, urlparse, urlunparse
import time

import requests
from bs4 import BeautifulSoup


def normalize_url(url):
    parsed = urlparse(url)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "/",
            parsed.params,
            parsed.query,
            "",
        )
    )


def is_valid_url(url, base_domain):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and parsed.netloc == base_domain


def get_file_path(url, output_dir, base_domain):
    parsed = urlparse(url)
    path = parsed.path.lstrip("/") or "index"

    if path.endswith("/"):
        path = f"{path}index"

    _, ext = os.path.splitext(path)

    if parsed.query:
        query_part = parsed.query.replace("=", "_").replace("&", "_")
        if ext:
            path = f"{path[: -len(ext)]}_{query_part}{ext}"
        else:
            path = f"{path}_{query_part}.html"
    elif not ext:
        path = f"{path}.html"

    return os.path.join(output_dir, base_domain, path)


def save_page(url, content, output_dir, base_domain):
    file_path = get_file_path(url, output_dir, base_domain)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(content)
    print(f"  [ok] Saved: {os.path.relpath(file_path, output_dir)}")


def extract_links(url, html, base_domain):
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for tag in soup.find_all("a", href=True):
        normalized = normalize_url(urljoin(url, tag["href"]))
        if not is_valid_url(normalized, base_domain):
            continue

        links.add(normalized)

        parsed = urlparse(normalized)
        if "lang=en" in parsed.query:
            links.add(
                urlunparse(
                    parsed._replace(query=parsed.query.replace("lang=en", "lang=nl"))
                )
            )
        elif "lang=nl" in parsed.query:
            links.add(
                urlunparse(
                    parsed._replace(query=parsed.query.replace("lang=nl", "lang=en"))
                )
            )

    return links


def download_assets(url, html, base_domain, output_dir, session, visited, delay):
    soup = BeautifulSoup(html, "html.parser")
    asset_urls = (
        [
            urljoin(url, t["href"])
            for t in soup.find_all("link", rel="stylesheet", href=True)
        ]
        + [urljoin(url, t["src"]) for t in soup.find_all("script", src=True)]
        + [urljoin(url, t["src"]) for t in soup.find_all("img", src=True)]
        + [
            urljoin(url, t["href"])
            for t in soup.find_all("link", rel="icon", href=True)
        ]
    )

    for asset_url in asset_urls:
        normalized = normalize_url(asset_url)
        if urlparse(normalized).netloc != base_domain or normalized in visited:
            continue

        visited.add(normalized)
        try:
            time.sleep(delay)
            response = session.get(normalized, timeout=30)
            response.raise_for_status()

            final_url = normalize_url(response.url)
            if urlparse(final_url).netloc != base_domain:
                print(
                    f"  [!!] Skipping asset - redirected to different domain: {urlparse(final_url).netloc}"
                )
                continue

            save_page(final_url, response.content, output_dir, base_domain)
        except Exception as e:
            print(f"  [x] Failed to download asset {normalized}: {e}")


def scrape_page(
    url, base_domain, output_dir, session, visited, delay, max_depth, depth=0
):
    if depth > max_depth:
        return

    normalized_url = normalize_url(url)
    if normalized_url in visited:
        return

    visited.add(normalized_url)

    try:
        print(f"[Depth {depth}] Downloading: {normalized_url}")
        time.sleep(delay)

        response = session.get(normalized_url, timeout=30)
        response.raise_for_status()

        final_url = normalize_url(response.url)
        if urlparse(final_url).netloc != base_domain:
            print(
                f"  [!!] Skipping - redirected to different domain: {urlparse(final_url).netloc}"
            )
            return

        save_page(final_url, response.content, output_dir, base_domain)

        if "text/html" in response.headers.get("Content-Type", ""):
            download_assets(
                final_url,
                response.text,
                base_domain,
                output_dir,
                session,
                visited,
                delay,
            )
            for link in extract_links(final_url, response.text, base_domain):
                scrape_page(
                    link,
                    base_domain,
                    output_dir,
                    session,
                    visited,
                    delay,
                    max_depth,
                    depth + 1,
                )

    except requests.exceptions.RequestException as e:
        print(f"  [x] Failed to download {normalized_url}: {e}")
    except Exception as e:
        print(f"  [x] Error processing {normalized_url}: {e}")


def scrape_404_page(base_url, base_domain, output_dir, session, visited, delay):
    print("Attempting to fetch 404 page...")
    not_found_url = urljoin(base_url, "/this-page-does-not-exist-404")

    try:
        time.sleep(delay)
        response = session.get(not_found_url, timeout=30)

        if response.status_code != 404:
            print(f"  [!!] Expected 404 status but got {response.status_code}")
            return

        if "text/html" not in response.headers.get("Content-Type", ""):
            print(
                f"  [!!] 404 page is not HTML (Content-Type: {response.headers.get('Content-Type', '')})"
            )
            return

        file_path = os.path.join(output_dir, base_domain, "404.html")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"  [ok] Saved 404 page: {os.path.relpath(file_path, output_dir)}")
        download_assets(
            not_found_url,
            response.text,
            base_domain,
            output_dir,
            session,
            visited,
            delay,
        )

    except requests.exceptions.RequestException as e:
        print(f"  [x] Failed to fetch 404 page: {e}")
    except Exception as e:
        print(f"  [x] Error processing 404 page: {e}")

    print()


def scrape(base_url, output_dir, max_depth, delay):
    base_domain = urlparse(base_url).netloc
    visited = set()
    session = requests.Session()

    print(f"Scraping: {base_url}")
    print(f"  Output: {output_dir}")
    print(f"  Max depth: {max_depth}, delay: {delay}s")
    print()

    scrape_page(base_url, base_domain, output_dir, session, visited, delay, max_depth)
    scrape_404_page(base_url, base_domain, output_dir, session, visited, delay)

    print()
    print(f"[ok] Done! Downloaded {len(visited)} pages/assets to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Recursively scrape a static website")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument(
        "-o",
        "--output",
        default="./downloaded-site",
        help="Output directory (default: ./downloaded-site)",
    )
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=10,
        help="Maximum recursion depth (default: 10)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)",
    )

    args = parser.parse_args()

    try:
        scrape(args.url, args.output, args.depth, args.delay)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
