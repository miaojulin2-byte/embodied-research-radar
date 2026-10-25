# Deployment

Live site: https://miaojulin2-byte.github.io/embodied-research-radar/
Repository: https://github.com/miaojulin2-byte/embodied-research-radar

Verified on 2026-10-25:
- Initial full arXiv pagination and daily update succeeded (run 40168862704); 2,777 indexed records.
- Pages deployment succeeded and the live homepage rendered in Chrome.
- First checkpointed evidence backfill succeeded (run 40169452702).
- The next backfill batch started automatically (run 40171037201); historical evidence completion remains in progress.
- Daily update: 09:17 Asia/Taipei (01:17 UTC). GitHub scheduled execution can be delayed.
- Backlog: batches of at most 25 minutes, automatically chained after progress; retries every two hours.
- Hosting: GitHub Pages, Actions build source. No always-on server is needed.
- The homepage, full index, and individual evidence cards use separate payloads.

API credentials belong in repository Secrets. No credentials are committed. Optional LLM_API_KEY and Semantic Scholar API key are not configured; the extractive pipeline works without them. Unknown or unsupported facts stay unverified.
