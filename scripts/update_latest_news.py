#!/usr/bin/env python3

import json
import os
import sys
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen


README_PATH = "profile/README.md"
START_MARKER = "<!-- latest-news:start -->"
END_MARKER = "<!-- latest-news:end -->"


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def fetch_posts(ghost_url: str, content_api_key: str) -> list[dict]:
    base = ghost_url.rstrip("/")
    params = urlencode(
        {
            "key": content_api_key,
            "limit": "5",
            "include": "tags",
            "fields": "title,url,published_at",
            "order": "published_at DESC",
        }
    )
    endpoint = f"{base}/ghost/api/content/posts/?{params}"

    request = Request(
        endpoint, headers={"User-Agent": "mozilla-ai-readme-news-updater"}
    )
    with urlopen(request, timeout=20) as response:
        payload = response.read().decode("utf-8")

    data = json.loads(payload)
    posts = data.get("posts", [])
    if not isinstance(posts, list):
        return []
    return posts[:5]


def format_date(iso_ts: str) -> str:
    if not iso_ts:
        return ""
    normalized = iso_ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return ""
    return dt.strftime("%b %d, %Y")


def build_section(posts: list[dict]) -> str:
    lines = ["## Latest news", START_MARKER]

    if not posts:
        lines.append("- No recent posts available.")
    else:
        for post in posts:
            title = (post.get("title") or "Untitled").strip()
            url = (post.get("url") or "").strip()
            date_label = format_date(post.get("published_at") or "")

            if not url:
                continue
            if date_label:
                lines.append(f"- [{title}]({url}) ({date_label})")
            else:
                lines.append(f"- [{title}]({url})")

    lines.append(END_MARKER)
    return "\n".join(lines)


def replace_or_append_news(readme: str, section: str) -> str:
    start_index = readme.find(START_MARKER)
    end_index = readme.find(END_MARKER)

    if start_index != -1 and end_index != -1 and end_index > start_index:
        block_start = readme.rfind("## Latest news", 0, start_index)
        if block_start == -1:
            block_start = start_index
        block_end = end_index + len(END_MARKER)
        return readme[:block_start].rstrip() + "\n\n" + section + "\n"

    return readme.rstrip() + "\n\n" + section + "\n"


def main() -> None:
    ghost_url = os.environ.get("GHOST_URL", "").strip()
    content_api_key = os.environ.get("GHOST_CONTENT_API_KEY", "").strip()

    if not ghost_url:
        fail("Missing GHOST_URL environment variable")
    if not content_api_key:
        fail("Missing GHOST_CONTENT_API_KEY environment variable")

    posts = fetch_posts(ghost_url, content_api_key)

    with open(README_PATH, "r", encoding="utf-8") as f:
        current = f.read()

    updated = replace_or_append_news(current, build_section(posts))

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"Updated {README_PATH} with {len(posts)} posts")


if __name__ == "__main__":
    main()
