import os
import logging
import html
import base64
from urllib.parse import quote_plus

import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Config from environment
API_ID = int(os.environ.get('API_ID', '0'))
API_HASH = os.environ.get('API_HASH', '')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')  # optional

# GitHub API
GITHUB_SEARCH_URL = 'https://api.github.com/search/repositories'
GITHUB_README_URL = 'https://api.github.com/repos/{full_name}/readme'
HEADERS = {'Accept': 'application/vnd.github.v3+json'}
if GITHUB_TOKEN:
    HEADERS['Authorization'] = f'token {GITHUB_TOKEN}'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Client('ghsearch-bot', api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

RESULTS_PER_PAGE = 5


def github_search(q: str, page: int = 1, per_page: int = RESULTS_PER_PAGE):
    params = {'q': q, 'page': page, 'per_page': per_page, 'sort': 'stars', 'order': 'desc'}
    resp = requests.get(GITHUB_SEARCH_URL, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_readme(full_name: str):
    url = GITHUB_README_URL.format(full_name=full_name)
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if 'content' in data:
        try:
            decoded = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
            return decoded[:1500] + ("..." if len(decoded) > 1500 else "")
        except Exception:
            return None
    return None


def make_repo_line(item):
    name = html.escape(item.get('full_name'))
    desc = item.get('description') or ''
    desc = html.escape(desc)
    stars = item.get('stargazers_count', 0)
    lang = item.get('language') or 'Unknown'
    url = item.get('html_url')
    return f"<b>{name}</b> — {desc}\n⭐ {stars} — {lang}\n{url}"


def make_keyboard(query, page, total_count, items):
    kb = []
    for it in items:
        kb.append([
            InlineKeyboardButton('🌐 Open', url=it['html_url']),
            InlineKeyboardButton('📖 README', callback_data=f'readme|{it["full_name"]}')
        ])
    nav = []
    start_idx = (page - 1) * RESULTS_PER_PAGE + 1
    end_idx = min(start_idx + RESULTS_PER_PAGE - 1, total_count)
    if page > 1:
        nav.append(InlineKeyboardButton('⬅️ Prev', callback_data=f'nav|{quote_plus(query)}|{page-1}'))
    if end_idx < total_count:
        nav.append(InlineKeyboardButton('Next ➡️', callback_data=f'nav|{quote_plus(query)}|{page+1}'))
    if nav:
        kb.append(nav)
    return InlineKeyboardMarkup(kb)


@app.on_message(filters.private & filters.command('start'))
async def start(_, message):
    await message.reply_text('Send /search <query> to search GitHub repositories. Example: /search fastapi')


@app.on_message(filters.private & filters.command('search'))
async def search_cmd(_, message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.reply_text('Usage: /search <query>')
        return
    query = parts[1].strip()
    try:
        data = github_search(query, page=1)
    except Exception as e:
        logger.exception('GitHub search failed')
        await message.reply_text(f'GitHub search failed: {e}')
        return

    total = data.get('total_count', 0)
    items = data.get('items', [])
    if total == 0 or not items:
        await message.reply_text('No repositories found.')
        return

    texts = [make_repo_line(it) for it in items]
    header = f'<b>Results for</b> <code>{html.escape(query)}</code> — {total} repositories\n\n'
    text = header + '\n\n'.join(texts)

    kb = make_keyboard(query, 1, total, items)
    await message.reply_text(text, reply_markup=kb, disable_web_page_preview=True)


@app.on_callback_query()
async def cb_handler(_, query: CallbackQuery):
    data = query.data or ''
    if data.startswith('nav|'):
        try:
            _, q_enc, page_str = data.split('|')
            page = int(page_str)
            q = q_enc.replace('+', ' ')
        except Exception:
            await query.answer('Invalid navigation')
            return
        try:
            data_json = github_search(q, page=page)
        except Exception as e:
            logger.exception('GitHub search failed')
            await query.answer('GitHub search failed')
            return
        total = data_json.get('total_count', 0)
        items = data_json.get('items', [])
        if not items:
            await query.answer('No results on this page')
            return
        texts = [make_repo_line(it) for it in items]
        header = f'<b>Results for</b> <code>{html.escape(q)}</code> — {total} repositories\n\n'
        text = header + '\n\n'.join(texts)
        kb = make_keyboard(q, page, total, items)
        try:
            await query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
            await query.answer()
        except Exception:
            await query.message.reply_text(text, reply_markup=kb, disable_web_page_preview=True)
            await query.answer()
    elif data.startswith('readme|'):
        _, full_name = data.split('|', 1)
        readme = fetch_readme(full_name)
        if not readme:
            await query.answer('README not found', show_alert=True)
            return
        safe_name = html.escape(full_name)
        # Render README using Markdown style
        text = f"*README preview for {safe_name}*\n\n{readme}"
        try:
            await query.message.reply_text(text, disable_web_page_preview=True, parse_mode="Markdown")
        except Exception:
            # fallback to plain text if markdown fails
            await query.message.reply_text(f"README preview for {safe_name}:\n\n{readme}")
        await query.answer()
    else:
        await query.answer()


if __name__ == '__main__':
    app.run()