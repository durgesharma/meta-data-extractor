# Web Metadata Extractor & Website Crawler (MTE)

A clean, standalone Python CLI tool to extract and audit Canonical URLs, Titles, and Meta Descriptions from any website, with automatic internal crawling.

---

## ⚡ Instant Command: `mte` or `MTE`

You can run the tool by typing **`mte`** directly from anywhere in your terminal:

```bash
# Interactive mode
mte

# Extract a single URL
mte https://www.python.org

# Crawl an entire website (discovers up to 20 pages)
mte https://www.python.org --crawl --limit 20

# Export results to CSV
mte https://www.python.org --crawl --limit 15 -o results.csv

# Batch extract from a text file of URLs
mte -f urls_sample.txt -o batch_results.csv
```

---

## 🚀 Installation & Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Register the global `mte` command (optional):**
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
