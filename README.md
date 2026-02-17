# get-data-from-gee

## HKU Scholars Hub Scraper - 上海风貌别墅

Scrapes papers related to Shanghai heritage villas (上海风貌别墅) from the HKU Scholars Hub (hub.hku.hk).

### Multi-strategy approach

1. **Curated database** - Pre-collected relevant paper handles discovered via search engines
2. **OpenAlex API** - Searches the open academic metadata index for HKU-affiliated papers
3. **Direct scraping** - Scrapes hub.hku.hk search and detail pages (when accessible)
4. **OAI-PMH harvesting** - Harvests metadata via the DSpace OAI-PMH protocol (when accessible)
5. **CrossRef enrichment** - Enriches papers with DOI via the CrossRef API

### Usage

```bash
pip install -r requirements.txt
python3 scrape_hku.py
```

Results are saved to `output/` as both JSON and CSV.

### Search Keywords

- 上海别墅 / 上海风貌 / 上海花园洋房 / 上海里弄 / 上海历史建筑
- Shanghai villa heritage / garden villa / heritage architecture
- Shanghai concession / lane house / lilong / shikumen
- Shanghai French Concession / vernacular architecture / urban conservation