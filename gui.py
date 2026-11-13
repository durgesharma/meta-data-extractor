"""
Minimal Web GUI for Meta-D (Web Metadata Extractor & Crawler)
Provides a friendly, visual dashboard accessible at http://localhost:<port>
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sys
import webbrowser
from typing import Any

# Ensure package directory is in sys.path
_PKG_DIR = str(Path(__file__).resolve().parent)
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

from flask import Flask, Response, jsonify, render_template_string, request
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
    <title>Meta-D | Web Metadata Extractor & Crawler</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
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
            max-width: 980px;
        }

        .header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .header h1 {
            font-size: 2.3rem;
            font-weight: 800;
            background: linear-gradient(135deg, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.4rem;
        }

        .header p {
            color: var(--text-muted);
            font-size: 1.05rem;
        }

        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--border-radius);
            padding: 1.75rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
            margin-bottom: 1.75rem;
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

        .btn-danger {
            background-color: #ef4444;
        }
        .btn-danger:hover {
            background-color: #dc2626;
        }

        .btn-outline {
            background-color: transparent;
            border: 1px solid #374151;
            color: var(--text-muted);
            padding: 0.6rem 1rem;
            font-size: 0.9rem;
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

        /* Live Crawl Indicator Box */
        .live-progress-box {
            display: none;
            background: linear-gradient(135deg, rgba(30, 58, 138, 0.3), rgba(88, 28, 135, 0.3));
            border: 1px solid rgba(59, 130, 246, 0.4);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            margin-bottom: 1.75rem;
            animation: pulse-glow 2s infinite alternate;
        }

        @keyframes pulse-glow {
            0% { box-shadow: 0 0 10px rgba(59, 130, 246, 0.2); }
            100% { box-shadow: 0 0 20px rgba(168, 85, 247, 0.3); }
        }

        .progress-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.8rem;
        }

        .progress-status {
            font-size: 1.05rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .pulsing-dot {
            width: 10px;
            height: 10px;
            background-color: #10b981;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #10b981;
            animation: blink 1s infinite alternate;
        }

        @keyframes blink {
            from { opacity: 0.4; }
            to { opacity: 1; }
        }

        .progress-bar-bg {
            width: 100%;
            height: 8px;
            background-color: #1f2937;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 0.8rem;
        }

        .progress-bar-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #3b82f6, #a855f7);
            border-radius: 4px;
            transition: width 0.3s ease;
        }

        .current-scanning-url {
            font-size: 0.85rem;
            color: #93c5fd;
            word-break: break-all;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* KPI Dashboard Cards */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1.75rem;
        }

        .kpi-card {
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--border-radius);
            padding: 1.25rem;
            text-align: center;
        }

        .kpi-title {
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.35rem;
        }

        .kpi-value {
            font-size: 1.8rem;
            font-weight: 800;
            color: #ffffff;
        }

        .kpi-sub {
            font-size: 0.8rem;
            color: #9ca3af;
            margin-top: 0.2rem;
        }

        /* Results Display */
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 0.75rem;
        }

        .results-count {
            font-size: 1.15rem;
            font-weight: 700;
        }

        .export-btns {
            display: flex;
            gap: 0.5rem;
        }

        .result-item {
            background-color: #111827;
            border: 1px solid #1f2937;
            border-radius: 10px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            transition: border-color 0.2s, transform 0.2s;
            animation: fadeIn 0.3s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
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
            font-size: 0.95rem;
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

        .empty-state {
            text-align: center;
            padding: 3.5rem 1rem;
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
            <p>Live Web Metadata Auditor & Full Website Crawler</p>
        </div>

        <!-- Input Box -->
        <div class="card">
            <form id="extractForm">
                <div class="form-group">
                    <label for="targetUrl">Enter Website URL</label>
                    <div class="input-row">
                        <input type="text" id="targetUrl" placeholder="https://example.com" required autofocus>
                        <button type="submit" class="btn" id="submitBtn">
                            <span id="btnText">Start Extraction</span>
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
                        <span>Crawl Website</span>
                    </label>
                </div>

                <div class="crawl-settings" id="crawlSettings">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
                        <label for="crawlLimit" style="margin:0;">Page Limit</label>
                        <label class="radio-label" style="font-size:0.85rem; color:#60a5fa;">
                            <input type="checkbox" id="crawlAll" onchange="toggleCrawlAll()">
                            <span><b>Whole Website (Unlimited)</b></span>
                        </label>
                    </div>
                    <input type="number" id="crawlLimit" value="15" min="1" max="1000" style="max-width: 150px;">
                    <div id="unlimitedHint" style="display:none; font-size:0.8rem; color:#9ca3af; margin-top:0.4rem;">
                        ⚡ Crawls every discoverable internal link on the entire website until complete.
                    </div>
                </div>
            </form>
        </div>

        <!-- Live Crawl Progress Indicator Box -->
        <div class="live-progress-box" id="liveProgressBox">
            <div class="progress-top">
                <div class="progress-status">
                    <span class="pulsing-dot"></span>
                    <span id="liveStatusText">Crawling in progress...</span>
                </div>
                <button class="btn btn-danger btn-outline" style="padding:0.4rem 0.8rem; font-size:0.8rem;" onclick="stopCrawl()">🛑 Stop Crawl</button>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="progressBarFill"></div>
            </div>
            <div class="current-scanning-url" id="liveCurrentUrl">Starting scanner...</div>
        </div>

        <!-- KPI Dashboard Summary Cards -->
        <div class="kpi-grid" id="kpiGrid" style="display: none;">
            <div class="kpi-card">
                <div class="kpi-title">Pages Scanned</div>
                <div class="kpi-value" id="kpiPages">0</div>
                <div class="kpi-sub">Total pages audited</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Site Links Found</div>
                <div class="kpi-value" id="kpiLinks" style="color: #60a5fa;">0</div>
                <div class="kpi-sub">Unique internal URLs</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">SEO Health</div>
                <div class="kpi-value" id="kpiHealth" style="color: #34d399;">100%</div>
                <div class="kpi-sub">Optimal titles & descriptions</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Avg Latency</div>
                <div class="kpi-value" id="kpiSpeed">0 ms</div>
                <div class="kpi-sub">Server response speed</div>
            </div>
        </div>

        <!-- Results Display -->
        <div id="resultsContainer" style="display: none;">
            <div class="results-header">
                <div class="results-count" id="resultsCount">Extracted Pages</div>
                <div class="export-btns">
                    <button class="btn btn-outline" onclick="downloadExport('csv')">📥 Download CSV</button>
                    <button class="btn btn-outline" onclick="downloadExport('json')">📥 Download JSON</button>
                    <button class="btn btn-outline" id="btnLinksExport" onclick="downloadSiteUrls()" style="display:none;">🔗 All Site URLs (.txt)</button>
                </div>
            </div>
            <div id="resultsList"></div>
        </div>

        <div id="emptyState" class="empty-state">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p>Enter any URL above and click <b>Start Extraction</b> to audit metadata in real time.</p>
        </div>
    </div>

    <script>
        let currentResults = [];
        let currentDiscoveredUrls = [];
        let activeEventSource = null;

        function toggleMode() {
            const isCrawl = document.querySelector('input[name="mode"]:checked').value === 'crawl';
            document.getElementById('crawlSettings').style.display = isCrawl ? 'block' : 'none';
            document.getElementById('btnText').textContent = isCrawl ? 'Start Crawl' : 'Extract';
        }

        function toggleCrawlAll() {
            const isAll = document.getElementById('crawlAll').checked;
            document.getElementById('crawlLimit').disabled = isAll;
            document.getElementById('crawlLimit').style.opacity = isAll ? '0.4' : '1';
            document.getElementById('unlimitedHint').style.display = isAll ? 'block' : 'none';
        }

        function stopCrawl() {
            if (activeEventSource) {
                activeEventSource.close();
                activeEventSource = null;
            }
            document.getElementById('liveProgressBox').style.display = 'none';
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('btnText').textContent = 'Start Crawl';
            updateKpiStats(currentResults, currentDiscoveredUrls);
        }

        document.getElementById('extractForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const urlInput = document.getElementById('targetUrl').value.trim();
            if (!urlInput) return;

            const isCrawl = document.querySelector('input[name="mode"]:checked').value === 'crawl';
            const isAll = document.getElementById('crawlAll').checked;
            const limit = isAll ? 0 : (parseInt(document.getElementById('crawlLimit').value, 10) || 15);

            // Reset view
            currentResults = [];
            currentDiscoveredUrls = [];
            document.getElementById('resultsList').innerHTML = '';
            document.getElementById('emptyState').style.display = 'none';
            document.getElementById('resultsContainer').style.display = 'block';
            document.getElementById('kpiGrid').style.display = 'none';
            document.getElementById('btnLinksExport').style.display = 'none';

            // Show live progress indicator
            const liveBox = document.getElementById('liveProgressBox');
            const liveText = document.getElementById('liveStatusText');
            const liveUrl = document.getElementById('liveCurrentUrl');
            const progressFill = document.getElementById('progressBarFill');
            const submitBtn = document.getElementById('submitBtn');
            const btnText = document.getElementById('btnText');

            liveBox.style.display = 'block';
            progressFill.style.width = '5%';
            liveText.textContent = isCrawl ? (isAll ? 'Crawling Whole Website (Unlimited)...' : `Crawling Website (Target: ${limit} pages)...`) : 'Inspecting Single Page...';
            liveUrl.textContent = `Connecting to ${urlInput}...`;
            submitBtn.disabled = true;
            btnText.textContent = 'Scanning...';

            if (activeEventSource) activeEventSource.close();

            const streamUrl = `/api/crawl-stream?url=${encodeURIComponent(urlInput)}&crawl=${isCrawl}&limit=${limit}`;
            activeEventSource = new EventSource(streamUrl);

            activeEventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === 'fetching') {
                    liveUrl.textContent = `Scanning: ${data.current_url}`;
                    const disc = data.discovered_count || 1;
                    const scan = data.scanned_count || 0;
                    liveText.textContent = `Scanned ${scan} pages • Discovered ${disc} total site links`;
                    if (limit > 0) {
                        const pct = Math.min(100, Math.round((scan / limit) * 100));
                        progressFill.style.width = `${pct}%`;
                    } else {
                        progressFill.style.width = '100%';
                    }
                } else if (data.type === 'page') {
                    currentResults.push(data.page);
                    appendResultItem(data.page);
                    document.getElementById('resultsCount').textContent = `Extracted Metadata (${currentResults.length} page${currentResults.length > 1 ? 's' : ''})`;
                    updateKpiStats(currentResults, currentDiscoveredUrls);
                } else if (data.type === 'done') {
                    currentDiscoveredUrls = data.discovered_urls || [];
                    liveBox.style.display = 'none';
                    submitBtn.disabled = false;
                    btnText.textContent = isCrawl ? 'Start Crawl' : 'Extract';
                    activeEventSource.close();
                    activeEventSource = null;

                    updateKpiStats(currentResults, currentDiscoveredUrls);
                    if (currentDiscoveredUrls.length > 0) {
                        const btnLinks = document.getElementById('btnLinksExport');
                        btnLinks.style.display = 'inline-flex';
                        btnLinks.textContent = `🔗 All ${currentDiscoveredUrls.length} Site URLs (.txt)`;
                    }
                }
            };

            activeEventSource.onerror = (err) => {
                activeEventSource.close();
                activeEventSource = null;
                liveBox.style.display = 'none';
                submitBtn.disabled = false;
                btnText.textContent = isCrawl ? 'Start Crawl' : 'Extract';
                updateKpiStats(currentResults, currentDiscoveredUrls);
            };
        });

        function updateKpiStats(results, discoveredUrls) {
            if (!results || results.length === 0) return;

            document.getElementById('kpiGrid').style.display = 'grid';
            document.getElementById('kpiPages').textContent = results.length;

            const totalLinks = discoveredUrls.length || results.length;
            document.getElementById('kpiLinks').textContent = totalLinks;

            // Health calculation
            const optimalCount = results.filter(r => r.title_status === 'Optimal' && r.description_status === 'Optimal').length;
            const healthPct = Math.round((optimalCount / results.length) * 100);
            const healthElem = document.getElementById('kpiHealth');
            healthElem.textContent = `${healthPct}%`;
            healthElem.style.color = healthPct >= 80 ? '#34d399' : (healthPct >= 50 ? '#fbbf24' : '#f87171');

            // Avg latency
            const totalMs = results.reduce((acc, r) => acc + (r.response_time_ms || 0), 0);
            const avgMs = Math.round(totalMs / results.length);
            document.getElementById('kpiSpeed').textContent = `${avgMs} ms`;
        }

        function getStatusBadge(status) {
            if (status === 'Optimal') return `<span class="badge badge-optimal">${status}</span>`;
            if (status === 'Short') return `<span class="badge badge-short">${status}</span>`;
            if (status && status.includes('Long')) return `<span class="badge badge-long">Too Long</span>`;
            return `<span class="badge badge-missing">Missing</span>`;
        }

        function appendResultItem(item) {
            const list = document.getElementById('resultsList');
            const div = document.createElement('div');
            div.className = 'result-item';

            div.innerHTML = `
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
            `;
            list.appendChild(div);
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function downloadSiteUrls() {
            if (!currentDiscoveredUrls.length) return;
            const content = currentDiscoveredUrls.join('\\n');
            const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
            triggerDownload(blob, 'all_website_urls.txt');
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

    @app.route("/api/crawl-stream")
    def crawl_stream():
        url = request.args.get("url", "").strip()
        is_crawl = request.args.get("crawl", "false").lower() == "true"
        limit = int(request.args.get("limit", 15))

        if not url:
            return jsonify({"error": "URL is required"}), 400

        def event_generator():
            if is_crawl:
                for event in extractor.crawl_stream(url, max_urls=limit):
                    yield f"data: {json.dumps(event)}\\n\\n"
            else:
                res = extractor.extract(url)
                yield f"data: {json.dumps({'type': 'page', 'page': res.to_dict(), 'scanned_count': 1, 'discovered_count': 1})}\\n\\n"
                yield f"data: {json.dumps({'type': 'done', 'total_scanned': 1, 'total_discovered': 1, 'discovered_urls': [res.final_url or res.input_url]})}\\n\\n"

        return Response(event_generator(), mimetype="text/event-stream")

    @app.route("/api/extract", methods=["POST"])
    def api_extract():
        data = request.get_json() or {}
        url = data.get("url", "").strip()
        is_crawl = bool(data.get("crawl", False))
        limit = int(data.get("limit", 15))

        if not url:
            return jsonify({"error": "URL is required"}), 400

        if is_crawl:
            results = extractor.crawl_and_extract(url, max_urls=limit)
            discovered = getattr(extractor, "last_discovered_urls", [])
        else:
            res = extractor.extract(url)
            results = [res]
            discovered = [res.final_url or res.input_url]

        return jsonify({
            "results": [r.to_dict() for r in results],
            "discovered_urls": discovered,
        })

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
