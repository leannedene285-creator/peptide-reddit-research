# peptide-reddit-research

Read-only research script (PRAW) to categorize public peptide-related discussions on Reddit. Non-commercial.

## What it does

1. `fetch-reddit.py` – searches a small set of subreddits (r/Biohacking, r/Peptides, r/Semaglutide, r/Tirzepatide) for peptide-related keywords over the last 12 months and saves public posts/comments locally. Read-only: no posting, commenting, voting or messaging. Author names are never stored.
2. `label-with-claude.py` – classifies each item offline into purchase motivation, pre-sale concerns and post-sale concerns. Only labels, a short excerpt and metadata are kept.
3. `summarize.py` – aggregates the labels into a Markdown report.

## Data policy

- Stays well under 100 requests/minute with a descriptive User-Agent.
- Raw content is deleted within 48 hours of collection; only aggregated, de-identified results are retained.
- Content removed from Reddit is removed from local data.
- Nothing is republished, sold, or used for model training.

中文使用说明见 [docs/usage-zh.md](docs/usage-zh.md)。
