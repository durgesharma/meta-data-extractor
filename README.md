# Web Metadata Extractor & Website Crawler (`meta-d`)

A clean, standalone Python CLI tool to extract and audit Canonical URLs, Titles, and Meta Descriptions from any website, with automatic internal crawling.

---

## ⚡ Instant Command: `meta-d` (or `mata-d`)

You can run the tool by typing **`meta-d`** directly in your terminal:

```bash
# 1. Launch the Visual Web GUI (on any port you want!)
meta-d 3000

# 2. Interactive CLI mode
meta-d

# 3. Extract a single page
meta-d https://www.python.org

# 4. Crawl the WHOLE website (no --crawl word needed!)
meta-d https://www.python.org --all

# 5. Crawl a specific number of pages (e.g. 20 pages)
meta-d https://www.python.org -l 20

# 6. High-speed crawl with custom hardware workers (e.g. 32 workers)
meta-d https://www.python.org -l 50 -w 32

# 7. Crawl and export ALL discovered website links to a text file
meta-d https://www.python.org --all --links-output all_urls.txt

# 8. Save crawl results to a CSV file
meta-d https://www.python.org -l 20 -o results.csv

# 9. Batch extract from a text file of URLs
meta-d -f urls_sample.txt -o batch_results.csv
```

---

## 🚀 Hardware Acceleration (5x-10x Speedup)

Tasks that previously took **10 minutes now finish in 1-2 minutes** thanks to built-in hardware acceleration:

- **Automatic CPU Core Detection:** Automatically inspects your host machine's hardware (`os.cpu_count()`) and scales parallel scraping workers dynamically (`min(32, max(8, cores * 2))`). On a 12-core machine, **24 parallel threads** run simultaneously.
- **High-Capacity Connection Pooling:** Implements an enterprise `HTTPAdapter(pool_connections=128, pool_maxsize=128)` with exponential backoff retries, eliminating network connection stalls.
- **Concurrent Stream Queue:** Employs thread-safe URL queues and `FIRST_COMPLETED` asynchronous event loops so crawler threads never wait idle while other pages are downloading.
- **Customizable Worker Override:** Want even more speed? Pass `-w` or `--workers` (e.g., `-w 32`) to scale worker threads up to your network's maximum bandwidth.

---

## 🖥️ Minimal Web GUI (For Non-Technical Users)

If someone doesn't want to use the terminal at all, they can simply type:
```bash
meta-d 3000
```
* Automatically starts a local web server at `http://localhost:3000`.
* Opens automatically in their default web browser.
* Clean visual UI to extract single pages or crawl entire sites.
* Live SEO badges (`Optimal`, `Short`, `Too Long`, `Missing`).
* One-click **Download CSV** and **Download JSON** buttons.
* If port 3000 is already in use by another program, it automatically switches to the next free port!

---

## 🚀 Installation & Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Register the global `meta-d` command:**
   ```bash
   pip install -e .
   ```

---

## 🐍 Import into Your Own Python Scripts

```python
from extractor import MetadataExtractor

extractor = MetadataExtractor()

# Single URL
data = extractor.extract("https://www.python.org")
print("Title:", data.title)
print("Description:", data.description)
print("Canonical:", data.canonical_url)

# Crawl an entire website up to 15 pages
results = extractor.crawl_and_extract("https://www.python.org", max_urls=15)
for page in results:
    print(page.final_url, "->", page.title)
```

---

## ❓ Troubleshooting & Common Questions

### Q: PowerShell shows `"The command meta-d was not found, but does exist in the current location. Instead type: .\meta-d"`
* **Why this happens:** Windows PowerShell has a safety policy where it does not run scripts from the current folder unless you add `.\` in front.
* **Fix 1 (Quick):** Run with **`.\`** in front:
  ```powershell
  .\meta-d 3000
  ```
* **Fix 2 (Permanent):** Run `pip install -e .` and **restart your terminal window**. Once reopened, Windows refreshes your PATH and you can type `meta-d` anywhere without `.\`.

### Q: Port 3000 is already in use by another app?
* Meta-D automatically detects port conflicts and switches to the next free port (e.g. `3001`), or you can specify any custom port:
  ```bash
  meta-d 5000
  ```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
