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

### Step 1: Scrape Ig Nobel Winners
```bash
python src/01_scrape_winners.py
```

### Step 2: Enrich with Publication Details
```bash
python src/02_enrich_papers.py
```

### Step 3: Collect Citations
```bash
python src/03_collect_citations.py
```

### Step 4: Generate Final Dataset
```bash
python src/04_generate_dataset.py
```

Or run all steps:
```bash
python src/run_all.py
```

## Data Sources

- **Ig Nobel Winners**: [Improbable Research](https://improbable.com/ig/winners/)
- **Wikipedia**: [List of Ig Nobel Prize winners](https://en.wikipedia.org/wiki/List_of_Ig_Nobel_Prize_winners)
- **Citation Data**: CrossRef API, Semantic Scholar API, Google Scholar
- **Recent Winners**:
  - [2024 Ig Nobel Prizes](https://www.chemistryviews.org/2024-ig-nobel-prize-winners/)
  - [2023 Ig Nobel Prizes](https://www.chemistryviews.org/2023-ig-nobel-prizes-honor-unusual-research/)

## Notes

- The scraping process may take time due to rate limits on scholarly APIs
- Some older Ig Nobel prizes (pre-2000s) may not have DOIs readily available
- Citation data completeness depends on availability in scholarly databases
