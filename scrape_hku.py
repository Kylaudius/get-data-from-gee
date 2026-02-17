#!/usr/bin/env python3
"""
HKU Scholars Hub Scraper - 上海风貌别墅相关论文
Scrapes papers related to Shanghai heritage villas from HKU Scholars Hub.

Multi-strategy approach:
1. Curated database of known relevant papers (discovered via search engines)
2. DOI-based metadata enrichment via CrossRef API
3. Direct hub.hku.hk scraping (when network access is available)
4. OAI-PMH metadata harvesting (when network access is available)
5. OpenAlex API for additional paper discovery

Usage:
    python3 scrape_hku.py
"""

import csv
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ── Configuration ──────────────────────────────────────────────────────────

BASE_URL = "https://hub.hku.hk"
SEARCH_URL = f"{BASE_URL}/simple-search"
OAI_URL = f"{BASE_URL}/oai/request"
OUTPUT_DIR = "output"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}

# ── Curated Paper Database ─────────────────────────────────────────────────
# Discovered via web search engines (Google, Bing) querying hub.hku.hk
# All papers are from HKU Scholars Hub and relate to Shanghai heritage/villas

KNOWN_PAPERS = [
    {
        "handle": "10722/330175",
        "title": "Jiaoquan house: a study of an endangered vernacular heritage typology in rural Shanghai",
        "url": "https://hub.hku.hk/handle/10722/330175",
        "collection": "Conservation: Theses; HKU Theses Online",
        "doi": "10.5353/th_991044649848503414",
        "source": "curated",
    },
    {
        "handle": "10722/240588",
        "title": "Housing Shanghai: the evolution of the workers' new village 1920s-2010s",
        "url": "https://hub.hku.hk/handle/10722/240588",
        "collection": "Architecture: Theses; HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/40274",
        "title": "Laszlo E. Hudec and modern architecture in Shanghai",
        "url": "https://hub.hku.hk/handle/10722/40274",
        "doi": "10.5353/th_b3165158",
        "collection": "Architecture: Theses; HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/36472",
        "title": "Real estate development opportunities in Shanghai: a reproduction of the Hong Kong model",
        "url": "https://hub.hku.hk/handle/10722/36472",
        "doi": "10.5353/th_b3125701",
        "collection": "HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/149387",
        "title": "Urban design to lower summertime outdoor temperatures: An empirical study on high-rise housing in Shanghai",
        "url": "https://hub.hku.hk/handle/10722/149387",
        "collection": "Architecture: Journal/Magazine Articles",
        "source": "curated",
    },
    {
        "handle": "10722/322596",
        "title": "Gentrification with Chinese characteristics and 'urban loopholes': the case of the neighborhood-scale transformation in the western end of the former French Concession in Shanghai",
        "url": "https://hub.hku.hk/handle/10722/322596",
        "collection": "Urban Planning & Design: Journal/Magazine Articles",
        "source": "curated",
    },
    {
        "handle": "10722/179560",
        "title": "Designing China's urban future: the Greater Shanghai Plan, 1927-1937",
        "url": "https://hub.hku.hk/handle/10722/179560",
        "collection": "Architecture: Journal/Magazine Articles",
        "source": "curated",
    },
    {
        "handle": "10722/128639",
        "title": "Urban governance and 'creative industry clusters' in Shanghai's urban development",
        "url": "https://hub.hku.hk/handle/10722/128639",
        "doi": "10.5353/th_b4308525",
        "collection": "Urban Planning & Design: Theses; HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/192388",
        "title": "The first step to safeguard our modern architectural heritage: identification, registration and documentation",
        "url": "https://hub.hku.hk/handle/10722/192388",
        "doi": "10.5353/th_b5070006",
        "collection": "Conservation: Theses; HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/355708",
        "title": "Maison de la Chine",
        "url": "https://hub.hku.hk/handle/10722/355708",
        "collection": "Architecture: Theses",
        "source": "curated",
    },
    {
        "handle": "10722/51621",
        "title": "The Shanghai Art College, 1913-1937",
        "url": "https://hub.hku.hk/handle/10722/51621",
        "collection": "HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/180064",
        "title": "The people's way of conservation: the study of Tianzi Fang, Shanghai on its bottom-up revitalization",
        "url": "https://hub.hku.hk/handle/10722/180064",
        "doi": "10.5353/th_b4853932",
        "collection": "Conservation: Theses; HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/265913",
        "title": "The social value of a heritage community: the case of Longchang apartment in Shanghai",
        "url": "https://hub.hku.hk/handle/10722/265913",
        "doi": "10.5353/th_991044060298803414",
        "collection": "Conservation: Theses; HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/60809",
        "title": "Urban Regeneration and Its Realities in Urban China",
        "url": "https://hub.hku.hk/handle/10722/60809",
        "collection": "Urban Planning & Design",
        "source": "curated",
    },
    {
        "handle": "10722/221042",
        "title": "Heritage conservation and environmental sustainability: revisiting the evaluation criteria for heritage buildings",
        "url": "https://hub.hku.hk/handle/10722/221042",
        "doi": "10.5353/th_b5573160",
        "collection": "Conservation: Theses; HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/307550",
        "title": "People, place and space: investigating spatial heritage as a key determinant of spirit of place: the case of Pingjiang Road in Suzhou city",
        "url": "https://hub.hku.hk/handle/10722/307550",
        "collection": "Conservation: Theses; HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/50434",
        "title": "Urban re-development and the preservation of traditional heritage: hutongs in Beijing",
        "url": "https://hub.hku.hk/handle/10722/50434",
        "collection": "HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/134029",
        "title": "Governing urban regeneration: a comparative study of Hong Kong, Singapore and Taipei",
        "url": "https://hub.hku.hk/handle/10722/134029",
        "doi": "10.5353/th_b4501524",
        "collection": "Urban Planning & Design: Theses; HKU Theses Online",
        "source": "curated",
    },
    {
        "handle": "10722/307546",
        "title": "A building in the hills: an undocumented chapter of Hong Kong art deco architecture",
        "url": "https://hub.hku.hk/handle/10722/307546",
        "collection": "Conservation: Theses; HKU Theses Online",
        "source": "curated",
    },
]

