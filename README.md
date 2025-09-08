# Telegram GitHub Repo Search Bot

Simple bot that searches GitHub repositories using the GitHub Search API.

Environment variables required:
- API_ID, API_HASH (from my.telegram.org)
- BOT_TOKEN (from @BotFather)
- (optional) GITHUB_TOKEN for higher rate limits

Commands
- /search <query> - search repositories

Features
- Paginated GitHub repo search
- Open repo link buttons
- Fetch README preview button (Markdown rendered, truncated at 1500 chars)

Run locally:
1. pip install -r requirements.txt
2. export API_ID=..., API_HASH=..., BOT_TOKEN=..., (optional) GITHUB_TOKEN=...
3. python bot.py

Notes
- Unauthenticated GitHub API requests are rate limited (60 per hour). Add a GITHUB_TOKEN for 5000/hour.
- README preview is truncated (1500 chars). For full content, fetch from GitHub directly.
- Markdown rendering may fail on unusual READMEs — fallback is plain text.
