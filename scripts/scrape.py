#!/usr/bin/env python3

import argparse
import os
import sys
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Set
import time

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Required packages not installed")
    print("Install with: pip install requests beautifulsoup4")
    sys.exit(1)


class SimpleScraper:
    def __init__(self, base_url: str, output_dir: str, max_depth: int = 10, delay: float = 0.5):
        self.base_url = base_url
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.delay = delay
        self.visited: Set[str] = set()
        self.base_domain = urlparse(base_url).netloc

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SimpleScraper/1.0)'
        })

    def normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/') if parsed.path != '/' else parsed.path,
            parsed.params,
            parsed.query,
            ''
        ))
        return normalized

    def is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)

        if parsed.scheme not in ('http', 'https'):
            return False

        if parsed.netloc != self.base_domain:
            return False

        return True

    def get_file_path(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.lstrip('/')

        if not path:
            path = 'index'

        if parsed.query:
            query_part = parsed.query.replace('=', '_').replace('&', '_')

            _, ext = os.path.splitext(path)
            if ext:
                base = path[:-len(ext)]
                path = f"{base}_{query_part}{ext}"
            else:
                path = f"{path}_{query_part}.html"
        else:
            _, ext = os.path.splitext(path)
            if not ext:
                path = f"{path}.html"

        return os.path.join(self.output_dir, self.base_domain, path)

    def save_page(self, url: str, content: bytes) -> None:
        file_path = self.get_file_path(url)
        dir_path = os.path.dirname(file_path)
        os.makedirs(dir_path, exist_ok=True)

        with open(file_path, 'wb') as f:
            f.write(content)

        rel_path = os.path.relpath(file_path, self.output_dir)
        print(f"  [ok] Saved: {rel_path}")

    def extract_links(self, url: str, html: str) -> Set[str]:
        soup = BeautifulSoup(html, 'html.parser')
        links = set()

        for tag in soup.find_all('a', href=True):
            absolute_url = urljoin(url, tag['href'])
            normalized = self.normalize_url(absolute_url)
            if self.is_valid_url(normalized):
                links.add(normalized)

                parsed = urlparse(normalized)
                if 'lang=en' in parsed.query:
                    dutch_query = parsed.query.replace('lang=en', 'lang=nl')
                    dutch_url = urlunparse((
                        parsed.scheme,
                        parsed.netloc,
                        parsed.path,
                        parsed.params,
                        dutch_query,
                        ''
                    ))
                    links.add(dutch_url)
                elif 'lang=nl' in parsed.query:
                    english_query = parsed.query.replace('lang=nl', 'lang=en')
                    english_url = urlunparse((
                        parsed.scheme,
                        parsed.netloc,
                        parsed.path,
                        parsed.params,
                        english_query,
                        ''
                    ))
                    links.add(english_url)

        return links

    def download_assets(self, url: str, html: str) -> None:
        soup = BeautifulSoup(html, 'html.parser')
        assets = []

        for tag in soup.find_all('link', rel='stylesheet', href=True):
            assets.append(urljoin(url, tag['href']))

        for tag in soup.find_all('script', src=True):
            assets.append(urljoin(url, tag['src']))

        for tag in soup.find_all('img', src=True):
            assets.append(urljoin(url, tag['src']))

        for tag in soup.find_all('link', rel='icon', href=True):
            assets.append(urljoin(url, tag['href']))

        for asset_url in assets:
            normalized = self.normalize_url(asset_url)

            if urlparse(normalized).netloc != self.base_domain:
                continue

            if normalized in self.visited:
                continue

            self.visited.add(normalized)

            try:
                time.sleep(self.delay)
                response = self.session.get(normalized, timeout=30)
                response.raise_for_status()

                final_asset_url = self.normalize_url(response.url)
                final_asset_domain = urlparse(final_asset_url).netloc

                if final_asset_domain != self.base_domain:
                    print(f"  [!!] Skipping asset - redirected to different domain: {final_asset_domain}")
                    continue

                self.save_page(final_asset_url, response.content)
            except Exception as e:
                print(f"  [x] Failed to download asset {normalized}: {e}")

    def scrape_page(self, url: str, depth: int = 0) -> None:
        if depth > self.max_depth:
            return

        normalized_url = self.normalize_url(url)

        if normalized_url in self.visited:
            return

        self.visited.add(normalized_url)

        try:
            print(f"[Depth {depth}] Downloading: {normalized_url}")
            time.sleep(self.delay)

            response = self.session.get(normalized_url, timeout=30)
            response.raise_for_status()

            final_url = self.normalize_url(response.url)
            final_domain = urlparse(final_url).netloc

            if final_domain != self.base_domain:
                print(f"  [!!] Skipping - redirected to different domain: {final_domain}")
                return

            content_type = response.headers.get('Content-Type', '')

            self.save_page(final_url, response.content)

            if 'text/html' in content_type:
                html = response.text

                self.download_assets(final_url, html)

                links = self.extract_links(final_url, html)
                for link in links:
                    self.scrape_page(link, depth + 1)

        except requests.exceptions.RequestException as e:
            print(f"  [x] Failed to download {normalized_url}: {e}")
        except Exception as e:
            print(f"  [x] Error processing {normalized_url}: {e}")

    def scrape_404_page(self) -> None:
        print("Attempting to fetch 404 page...")

        not_found_url = urljoin(self.base_url, '/this-page-does-not-exist-404')

        try:
            time.sleep(self.delay)
            response = self.session.get(not_found_url, timeout=30)

            if response.status_code == 404:
                content_type = response.headers.get('Content-Type', '')

                if 'text/html' in content_type:
                    file_path = os.path.join(self.output_dir, self.base_domain, '404.html')
                    dir_path = os.path.dirname(file_path)
                    os.makedirs(dir_path, exist_ok=True)

                    with open(file_path, 'wb') as f:
                        f.write(response.content)

                    rel_path = os.path.relpath(file_path, self.output_dir)
                    print(f"  [ok] Saved 404 page: {rel_path}")

                    html = response.text
                    self.download_assets(not_found_url, html)
                else:
                    print(f"  [!!] 404 page is not HTML (Content-Type: {content_type})")
            else:
                print(f"  [!!] Expected 404 status but got {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"  [x] Failed to fetch 404 page: {e}")
        except Exception as e:
            print(f"  [x] Error processing 404 page: {e}")

        print()

    def scrape(self) -> None:
        print(f"Scraping: {self.base_url}")
        print(f"  Output: {self.output_dir}")
        print(f"  Max depth: {self.max_depth}, delay: {self.delay}s")
        print()

        self.scrape_page(self.base_url)

        self.scrape_404_page()

        print()
        print(f"[ok] Done! Downloaded {len(self.visited)} pages/assets to {self.output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Recursively scrape a static website',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s https://example.com --output ./my-site
  %(prog)s https://example.com --depth 5 --delay 1.0
        """
    )

    parser.add_argument('url', help='URL to scrape')
    parser.add_argument('-o', '--output', default='./downloaded-site',
                        help='Output directory (default: ./downloaded-site)')
    parser.add_argument('-d', '--depth', type=int, default=10,
                        help='Maximum recursion depth (default: 10)')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay between requests in seconds (default: 0.5)')

    args = parser.parse_args()

    scraper = SimpleScraper(args.url, args.output, args.depth, args.delay)

    try:
        scraper.scrape()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        print(f"Downloaded {len(scraper.visited)} pages/assets before interruption")
        sys.exit(1)


if __name__ == '__main__':
    main()