# Search queries for hub.hku.hk simple-search and OAI-PMH
SEARCH_QUERIES = [
    "上海 别墅",
    "上海 风貌",
    "上海 花园洋房",
    "上海 里弄",
    "上海 历史建筑",
    "Shanghai villa heritage",
    "Shanghai garden villa",
    "Shanghai heritage architecture",
    "Shanghai concession architecture",
    "Shanghai lane house lilong",
    "Shanghai shikumen",
    "Shanghai housing heritage conservation",
    "Shanghai residential heritage",
    "Shanghai French Concession",
    "Shanghai vernacular architecture",
    "Shanghai urban conservation",
]

# OAI-PMH sets (architecture and conservation related)
OAI_SETS = [
    "com_10722_38535",   # Architecture: Theses
    "com_10722_38526",   # Architecture
    "com_10722_38704",   # Architecture: Journal/Magazine Articles
]

# OpenAlex search queries
OPENALEX_QUERIES = [
    "Shanghai heritage villa architecture",
    "Shanghai conservation residential housing",
    "Shanghai lane house lilong shikumen",
    "Shanghai French Concession architecture",
    "Shanghai vernacular heritage building",
    "Shanghai urban regeneration heritage",
]

# HKU OpenAlex Institution ID
HKU_OPENALEX_ID = "I889458895"


# ── Helper Functions ───────────────────────────────────────────────────────

def make_request(url, params=None, headers=None, max_retries=3, timeout=30):
    """Make HTTP request with retry logic."""
    hdrs = headers or HEADERS
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=hdrs, timeout=timeout)
            if resp.status_code == 200:
                return resp
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
    return None


def is_relevant(text):
    """Check if text contains keywords related to Shanghai heritage/architecture."""
    if not text:
        return False
    text_lower = text.lower()
    shanghai_match = any(kw in text_lower for kw in ["shanghai", "上海"])
    topic_match = any(
        kw in text_lower
        for kw in [
            "villa", "别墅", "洋房", "heritage", "遗产", "风貌", "保护",
            "conservation", "历史", "architecture", "建筑", "housing", "住宅",
            "residential", "lane", "里弄", "弄堂", "lilong", "shikumen",
            "石库门", "concession", "租界", "garden", "花园", "urban", "城市",
            "plan", "design", "typology", "vernacular", "regeneration",
            "historic", "preservation", "renovation", "restoration",
        ]
    )
    return shanghai_match and topic_match


