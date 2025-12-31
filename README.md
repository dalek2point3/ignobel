# Ig Nobel Prize Citation Analysis Dataset

This project creates a dataset to analyze the effects of Ig Nobel prizes on citations to awarded papers.

## Project Goal

Build a dataset with two tables:
1. **Papers Table**: Details of Ig Nobel prize-winning papers and when they received awards
2. **Citations Table**: All papers that cite the focal Ig Nobel prize-winning papers

## Dataset Structure

### Table 1: Awarded Papers (`data/awarded_papers.csv`)
- `paper_id`: Unique identifier
- `year`: Year the Ig Nobel Prize was awarded
- `category`: Prize category (e.g., Physics, Medicine, Chemistry)
- `title`: Paper title or research description
- `authors`: List of authors/winners
- `doi`: Digital Object Identifier (if available)
- `publication_year`: Year the paper was originally published
- `journal`: Journal name (if available)
- `affiliation`: Institution affiliations

### Table 2: Citations (`data/citations.csv`)
- `focal_paper_id`: ID of the Ig Nobel winning paper
- `citing_paper_id`: Unique identifier for citing paper
- `citing_paper_doi`: DOI of citing paper
- `citing_paper_title`: Title of citing paper
- `citation_year`: Year the citation was made
- `authors`: Authors of citing paper
- `journal`: Journal where citing paper was published

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Step 1: Parse Ig Nobel Winners from HTML
```bash
python src/parse_html_winners.py
```

This extracts all 345 Ig Nobel winners (1991-2025) from the saved HTML file into `data/all_ig_nobel_winners.csv`.

**Output**: 345 winners, 64 with DOIs (18.6%), 281 without DOIs

### Step 2: Collect Citations from OpenAlex

**Test mode** (recommended first - processes 10 papers):
```bash
python src/05_collect_citations_openalex.py
```

**Custom test limit** (e.g., 50 papers):
```bash
python src/05_collect_citations_openalex.py --limit 50
```

**Full mode** (all 345 papers):
```bash
python src/05_collect_citations_openalex.py --full
```

**Requirements**:
- Internet connectivity to access OpenAlex API
- No proxy/firewall blocking api.openalex.org
- The script uses polite pool access (9 req/sec) with proper attribution

**How it works**:
- For papers **with DOIs** (64 papers): Direct lookup via OpenAlex DOI endpoint
- For papers **without DOIs** (281 papers): Title-based search with year filtering
- Uses cursor pagination to retrieve all citations (no limits)
- Saves progress incrementally to avoid data loss
- Extracts comprehensive citation metadata including temporal information

**Output**: `output/openalex_citations.csv` and `output/openalex_citations.json`

## Data Sources

- **Ig Nobel Winners**: Saved HTML from [Improbable Research](https://improbable.com/ig/winners/)
- **Citation Data**: [OpenAlex API](https://docs.openalex.org/) - comprehensive, free, open bibliographic database

## Current Status

✅ **Completed**:
- Parsed all 345 Ig Nobel winners (1991-2025) from HTML
- Created comprehensive citation collector for OpenAlex API
- Implemented dual lookup strategy (DOI + title search)
- Built robust error handling and progress tracking
- Test mode validated (code executes correctly)

⏳ **Pending**:
- Run citation collection in environment with internet access
- Generate final dataset with two tables (awarded papers + citations)

## Notes & Limitations

### Paper Coverage
- **Total papers**: 345 (1991-2025)
- **Papers with DOIs**: 64 (18.6%) - can be looked up directly
- **Papers without DOIs**: 281 (81.4%) - require title-based search
- Some years have exactly 10 prizes, a few have 8-9 (typical of Ig Nobel structure)

### Citation Collection
- Requires internet access to OpenAlex API (api.openalex.org)
- Rate limited to ~9 requests/second (polite pool access)
- Title search may have false positives for papers without DOIs
- Estimated runtime for full collection: ~2-3 hours (depends on citation counts)
- Script saves progress incrementally to prevent data loss

### Data Quality
- OpenAlex has excellent coverage of modern papers (2000+)
- Older papers (1991-1999) may have limited citation data
- Some Ig Nobel "papers" are demonstrations or exhibits without formal publications
- Citation data includes pre-award and post-award citations for temporal analysis
