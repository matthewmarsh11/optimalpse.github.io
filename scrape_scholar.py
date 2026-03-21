"""
Scrape Google Scholar for OptiML group members and categorize papers
into research themes for the website.
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sys

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Group members to search (name as it appears on Google Scholar)
AUTHORS = [
    "Ehecatl Antonio del Rio-Chanona",
    "Thomas Savage",
    "Max Mowbray",
    "Damien van de Berg",
    "Mathias Beham",
    "Panagiotis Petsagkourakis",
    "Zhengang Zhong",
    "Akhil Ahmed",
    "Ilya Orson Sandoval",
    "Frederick Experiment",  # Fred
    "Emma Southall",
    "Yong Lee",
    "David Perez",
    "Abdullah Al-Humaidi",
    "Matthew Sheridan",
    "Samuel Stricker",
    "Laurae Tonetta",
    "Alexander Nies",
    "Sam Stricker",
    "Wojciech Stark",
]

# Research theme keywords for classification
THEME_KEYWORDS = {
    "bo-ddo": [
        "bayesian optim", "derivative-free", "surrogate", "data-driven optim",
        "black box", "black-box", "gaussian process", "experimental design",
        "design of experiment", "catalyst discov", "sample efficient",
    ],
    "rl-control": [
        "reinforcement learning", "process control", "model predictive control",
        "MPC", "policy optim", "safe reinforcement", "constrained reinforcement",
        "dynamic optim", "batch process", "Q-learning", "policy gradient",
        "hierarchical control",
    ],
    "llms": [
        "large language model", "LLM", "language model", "natural language",
        "text mining", "GPT", "transformer", "multi-agent", "AI agent",
        "autonomous agent", "chatbot",
    ],
    "discovery": [
        "molecular", "catalyst", "symbolic regression", "interatomic potential",
        "molecular dynamics", "drug design", "materials discov", "flowsheet",
        "hybrid model", "first-principles", "physics-informed",
        "deep learning", "neural network", "machine learning interatomic",
        "property prediction",
    ],
    "sustainability": [
        "supply chain", "value chain", "sustainability", "decarboni",
        "carbon capture", "energy system", "emission", "green", "renewable",
        "circular economy", "life cycle", "net zero", "climate",
        "sustainable process",
    ],
}


def scrape_scholar(query, num_pages=2):
    """Scrape Google Scholar for a given query."""
    articles = []
    for page in range(num_pages):
        url = f"https://scholar.google.com/scholar?start={page * 10}&q={query}&hl=en&as_sdt=0,5"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 429:
                print(f"  Rate limited. Waiting 60s...")
                time.sleep(60)
                response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                print(f"  Got status {response.status_code}, skipping page {page}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.find_all("div", class_="gs_ri")

            for result in results:
                title_tag = result.find("h3", class_="gs_rt")
                if not title_tag:
                    continue
                title = title_tag.get_text()
                # Clean [PDF], [HTML] etc prefixes
                title = re.sub(r'^\[.*?\]\s*', '', title)

                authors_div = result.find("div", class_="gs_a")
                authors_text = authors_div.get_text() if authors_div else ""
                # Parse "Author1, Author2 - Journal, Year - Publisher"
                parts = authors_text.split(" - ")
                authors = parts[0].strip() if parts else ""
                venue = parts[1].strip() if len(parts) > 1 else ""

                # Extract year from venue
                year_match = re.search(r'(\d{4})', authors_text)
                year = year_match.group(1) if year_match else ""

                link_tag = result.find("a")
                link = link_tag["href"] if link_tag and link_tag.get("href") else ""

                # Snippet for keyword matching
                snippet_div = result.find("div", class_="gs_rs")
                snippet = snippet_div.get_text() if snippet_div else ""

                articles.append({
                    "title": title,
                    "authors": authors,
                    "venue": venue,
                    "year": year,
                    "url": link,
                    "snippet": snippet,
                })

        except Exception as e:
            print(f"  Error on page {page}: {e}")
            continue

        time.sleep(3)  # Be polite

    return articles


def classify_paper(paper):
    """Classify a paper into research themes based on title and snippet."""
    text = (paper["title"] + " " + paper.get("snippet", "") + " " + paper.get("venue", "")).lower()
    themes = []
    for theme, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                themes.append(theme)
                break
    return themes if themes else ["bo-ddo"]  # Default to first theme


def main():
    all_papers = {}  # Deduplicate by title
    theme_papers = {k: [] for k in THEME_KEYWORDS}

    for author in AUTHORS:
        query = f'author:"{author}"'
        print(f"Scraping: {author}...")
        papers = scrape_scholar(query, num_pages=2)
        print(f"  Found {len(papers)} papers")

        for paper in papers:
            # Deduplicate by normalized title
            norm_title = re.sub(r'\W+', ' ', paper["title"].lower()).strip()
            if norm_title not in all_papers:
                all_papers[norm_title] = paper
                themes = classify_paper(paper)
                for theme in themes:
                    theme_papers[theme].append(paper)

        time.sleep(5)  # Longer pause between authors

    # Sort each theme by year (newest first), take top 8
    for theme in theme_papers:
        theme_papers[theme].sort(key=lambda p: p.get("year", "0"), reverse=True)
        theme_papers[theme] = theme_papers[theme][:8]

    # Save as JSON
    output = {k: v for k, v in theme_papers.items()}
    with open("scholar_papers.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary safely
    for theme_key, papers in theme_papers.items():
        sys.stdout.buffer.write(f"\n# Theme: {theme_key} ({len(papers)} papers)\n".encode("utf-8"))
        for p in papers:
            sys.stdout.buffer.write(f"  - {p['title'][:80]}\n".encode("utf-8"))

    sys.stdout.buffer.write(f"\nSaved to scholar_papers.json\n".encode("utf-8"))
    sys.stdout.buffer.write(f"Total unique papers found: {len(all_papers)}\n".encode("utf-8"))


if __name__ == "__main__":
    main()