# ── Scraper Class ──────────────────────────────────────────────────────────

class HKUScholarsScraper:
    """Multi-strategy scraper for HKU Scholars Hub papers."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.papers = {}  # handle_or_id -> paper dict
        self.hub_accessible = None  # Will be tested

    def test_hub_access(self):
        """Test if hub.hku.hk is accessible."""
        print("\n[TEST] Checking hub.hku.hk accessibility...")
        resp = make_request(f"{BASE_URL}/", max_retries=1, timeout=10)
        self.hub_accessible = resp is not None
        status = "ACCESSIBLE" if self.hub_accessible else "BLOCKED (403)"
        print(f"  hub.hku.hk is {status}")
        return self.hub_accessible

    # ── Strategy 1: Load curated papers ────────────────────────────────────

    def load_curated_papers(self):
        """Load pre-curated paper records discovered via web search."""
        print(f"\n[CURATED] Loading {len(KNOWN_PAPERS)} known papers...")
        for paper in KNOWN_PAPERS:
            handle = paper["handle"]
            if handle not in self.papers:
                self.papers[handle] = dict(paper)
        print(f"  Loaded {len(KNOWN_PAPERS)} papers")

    # ── Strategy 2: Enrich via CrossRef DOI API ────────────────────────────

    def enrich_via_crossref(self):
        """Enrich papers with DOI via CrossRef API."""
        papers_with_doi = [
            (h, p) for h, p in self.papers.items()
            if p.get("doi") and not p.get("abstract")
        ]
        if not papers_with_doi:
            print("\n[CROSSREF] No papers to enrich via CrossRef")
            return

        print(f"\n[CROSSREF] Enriching {len(papers_with_doi)} papers via CrossRef...")
        for handle, paper in papers_with_doi:
            doi = paper["doi"]
            # Normalize DOI - ensure it doesn't have the URL prefix
            doi_clean = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
            url = f"https://api.crossref.org/works/{doi_clean}"
            resp = make_request(
                url,
                headers={"User-Agent": "HKUScholarsScraper/1.0 (mailto:research@example.com)"},
                max_retries=2,
            )
            if resp:
                try:
                    data = resp.json()
                    work = data.get("message", {})
                    if work.get("abstract"):
                        abstract = work["abstract"]
                        # Strip XML/HTML tags from CrossRef abstract
                        abstract = re.sub(r"<[^>]+>", "", abstract).strip()
                        paper["abstract"] = abstract
                    if work.get("author"):
                        authors = []
                        for a in work["author"]:
                            name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                            if name:
                                authors.append(name)
                        if authors:
                            paper["authors"] = "; ".join(authors)
                    if work.get("published-print", {}).get("date-parts"):
                        parts = work["published-print"]["date-parts"][0]
                        paper["date"] = str(parts[0]) if parts else ""
                    elif work.get("created", {}).get("date-parts"):
                        parts = work["created"]["date-parts"][0]
                        paper["date"] = str(parts[0]) if parts else ""
                    if work.get("subject"):
                        paper["keywords"] = "; ".join(work["subject"])
                    print(f"  [OK] {handle}: enriched via CrossRef")
                except (ValueError, KeyError) as e:
                    print(f"  [ERR] {handle}: CrossRef parse error: {e}")
            else:
                print(f"  [SKIP] {handle}: CrossRef not available")
            time.sleep(0.5)

    # ── Strategy 3: Direct hub.hku.hk scraping ─────────────────────────────

    def scrape_paper_detail(self, handle):
        """Scrape detailed metadata from a paper's detail page."""
        url = f"{BASE_URL}/handle/{handle}"
        resp = make_request(url, max_retries=2)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        detail = {"handle": handle, "url": url}

        # Meta tags (most reliable)
        for meta in soup.select("meta[name]"):
            name = meta.get("name", "").lower()
            content = meta.get("content", "")
            if not content:
                continue
            if name == "dc.title":
                detail["title"] = content
            elif name in ("dc.creator", "dc.contributor.author"):
                existing = detail.get("authors", "")
                detail["authors"] = f"{existing}; {content}" if existing else content
            elif name in ("dcterms.issued", "dc.date.issued"):
                detail["date"] = content
            elif name in ("dcterms.abstract", "dc.description.abstract"):
                detail["abstract"] = content
            elif name == "dc.subject":
                detail.setdefault("keywords", []).append(content)
            elif name == "citation_pdf_url":
                detail["pdf_url"] = content

        # Title from heading
        if "title" not in detail:
            title_el = soup.select_one("h2.page-header, h1.ds-div-head, title")
            if title_el:
                detail["title"] = title_el.get_text(strip=True).replace(" | HKU Scholars Hub", "")

        # Metadata table
        for row in soup.select("table.ds-table tr, table.itemDisplayTable tr"):
            label_el = row.select_one("td.label-cell, td.metadataFieldLabel, th")
            value_el = row.select_one("td.word-break, td.metadataFieldValue, td:last-child")
            if not (label_el and value_el):
                continue
            label = label_el.get_text(strip=True).lower()
            value = value_el.get_text(strip=True)
            if not value:
                continue
            if "advisor" in label or "supervisor" in label:
                detail["advisor"] = value
            elif "department" in label:
                detail["department"] = value
            elif "degree" in label:
                detail["degree"] = value
            elif "doi" in label:
                detail["doi"] = value

        # PDF link
        if "pdf_url" not in detail:
            pdf_link = soup.select_one("a[href$='.pdf'], a.btn-primary[href*='bitstream']")
            if pdf_link:
                detail["pdf_url"] = urljoin(BASE_URL, pdf_link.get("href", ""))

        if isinstance(detail.get("keywords"), list):
            detail["keywords"] = "; ".join(detail["keywords"])

        return detail

    def scrape_search_results(self, query, max_pages=3):
        """Scrape search results from hub.hku.hk simple-search."""
        print(f"  Query: '{query}'")
        page = 0
        total_found = 0

        while page < max_pages:
            params = {
                "query": query, "rpp": 20,
                "sort_by": "score", "order": "desc",
                "start": page * 20,
            }
            resp = make_request(SEARCH_URL, params=params, max_retries=1)
            if not resp:
                break

            soup = BeautifulSoup(resp.text, "lxml")
            # Extract links to paper handles
            found_any = False
            for link in soup.select("a[href*='/handle/10722/']"):
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if title and len(title) > 5:
                    match = re.search(r"handle/(\d+/\d+)", href)
                    if match:
                        handle = match.group(1)
                        if handle not in self.papers:
                            self.papers[handle] = {
                                "handle": handle,
                                "title": title,
                                "url": urljoin(BASE_URL, href),
                                "source": "search",
                            }
                            total_found += 1
                        found_any = True

            if not found_any:
                break
            page += 1
            time.sleep(1)

        if total_found:
            print(f"    -> {total_found} new papers found")

    def scrape_hub_direct(self):
        """Attempt direct scraping of hub.hku.hk."""
        if not self.hub_accessible:
            print("\n[HUB] Skipping direct scraping (hub.hku.hk not accessible)")
            return

        print("\n[HUB] Searching hub.hku.hk directly...")
        for query in SEARCH_QUERIES:
            self.scrape_search_results(query)

        # Enrich papers with detail pages
        papers_to_enrich = [
            h for h, p in self.papers.items()
            if not p.get("abstract")
        ]
        if papers_to_enrich:
            print(f"\n[HUB] Fetching details for {len(papers_to_enrich)} papers...")
            for i, handle in enumerate(papers_to_enrich):
                detail = self.scrape_paper_detail(handle)
                if detail:
                    self.papers[handle].update(detail)
                time.sleep(1)

    # ── Strategy 4: OAI-PMH harvesting ─────────────────────────────────────

    def harvest_oai(self):
        """Harvest metadata via OAI-PMH protocol."""
        if not self.hub_accessible:
            print("\n[OAI-PMH] Skipping (hub.hku.hk not accessible)")
            return

        for set_spec in OAI_SETS:
            print(f"\n[OAI-PMH] Harvesting set: {set_spec}")
            params = {"verb": "ListRecords", "metadataPrefix": "oai_dc", "set": set_spec}
            total = 0
            resumption_token = None

            while total < 500:
                if resumption_token:
                    params = {"verb": "ListRecords", "resumptionToken": resumption_token}

                resp = make_request(OAI_URL, params=params, max_retries=1)
                if not resp:
                    break

                try:
                    root = ET.fromstring(resp.text)
                except ET.ParseError:
                    break

                ns = {
                    "oai": "http://www.openarchives.org/OAI/2.0/",
                    "dc": "http://purl.org/dc/elements/1.1/",
                    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
                }

                records = root.findall(".//oai:record", ns)
                if not records:
                    break

                for record in records:
                    header = record.find("oai:header", ns)
                    metadata = record.find("oai:metadata", ns)
                    if not (header is not None and metadata is not None):
                        continue
                    if header.get("status") == "deleted":
                        continue

                    identifier = header.findtext("oai:identifier", "", ns)
                    handle_match = re.search(r"(\d+/\d+)$", identifier)
                    if not handle_match:
                        continue
                    handle = handle_match.group(1)

                    dc = metadata.find("oai_dc:dc", ns)
                    if dc is None:
                        continue

                    paper = {
                        "handle": handle,
                        "url": f"{BASE_URL}/handle/{handle}",
                        "title": "; ".join(t.text for t in dc.findall("dc:title", ns) if t.text),
                        "authors": "; ".join(c.text for c in dc.findall("dc:creator", ns) if c.text),
                        "abstract": " ".join(d.text for d in dc.findall("dc:description", ns) if d.text),
                        "keywords": "; ".join(s.text for s in dc.findall("dc:subject", ns) if s.text),
                        "source": "oai-pmh",
                    }
                    dates = dc.findall("dc:date", ns)
                    if dates and dates[0].text:
                        paper["date"] = dates[0].text

                    text = f"{paper['title']} {paper['abstract']} {paper['keywords']}"
                    if is_relevant(text) and handle not in self.papers:
                        self.papers[handle] = paper

                    total += 1

                token_el = root.find(".//oai:resumptionToken", ns)
                if token_el is not None and token_el.text:
                    resumption_token = token_el.text
                    time.sleep(1)
                else:
                    break

            print(f"  Processed {total} records")

    # ── Strategy 5: OpenAlex API ───────────────────────────────────────────

    def search_openalex(self):
        """Search OpenAlex for additional HKU papers on Shanghai architecture."""
        print("\n[OPENALEX] Searching for additional papers...")
        total_found = 0

        for query in OPENALEX_QUERIES:
            url = "https://api.openalex.org/works"
            params = {
                "search": query,
                "filter": f"authorships.institutions.lineage:{HKU_OPENALEX_ID}",
                "per_page": 25,
                "sort": "relevance_score:desc",
            }
            resp = make_request(
                url, params=params,
                headers={"User-Agent": "HKUScholarsScraper/1.0"},
                max_retries=2,
            )
            if not resp:
                continue

            try:
                data = resp.json()
            except ValueError:
                continue

            for work in data.get("results", []):
                title = work.get("title", "")
                if not title:
                    continue

                # Check relevance
                abstract_idx = work.get("abstract_inverted_index") or {}
                abstract_text = " ".join(abstract_idx.keys()) if abstract_idx else ""
                text = f"{title} {abstract_text}"
                if not is_relevant(text):
                    continue

                doi = work.get("doi", "")
                openalex_id = work.get("id", "")

                # Use DOI or OpenAlex ID as key
                key = doi or openalex_id
                if not key or key in self.papers:
                    continue

                authors = []
                for a in work.get("authorships", []):
                    name = a.get("author", {}).get("display_name", "")
                    if name:
                        authors.append(name)

                landing_url = ""
                loc = work.get("primary_location") or {}
                if loc:
                    landing_url = loc.get("landing_page_url", "")

                oa_url = work.get("open_access", {}).get("oa_url", "")

                paper = {
                    "title": title,
                    "authors": "; ".join(authors),
                    "date": str(work.get("publication_year", "")),
                    "doi": doi.replace("https://doi.org/", "") if doi else "",
                    "url": landing_url or doi or "",
                    "pdf_url": oa_url or "",
                    "source": "openalex",
                    "openalex_id": openalex_id,
                }

                # Reconstruct abstract from inverted index
                if abstract_idx:
                    try:
                        words = [""] * (max(max(v) for v in abstract_idx.values()) + 1)
                        for word, positions in abstract_idx.items():
                            for pos in positions:
                                words[pos] = word
                        paper["abstract"] = " ".join(w for w in words if w)
                    except (ValueError, TypeError):
                        pass

                source_info = loc.get("source") or {}
                if source_info:
                    paper["journal"] = source_info.get("display_name", "")

                self.papers[key] = paper
                total_found += 1

            time.sleep(0.5)

        print(f"  Found {total_found} additional papers via OpenAlex")

    # ── Save Results ───────────────────────────────────────────────────────

    def save_results(self):
        """Save results to CSV and JSON files."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        papers_list = sorted(
            self.papers.values(),
            key=lambda p: p.get("date", ""),
            reverse=True,
        )

        # Save JSON
        json_path = os.path.join(OUTPUT_DIR, f"hku_shanghai_villas_{timestamp}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(papers_list, f, ensure_ascii=False, indent=2)
        print(f"\n[SAVE] JSON: {json_path} ({len(papers_list)} papers)")

        # Save CSV
        csv_path = os.path.join(OUTPUT_DIR, f"hku_shanghai_villas_{timestamp}.csv")
        fieldnames = [
            "handle", "title", "authors", "date", "department", "degree",
            "advisor", "abstract", "keywords", "collection", "url",
            "pdf_url", "doi", "journal", "source",
        ]
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(papers_list)
        print(f"[SAVE] CSV: {csv_path}")

        # Print summary
        print(f"\n{'='*78}")
        print(f"  RESULTS: {len(papers_list)} papers on 上海风貌别墅 (Shanghai Heritage Villas)")
        print(f"{'='*78}")

        for i, p in enumerate(papers_list, 1):
            title = p.get("title", "No title")
            if len(title) > 85:
                title = title[:82] + "..."
            date = p.get("date", "N/A")
            authors = p.get("authors", "N/A")
            if len(authors) > 50:
                authors = authors[:47] + "..."
            src = p.get("source", "?")

            print(f"\n  {i:2d}. [{date}] {title}")
            print(f"      Authors: {authors}")
            print(f"      URL: {p.get('url', 'N/A')}")
            if p.get("collection"):
                print(f"      Collection: {p['collection']}")
            if p.get("doi"):
                print(f"      DOI: {p['doi']}")
            if p.get("pdf_url"):
                print(f"      PDF: {p['pdf_url']}")
            if p.get("abstract"):
                abstract = p["abstract"]
                if len(abstract) > 150:
                    abstract = abstract[:147] + "..."
                print(f"      Abstract: {abstract}")

        return json_path, csv_path


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 78)
    print("  HKU Scholars Hub Scraper")
    print("  Topic: 上海风貌别墅 (Shanghai Heritage Villas)")
    print("  Strategies: Curated DB + CrossRef + Hub Scraping + OAI-PMH + OpenAlex")
    print("=" * 78)

    scraper = HKUScholarsScraper()

    # Test hub accessibility
    scraper.test_hub_access()

    # Strategy 1: Load curated papers
    scraper.load_curated_papers()

    # Strategy 2: Search OpenAlex for additional papers
    scraper.search_openalex()

    # Strategy 3: Direct hub.hku.hk scraping (if accessible)
    scraper.scrape_hub_direct()

    # Strategy 4: OAI-PMH harvesting (if accessible)
    scraper.harvest_oai()

    # Strategy 5: Enrich via CrossRef DOI
    scraper.enrich_via_crossref()

    # Final filter for relevance (keep curated papers regardless)
    curated_handles = {p["handle"] for p in KNOWN_PAPERS}
    before = len(scraper.papers)
    filtered = {}
    for key, paper in scraper.papers.items():
        text = " ".join([
            paper.get("title", ""),
            paper.get("abstract", ""),
            paper.get("keywords", ""),
        ])
        if is_relevant(text) or paper.get("handle") in curated_handles:
            filtered[key] = paper
    scraper.papers = filtered
    print(f"\n[FILTER] {before} -> {len(filtered)} papers after relevance check")

    # Save results
    scraper.save_results()

    print(f"\nDone! Results saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
