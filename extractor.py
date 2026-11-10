"""
Web Metadata Extractor & Crawler
Description: A clean, standalone tool to extract and audit Canonical URLs, Titles,
             and Meta Descriptions, with automatic internal website crawling.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console()

# File extensions to ignore when discovering internal web page links
IGNORED_EXTENSIONS = {
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp",
    ".mp3", ".wav", ".mp4", ".mov", ".avi", ".mkv",
    ".css", ".js", ".json", ".xml", ".woff", ".woff2", ".ttf", ".eot",
    ".exe", ".dmg", ".pkg", ".apk",
}

# Real desktop browser headers to prevent getting 403 bot-blocked
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


@dataclass
class MetadataResult:
    """Stores extracted metadata and SEO evaluations for a URL."""
    input_url: str
    status_code: int = 0
    response_time_ms: float = 0.0
    final_url: str = ""
    canonical_url: str = ""
    og_url: str = ""
    title: str = ""
    title_source: str = ""
    title_length: int = 0
    title_status: str = ""
    description: str = ""
    description_source: str = ""
    description_length: int = 0
    description_status: str = ""
    keywords: str = ""
    robots: str = ""
    og_image: str = ""
    error: str = ""
    discovered_links_count: int = 0
    discovered_links: list[str] = field(default_factory=list, repr=False)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("discovered_links", None)
        return data


class MetadataExtractor:
    """Extracts metadata and crawls internal pages."""

    def __init__(self, headers: dict[str, str] | None = None, timeout: int = 15):
        self.headers = headers or DEFAULT_HEADERS
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    @staticmethod
    def _evaluate_title(title: str) -> str:
        """Assesses title length against standard SEO benchmarks (40-60 characters)."""
        length = len(title)
        if length == 0:
            return "Missing"
        if 40 <= length <= 60:
            return "Optimal"
        if length < 40:
            return "Short"
        return "Long (May Truncate)"

    @staticmethod
    def _evaluate_description(desc: str) -> str:
        """Assesses meta description length against standard SEO benchmarks (120-160 characters)."""
        length = len(desc)
        if length == 0:
            return "Missing"
        if 120 <= length <= 160:
            return "Optimal"
        if length < 120:
            return "Short"
        return "Long (May Truncate)"

    @staticmethod
    def _clean_text(text: str | None) -> str:
        """Strips redundant whitespace and newlines."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalizes URLs for deduplication: standardizes schemes, domains, paths and removes fragments."""
        clean, _ = urldefrag(url)
        parsed = urlparse(clean)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{scheme}://{netloc}{path}{query}"

    @staticmethod
    def _is_valid_internal_url(url: str, base_domain: str) -> bool:
        """Checks if a URL belongs to the target domain and is a web page, not an asset/file."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            netloc = parsed.netloc.lower()
            if netloc != base_domain and not netloc.endswith("." + base_domain):
                return False
            path = parsed.path.lower()
            if any(path.endswith(ext) for ext in IGNORED_EXTENSIONS):
                return False
            return True
        except Exception:
            return False

    @classmethod
    def _extract_internal_links(cls, soup: BeautifulSoup, current_url: str, base_domain: str) -> list[str]:
        """Finds all distinct internal HTML links on the page."""
        links: set[str] = set()
        for a_tag in soup.find_all("a", href=True):
            raw_href = a_tag["href"].strip()
            if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            absolute_url = urljoin(current_url, raw_href)
            normalized = cls._normalize_url(absolute_url)

            if cls._is_valid_internal_url(normalized, base_domain):
                links.add(normalized)
        return sorted(links)

    def extract(self, url: str, extract_links: bool = False, base_domain: str = "") -> MetadataResult:
        """Fetches the page and extracts URL, title, description, and auxiliary metadata."""
        if "://" not in url:
            url = f"https://{url}"

        result = MetadataResult(input_url=url)
        start_time = time.perf_counter()

        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
            )
            result.response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            result.status_code = response.status_code
            result.final_url = response.url

            if response.status_code >= 400:
                result.error = f"HTTP Error {response.status_code}: {response.reason}"
                return result

            content_type = (response.headers.get("Content-Type") or "").lower()
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                result.error = f"Non-HTML content type: {content_type}"
                return result

            # Ensure proper Unicode decoding (prevents replacement chars like  on smart quotes/dashes)
            if response.encoding is None or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding or "utf-8"

            soup = BeautifulSoup(response.text, "html.parser")

            # 1. Meta URLs (Canonical & og:url)
            canonical_tag = soup.find(
                "link",
                rel=lambda val: val and "canonical" in (
                    val.lower() if isinstance(val, str) else " ".join(str(v).lower() for v in val)
                )
            )
            if canonical_tag and canonical_tag.get("href"):
                raw_canonical = canonical_tag.get("href", "").strip()
                result.canonical_url = urljoin(result.final_url, raw_canonical)
            else:
                result.canonical_url = result.final_url

            og_url_tag = soup.find("meta", property=re.compile(r"^og:url$", re.I)) or soup.find("meta", attrs={"name": re.compile(r"^og:url$", re.I)})
            if og_url_tag and og_url_tag.get("content"):
                result.og_url = urljoin(result.final_url, og_url_tag.get("content", "").strip())

            # 2. Page Title with Fallbacks
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                result.title = self._clean_text(title_tag.string)
                result.title_source = "<title>"
            
            if not result.title:
                og_title = soup.find("meta", property=re.compile(r"^og:title$", re.I)) or soup.find("meta", attrs={"name": re.compile(r"^og:title$", re.I)})
                if og_title and og_title.get("content"):
                    result.title = self._clean_text(og_title.get("content"))
                    result.title_source = "og:title"

            if not result.title:
                tw_title = soup.find("meta", attrs={"name": re.compile(r"^twitter:title$", re.I)}) or soup.find("meta", property=re.compile(r"^twitter:title$", re.I))
                if tw_title and tw_title.get("content"):
                    result.title = self._clean_text(tw_title.get("content"))
                    result.title_source = "twitter:title"

            if not result.title:
                h1 = soup.find("h1")
                if h1:
                    result.title = self._clean_text(h1.get_text())
                    result.title_source = "<h1>"

            result.title_length = len(result.title)
            result.title_status = self._evaluate_title(result.title)

            # 3. Meta Description with Fallbacks
            desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
            if desc_tag and desc_tag.get("content"):
                result.description = self._clean_text(desc_tag.get("content"))
                result.description_source = "meta description"

            if not result.description:
                og_desc = soup.find("meta", property=re.compile(r"^og:description$", re.I)) or soup.find("meta", attrs={"name": re.compile(r"^og:description$", re.I)})
                if og_desc and og_desc.get("content"):
                    result.description = self._clean_text(og_desc.get("content"))
                    result.description_source = "og:description"

            if not result.description:
                tw_desc = soup.find("meta", attrs={"name": re.compile(r"^twitter:description$", re.I)}) or soup.find("meta", property=re.compile(r"^twitter:description$", re.I))
                if tw_desc and tw_desc.get("content"):
                    result.description = self._clean_text(tw_desc.get("content"))
                    result.description_source = "twitter:description"

            result.description_length = len(result.description)
            result.description_status = self._evaluate_description(result.description)

            # 4. Auxiliary Metadata
            keywords_tag = soup.find("meta", attrs={"name": re.compile(r"^keywords$", re.I)})
            if keywords_tag and keywords_tag.get("content"):
                result.keywords = self._clean_text(keywords_tag.get("content"))

            robots_tag = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
            if robots_tag and robots_tag.get("content"):
                result.robots = self._clean_text(robots_tag.get("content"))

            og_img = soup.find("meta", property=re.compile(r"^og:image$", re.I)) or soup.find("meta", attrs={"name": re.compile(r"^og:image$", re.I)})
            if og_img and og_img.get("content"):
                result.og_image = urljoin(result.final_url, og_img.get("content", "").strip())

            # 5. Internal Links Discovery (for Crawler)
            if extract_links:
                domain_to_match = base_domain or urlparse(result.final_url).netloc.lower()
                discovered = self._extract_internal_links(soup, result.final_url, domain_to_match)
                result.discovered_links = discovered
                result.discovered_links_count = len(discovered)

        except requests.exceptions.RequestException as e:
            result.response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            result.error = f"Network Error: {str(e)}"
        except Exception as e:
            result.response_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            result.error = f"Parsing Error: {str(e)}"

        return result

    def extract_batch(self, urls: list[str], max_workers: int = 5) -> list[MetadataResult]:
        """Extracts metadata concurrently from a list of URLs."""
        results: list[MetadataResult] = []
        cleaned_urls = [u.strip() for u in urls if u.strip()]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(f"Extracting metadata from {len(cleaned_urls)} URLs...", total=len(cleaned_urls))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {executor.submit(self.extract, url): url for url in cleaned_urls}
                for future in as_completed(future_to_url):
                    try:
                        res = future.result()
                        results.append(res)
                    except Exception as e:
                        url = future_to_url[future]
                        res = MetadataResult(input_url=url, error=str(e))
                        results.append(res)
                    progress.advance(task)

        # Retain original order
        order_map = {url: i for i, url in enumerate(cleaned_urls)}
        results.sort(key=lambda r: order_map.get(r.input_url, 99999))
        return results

    def crawl_and_extract(
        self,
        seed_url: str,
        max_urls: int = 15,
        delay: float = 0.05,
    ) -> list[MetadataResult]:
        """
        Crawls a website starting from a seed URL, discovers all internal links,
        and extracts metadata from up to max_urls pages.
        """
        if "://" not in seed_url:
            seed_url = f"https://{seed_url}"

        seed_url = self._normalize_url(seed_url)
        parsed_seed = urlparse(seed_url)
        base_domain = parsed_seed.netloc.lower()

        visited_urls: set[str] = set()
        queued_urls: set[str] = {seed_url}
        queue: deque[str] = deque([seed_url])
        results: list[MetadataResult] = []

        console.print(
            f"[bold cyan]Crawling domain:[/bold cyan] [green]{base_domain}[/green] "
            f"(Target limit: [bold yellow]{max_urls}[/bold yellow] pages)"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed}/{task.total} URLs[/cyan]"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Crawling {base_domain}...", total=max_urls)

            while queue and len(results) < max_urls:
                current_url = queue.popleft()
                norm_current = self._normalize_url(current_url)
                if norm_current in visited_urls:
                    continue
                visited_urls.add(norm_current)

                res = self.extract(norm_current, extract_links=True, base_domain=base_domain)
                results.append(res)
                progress.advance(task)

                if res.final_url:
                    visited_urls.add(self._normalize_url(res.final_url))

                for link in res.discovered_links:
                    norm_link = self._normalize_url(link)
                    if norm_link not in visited_urls and norm_link not in queued_urls:
                        queued_urls.add(norm_link)
                        queue.append(norm_link)

                if delay > 0 and queue:
                    time.sleep(delay)

        console.print(f"[bold green]Crawl completed![/bold green] Extracted [cyan]{len(results)}[/cyan] pages.")
        return results


def display_single_result(result: MetadataResult) -> None:
    """Renders a single extraction result cleanly in the terminal."""
    if result.error:
        console.print(Panel(f"[bold red]Extraction Failed[/bold red]\n[yellow]URL:[/yellow] {result.input_url}\n[red]Error:[/red] {result.error}", border_style="red"))
        return

    status_color = "green" if result.status_code == 200 else "yellow"
    title_color = "green" if result.title_status == "Optimal" else ("yellow" if result.title_status in ["Short", "Long (May Truncate)"] else "red")
    desc_color = "green" if result.description_status == "Optimal" else ("yellow" if result.description_status in ["Short", "Long (May Truncate)"] else "red")

    table = Table(
        title=f"Metadata Report: [bold cyan]{result.final_url}[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("Property", style="bold", width=18)
    table.add_column("Value", style="none", overflow="fold")
    table.add_column("SEO Assessment / Notes", width=30, overflow="fold")

    table.add_row("HTTP Status", f"[{status_color}]{result.status_code}[/{status_color}]", f"{result.response_time_ms} ms")
    table.add_row("Input URL", result.input_url, "Initial target")
    table.add_row("Final URL", result.final_url, "After redirects" if result.final_url != result.input_url else "Direct")
    table.add_row("Canonical URL", result.canonical_url or "[dim]None[/dim]", "[green]Verified[/green]" if result.canonical_url else "[yellow]Missing[/yellow]")
    if result.og_url:
        table.add_row("og:url", result.og_url, "Social Graph")

    table.add_section()
    table.add_row(
        "Page Title",
        f"[bold]{result.title or '[dim]No Title Found[/dim]'}[/bold]",
        f"[{title_color}]{result.title_status}[/{title_color}] ({result.title_length} chars, from {result.title_source})"
    )

    table.add_section()
    table.add_row(
        "Meta Description",
        result.description or "[dim red]No Meta Description Found[/dim red]",
        f"[{desc_color}]{result.description_status}[/{desc_color}] ({result.description_length} chars, from {result.description_source})"
    )

    if result.robots or result.keywords or result.og_image:
        table.add_section()
        if result.robots:
            table.add_row("Robots Meta", result.robots, "Indexing Directives")
        if result.keywords:
            table.add_row("Keywords", result.keywords, "Legacy Meta")
        if result.og_image:
            table.add_row("og:image", result.og_image, "Social Preview Image")

    console.print(table)


def display_batch_table(results: list[MetadataResult]) -> None:
    """Renders a comparative table for multiple URLs."""
    table = Table(
        title="Batch Extraction Summary",
        show_header=True,
        header_style="bold cyan",
        expand=True,
    )
    table.add_column("#", width=3)
    table.add_column("Status", width=6)
    table.add_column("URL / Canonical", overflow="fold", ratio=2)
    table.add_column("Title (Chars & Status)", overflow="fold", ratio=2)
    table.add_column("Description (Chars & Status)", overflow="fold", ratio=3)

    for i, res in enumerate(results, 1):
        if res.error:
            table.add_row(
                str(i),
                "[red]ERR[/red]",
                f"[yellow]{res.input_url}[/yellow]\n[red]{res.error}[/red]",
                "-",
                "-"
            )
            continue

        status_tag = f"[green]{res.status_code}[/green]" if res.status_code == 200 else f"[yellow]{res.status_code}[/yellow]"
        title_color = "green" if res.title_status == "Optimal" else "yellow"
        desc_color = "green" if res.description_status == "Optimal" else "yellow"

        url_cell = f"{res.final_url}\n[dim cyan]Canonical: {res.canonical_url}[/dim cyan]"
        title_cell = f"{res.title}\n[{title_color}]({res.title_length} chars - {res.title_status})[/{title_color}]"

        desc_cell = f"{res.description or '[dim red]None[/dim red]'}\n[{desc_color}]({res.description_length} chars - {res.description_status})[/{desc_color}]"

        table.add_row(str(i), status_tag, url_cell, title_cell, desc_cell)

    console.print(table)


def save_to_csv(results: list[MetadataResult], output_path: str) -> None:
    """Exports extraction results to a CSV file."""
    if not results:
        return
    fieldnames = list(results[0].to_dict().keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r.to_dict())
    console.print(f"[bold green]Saved to CSV:[/bold green] [cyan]{output_path}[/cyan]")


def save_to_json(results: list[MetadataResult], output_path: str) -> None:
    """Exports extraction results to a JSON file."""
    data = [r.to_dict() for r in results]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    console.print(f"[bold green]Saved to JSON:[/bold green] [cyan]{output_path}[/cyan]")


def save_results(results: list[MetadataResult], output_path: str) -> None:
    """Saves results to CSV or JSON based on file extension."""
    if not results or not output_path:
        return
    if output_path.lower().endswith(".json"):
        save_to_json(results, output_path)
    else:
        save_to_csv(results, output_path if output_path.lower().endswith(".csv") else f"{output_path}.csv")


def main() -> None:
    # 0. Web GUI trigger: e.g. "meta-d 3000", "meta-d gui", "meta-d --gui 5000"
    if len(sys.argv) > 1:
        first_arg = sys.argv[1].strip()
        if first_arg.isdigit():
            from gui import start_gui
            start_gui(port=int(first_arg))
            return
        if first_arg.lower() in ("gui", "--gui", "web", "--web"):
            port = 3000
            if len(sys.argv) > 2 and sys.argv[2].strip().isdigit():
                port = int(sys.argv[2].strip())
            from gui import start_gui
            start_gui(port=port)
            return

    parser = argparse.ArgumentParser(
        description="Meta URL, Title, and Description Extractor & Website Crawler."
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Target web page URL (e.g. https://python.org) or port number for GUI",
    )
    parser.add_argument(
        "-g", "--gui",
        nargs="?",
        const=3000,
        type=int,
        help="Launch minimal Web GUI dashboard on specified port (default: 3000)",
    )
    parser.add_argument(
        "-c", "--crawl",
        action="store_true",
        help="Crawl mode: automatically discover and extract all internal URLs on the website",
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=15,
        help="Maximum number of URLs to crawl and extract (default: 15)",
    )
    parser.add_argument(
        "-f", "--file",
        help="Path to text or CSV file containing a list of URLs (one URL per line)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Export results to a file (.csv or .json)",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=5,
        help="Number of concurrent workers for batch file extraction (default: 5)",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=15,
        help="HTTP request timeout in seconds (default: 15)",
    )

    args = parser.parse_args()

    # If --gui flag was passed
    if args.gui:
        from gui import start_gui
        start_gui(port=args.gui)
        return

    extractor = MetadataExtractor(timeout=args.timeout)

    # 1. URL list from file
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except Exception as e:
            console.print(f"[bold red]Failed to read file {args.file}:[/bold red] {e}")
            sys.exit(1)

        console.print(f"[cyan]Loaded {len(urls)} URLs from {args.file}.[/cyan]")
        results = extractor.extract_batch(urls, max_workers=args.workers)
        display_batch_table(results)

        if args.output:
            save_results(results, args.output)
        return

    # 2. Crawl Mode on a seed URL
    if args.url and args.crawl:
        results = extractor.crawl_and_extract(args.url, max_urls=args.limit)
        display_batch_table(results)

        if args.output:
            save_results(results, args.output)
        return

    # 3. Single URL passed via positional argument
    if args.url:
        result = extractor.extract(args.url)
        display_single_result(result)

        if args.output:
            save_results([result], args.output)
        return

    # 4. Interactive Mode (when run without arguments)
    console.print(
        Panel.fit(
            "[bold cyan]Web Metadata Extractor & Crawler[/bold cyan]\n"
            "• Type a URL to inspect (or '3000' to open the Web GUI)\n"
            "• Automatic Website Crawling (discovers internal links)\n"
            "[dim]Press Enter without text to exit.[/dim]",
            border_style="cyan"
        )
    )

    while True:
        try:
            target_url = console.input("\n[bold yellow]Enter Website or URL[/bold yellow] (or port like '3000', 'q' to quit): ").strip()
            if not target_url or target_url.lower() in ("q", "quit", "exit"):
                console.print("[dim]Exiting extractor. Goodbye![/dim]")
                break

            if target_url.isdigit():
                from gui import start_gui
                start_gui(port=int(target_url))
                break

            crawl_choice = console.input("[cyan]Crawl internal links from this website?[/cyan] (y/N): ").strip().lower()
            if crawl_choice in ("y", "yes"):
                limit_input = console.input("[cyan]How many URLs to extract? [default: 10][/cyan]: ").strip()
                limit = int(limit_input) if limit_input.isdigit() and int(limit_input) > 0 else 10
                results = extractor.crawl_and_extract(target_url, max_urls=limit)
                display_batch_table(results)

                save_choice = console.input("\n[cyan]Export results to CSV or JSON? (enter filename or press Enter to skip)[/cyan]: ").strip()
                if save_choice:
                    save_results(results, save_choice)
            else:
                with console.status(f"[cyan]Fetching and extracting from {target_url}...[/cyan]"):
                    result = extractor.extract(target_url)
                display_single_result(result)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled by user.[/dim]")
            break


if __name__ == "__main__":
    main()
