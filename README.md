# Web Metadata Extractor & Website Crawler (`meta-d`)

A clean, standalone Python CLI tool to extract and audit Canonical URLs, Titles, and Meta Descriptions from any website, with automatic internal crawling.

---

## ⚡ Instant Command: `meta-d` (or `mata-d`)

You can run the tool by typing **`meta-d`** directly in your terminal:

```bash
# 1. Interactive mode
meta-d

# 2. Extract a single URL
meta-d https://www.python.org

# 3. Crawl an entire website (e.g. up to 20 pages)
meta-d https://www.python.org --crawl --limit 20

# 4. Save crawl results to a CSV file
meta-d https://www.python.org --crawl --limit 20 -o results.csv

# 5. Batch extract from a text file of URLs
meta-d -f urls_sample.txt -o batch_results.csv
```

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

## 📄 License

This project is licensed under the [MIT License](LICENSE).
