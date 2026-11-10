# Web Metadata Extractor & Website Crawler

A clean, standalone Python tool to extract and audit Canonical URLs, Titles, and Meta Descriptions from any website, with automatic internal crawling.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Extract a Single URL
```bash
python extractor.py https://www.python.org
```

### 3. Crawl a Website (Finds & Extracts Internal Pages)
Specify a seed URL and how many pages to crawl:
```bash
python extractor.py https://www.python.org --crawl --limit 10
```

### 4. Save to CSV or JSON
```bash
# Save crawl results to CSV
python extractor.py https://www.python.org --crawl --limit 20 -o results.csv

# Save single URL to JSON
python extractor.py https://www.python.org -o python_meta.json
```

### 5. Batch Extract from a List of URLs
```bash
python extractor.py -f urls_sample.txt -o batch_results.csv
```

### 6. Interactive Mode
Run with no arguments to enter interactive prompt mode:
```bash
python extractor.py
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
