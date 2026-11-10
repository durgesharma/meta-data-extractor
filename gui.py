"""
Minimal Web GUI for Meta-D (Web Metadata Extractor & Crawler)
Provides a friendly, zero-friction web dashboard accessible at http://localhost:<port>
"""

from __future__ import annotations

import io
import json
import logging
import sys
import webbrowser
from typing import Any

from flask import Flask, jsonify, render_template_string, request, send_file
from rich.console import Console
from rich.panel import Panel

from extractor import MetadataExtractor

# Suppress standard Flask logging noise in the terminal
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

console = Console()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meta-D | Web Metadata Extractor</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0b0f19;
            --card-bg: #111827;
            --card-border: #1f2937;
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --border-radius: 12px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        body {
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            padding: 2.5rem 1rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container {
            width: 100%;
            max-width: 960px;
        }

        .header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .header h1 {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #60a5fa, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        .header p {
            color: var(--text-muted);
            font-size: 1rem;
        }

        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--border-radius);
            padding: 1.75rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
            margin-bottom: 2rem;
        }

        .form-group {
            margin-bottom: 1.25rem;
        }

        label {
            display: block;
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }

        .input-row {
            display: flex;
            gap: 0.75rem;
        }

        input[type="text"], input[type="number"] {
            width: 100%;
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 8px;
            color: var(--text-main);
            padding: 0.85rem 1.1rem;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        input[type="text"]:focus, input[type="number"]:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
        }

        .btn {
            background-color: var(--accent);
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 0.85rem 1.75rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            white-space: nowrap;
        }

        .btn:hover {
            background-color: var(--accent-hover);
            transform: translateY(-1px);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .btn-outline {
            background-color: transparent;
            border: 1px solid #374151;
            color: var(--text-muted);
        }

        .btn-outline:hover {
            background-color: #1f2937;
            color: var(--text-main);
        }

        .mode-toggle {
            display: flex;
            gap: 1.5rem;
            margin-bottom: 1.25rem;
        }

        .radio-label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
            font-size: 0.95rem;
            color: var(--text-main);
            font-weight: 500;
        }

        .radio-label input {
            accent-color: var(--accent);
            width: 17px;
            height: 17px;
        }

        .crawl-settings {
            display: none;
            background-color: rgba(31, 41, 55, 0.5);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.25rem;
        }

        /* Results Display */
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .results-count {
            font-size: 1.1rem;
            font-weight: 600;
        }

        .export-btns {
            display: flex;
            gap: 0.5rem;
        }

        .result-item {
            background-color: #1a2234;
            border: 1px solid #283548;
            border-radius: 10px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            transition: border-color 0.2s;
        }

        .result-item:hover {
            border-color: #3b82f6;
        }

        .item-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
            margin-bottom: 0.75rem;
        }

        .item-url {
            font-size: 0.9rem;
            color: #60a5fa;
            word-break: break-all;
            text-decoration: none;
            font-weight: 600;
        }

        .item-url:hover {
            text-decoration: underline;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }

        .badge-optimal { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
        .badge-short { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
        .badge-long { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        .badge-missing { background: rgba(107, 114, 128, 0.2); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.4); }
        .badge-status { background: #1f2937; color: #93c5fd; }

        .meta-field {
            margin-top: 0.6rem;
        }

        .meta-label {
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.2rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .meta-value {
            font-size: 0.95rem;
            color: var(--text-main);
            line-height: 1.4;
        }

        .meta-canonical {
            font-size: 0.8rem;
            color: #94a3b8;
            word-break: break-all;
            margin-top: 0.4rem;
        }

        .spinner {
            display: none;
            width: 22px;
            height: 22px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 0.8s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .empty-state {
            text-align: center;
            padding: 3rem 1rem;
            color: var(--text-muted);
        }

        .empty-state svg {
            width: 48px;
            height: 48px;
            margin-bottom: 1rem;
            stroke: #4b5563;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 Meta-D Extractor</h1>
            <p>Simple & Visual Web Metadata Auditor & Website Crawler</p>
        </div>

        <div class="card">
            <form id="extractForm">
                <div class="form-group">
                    <label for="targetUrl">Enter Website URL</label>
                    <div class="input-row">
                        <input type="text" id="targetUrl" placeholder="https://example.com" required autofocus>
                        <button type="submit" class="btn" id="submitBtn">
                            <span class="spinner" id="spinner"></span>
                            <span id="btnText">Extract</span>
                        </button>
                    </div>
                </div>

                <div class="mode-toggle">
                    <label class="radio-label">
                        <input type="radio" name="mode" value="single" checked onchange="toggleMode()">
                        <span>Single Page</span>
                    </label>
                    <label class="radio-label">
                        <input type="radio" name="mode" value="crawl" onchange="toggleMode()">
                        <span>Crawl Entire Website</span>
                    </label>
                </div>

                <div class="crawl-settings" id="crawlSettings">
                    <label for="crawlLimit">Maximum Pages to Crawl</label>
                    <input type="number" id="crawlLimit" value="10" min="1" max="100" style="max-width: 150px;">
                </div>
            </form>
        </div>

        <div id="resultsContainer" style="display: none;">
            <div class="results-header">
                <div class="results-count" id="resultsCount">Results</div>
                <div class="export-btns">
                    <button class="btn btn-outline" onclick="downloadExport('csv')">📥 Download CSV</button>
                    <button class="btn btn-outline" onclick="downloadExport('json')">📥 Download JSON</button>
                </div>
            </div>
            <div id="resultsList"></div>
        </div>

        <div id="emptyState" class="empty-state">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p>Enter any URL above and click <b>Extract</b> to see titles, descriptions, and SEO scores.</p>
        </div>
    </div>

    <script>
        let currentResults = [];

        function toggleMode() {
            const isCrawl = document.querySelector('input[name="mode"]:checked').value === 'crawl';
            document.getElementById('crawlSettings').style.display = isCrawl ? 'block' : 'none';
            document.getElementById('btnText').textContent = isCrawl ? 'Start Crawl' : 'Extract';
        }

        document.getElementById('extractForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const urlInput = document.getElementById('targetUrl').value.trim();
            if (!urlInput) return;

            const isCrawl = document.querySelector('input[name="mode"]:checked').value === 'crawl';
            const limit = parseInt(document.getElementById('crawlLimit').value, 10) || 10;

            const submitBtn = document.getElementById('submitBtn');
            const spinner = document.getElementById('spinner');
            const btnText = document.getElementById('btnText');

            submitBtn.disabled = true;
            spinner.style.display = 'inline-block';
            btnText.textContent = isCrawl ? 'Crawling...' : 'Extracting...';

            try {
                const response = await fetch('/api/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: urlInput, crawl: isCrawl, limit: limit })
                });

                const data = await response.json();
                currentResults = data.results || [];
                renderResults(currentResults);
            } catch (err) {
                alert('Extraction failed: ' + err.message);
            } finally {
                submitBtn.disabled = false;
                spinner.style.display = 'none';
                btnText.textContent = isCrawl ? 'Start Crawl' : 'Extract';
            }
        });

        function getStatusBadge(status) {
            if (status === 'Optimal') return `<span class="badge badge-optimal">${status}</span>`;
            if (status === 'Short') return `<span class="badge badge-short">${status}</span>`;
            if (status && status.includes('Long')) return `<span class="badge badge-long">Too Long</span>`;
            return `<span class="badge badge-missing">Missing</span>`;
        }

        function renderResults(results) {
            const container = document.getElementById('resultsContainer');
            const emptyState = document.getElementById('emptyState');
            const list = document.getElementById('resultsList');
            const count = document.getElementById('resultsCount');

            if (!results || results.length === 0) {
                container.style.display = 'none';
                emptyState.style.display = 'block';
                return;
            }

            emptyState.style.display = 'none';
            container.style.display = 'block';
            count.textContent = `Extracted Metadata (${results.length} page${results.length > 1 ? 's' : ''})`;

            list.innerHTML = results.map(item => `
                <div class="result-item">
                    <div class="item-top">
                        <a href="${item.final_url || item.input_url}" target="_blank" rel="noopener" class="item-url">
                            ${item.final_url || item.input_url}
                        </a>
                        <div>
                            <span class="badge badge-status">${item.status_code || 0} OK</span>
                            <span class="badge badge-status">${item.response_time_ms} ms</span>
                        </div>
                    </div>

                    <div class="meta-field">
                        <div class="meta-label">
                            Page Title 
                            ${getStatusBadge(item.title_status)}
                            <span style="color:#6b7280; font-size:0.75rem;">(${item.title_length || 0} chars)</span>
                        </div>
                        <div class="meta-value">${escapeHtml(item.title) || '<span style="color:#6b7280;">No Title Found</span>'}</div>
                    </div>

                    <div class="meta-field">
                        <div class="meta-label">
                            Meta Description 
                            ${getStatusBadge(item.description_status)}
                            <span style="color:#6b7280; font-size:0.75rem;">(${item.description_length || 0} chars)</span>
                        </div>
                        <div class="meta-value">${escapeHtml(item.description) || '<span style="color:#6b7280;">No Meta Description Found</span>'}</div>
                    </div>

                    ${item.canonical_url ? `
                    <div class="meta-canonical">
                        <b>Canonical:</b> ${escapeHtml(item.canonical_url)}
                    </div>` : ''}
                </div>
            `).join('');
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function downloadExport(type) {
            if (!currentResults.length) return;

            if (type === 'json') {
                const blob = new Blob([JSON.stringify(currentResults, null, 2)], { type: 'application/json' });
                triggerDownload(blob, 'metadata_export.json');
            } else if (type === 'csv') {
                const keys = Object.keys(currentResults[0]);
                const csvRows = [];
                csvRows.push(keys.join(','));

                for (const row of currentResults) {
                    const values = keys.map(k => {
                        const val = (row[k] === null || row[k] === undefined) ? '' : ('' + row[k]);
                        return `"${val.replace(/"/g, '""')}"`;
                    });
                    csvRows.push(values.join(','));
                }
                const blob = new Blob([csvRows.join('\\n')], { type: 'text/csv' });
                triggerDownload(blob, 'metadata_export.csv');
            }
        }

        function triggerDownload(blob, filename) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
"""

def create_app() -> Flask:
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    extractor = MetadataExtractor()

    @app.route("/")
    def index():
        return render_template_string(HTML_TEMPLATE)

    @app.route("/api/extract", methods=["POST"])
    def api_extract():
        data = request.get_json() or {}
        url = data.get("url", "").strip()
        is_crawl = bool(data.get("crawl", False))
        limit = int(data.get("limit", 10))

        if not url:
            return jsonify({"error": "URL is required"}), 400

        if is_crawl:
            results = extractor.crawl_and_extract(url, max_urls=limit)
        else:
            res = extractor.extract(url)
            results = [res]

        return jsonify({"results": [r.to_dict() for r in results]})

    return app


def is_port_in_use(port: int) -> bool:
    """Checks if a local port is already bound by another application."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_available_port(start_port: int) -> int:
    """Finds the first available port starting from start_port."""
    import socket
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return start_port


def start_gui(port: int = 3000) -> None:
    """Launches the minimal Web GUI server on http://localhost:<port>."""
    if is_port_in_use(port):
        alt_port = find_available_port(port + 1)
        console.print(f"[bold yellow]Notice:[/bold yellow] Port {port} is already in use by another app. Automatically using port [bold cyan]{alt_port}[/bold cyan].")
        port = alt_port

    app = create_app()
    url = f"http://localhost:{port}"

    console.print(
        Panel.fit(
            f"[bold green]Meta-D Web GUI is Running![/bold green]\n"
            f"[cyan]Local URL:[/cyan] [bold underline white]{url}[/bold underline white]\n"
            f"[dim]Opening in your default browser... (Press Ctrl+C to stop)[/dim]",
            border_style="green"
        )
    )

    # Open browser automatically after half a second
    def open_browser():
        webbrowser.open_new_tab(url)

    from threading import Timer
    Timer(0.8, open_browser).start()

    try:
        app.run(host="127.0.0.1", port=port, debug=False)
    except Exception as e:
        console.print(f"[bold red]Server error:[/bold red] {e}")


if __name__ == "__main__":
    port_arg = 3000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_arg = int(sys.argv[1])
    start_gui(port_arg)
