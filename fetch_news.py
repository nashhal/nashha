import feedparser
import re
from pathlib import Path
from datetime import datetime

FEEDS = {
    "الجزيرة": "https://www.aljazeera.net/xml/rss/all.xml",
    "فرانس 24": "https://www.france24.com/ar/rss",
    "بي بي سي عربي": "https://feeds.bbci.co.uk/arabic/rss.xml",
    "RT عربي": "https://arabic.rt.com/rss/",
}
KEYWORDS = ["اليمن", "عدن", "الجنوب", "حضرموت", "لحج", "أبين", "شبوة", "المهرة", "سقطرى", "الضالع", "يافع"]


def clean(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def matches(entry):
    text = f"{entry.get('title', '')} {entry.get('summary', '')}"
    return any(k in text for k in KEYWORDS)


def main():
    path = Path("index.html")
    html = path.read_text(encoding="utf-8")
    articles = []
    feed_errors = 0

    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if getattr(feed, "bozo", False) and not feed.entries:
                feed_errors += 1
                continue
            for entry in feed.entries[:30]:
                if matches(entry):
                    articles.append({
                        "title": clean(entry.get("title", "بدون عنوان")),
                        "summary": clean(entry.get("summary", ""))[:220],
                        "source": source,
                        "link": entry.get("link", "#"),
                        "published": entry.get("published", ""),
                    })
        except Exception as exc:
            print(f"Feed error: {source}: {exc}")
            feed_errors += 1

    seen = set()
    unique = []
    for item in articles:
        key = item["title"]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    articles = unique[:12]

    if not articles:
        if feed_errors == len(FEEDS):
            raise RuntimeError("All RSS feeds failed")
        print("No matching headlines found; site left unchanged.")
        return

    now = datetime.now().strftime("%H:%M")
    hero = articles[0]
    ticker = " • ".join(a["title"] for a in articles[:5])

    html = re.sub(r'(<div[^>]*class=["\'][^"\']*breaking[^"\']*["\'][^>]*>).*?(</div>)', rf'\1{ticker}\2', html, count=1, flags=re.S | re.I)

    hero_pattern = r'(<section[^>]*class=["\'][^"\']*hero[^"\']*["\'][^>]*>).*?(</section>)'
    if re.search(hero_pattern, html, flags=re.S | re.I):
        hero_html = f'''<section class="hero"><div><span class="eyebrow">{hero["source"]} • {now}</span><h1>{hero["title"]}</h1><p>{hero["summary"]}</p><a href="{hero["link"]}" target="_blank" rel="noopener">التفاصيل ←</a></div></section>'''
        html = re.sub(hero_pattern, hero_html, html, count=1, flags=re.S | re.I)

    cards = []
    for a in articles[1:9]:
        cards.append(f'''<article class="news-card"><span>{a["source"]} • {now}</span><h3>{a["title"]}</h3><p>{a["summary"]}</p><a href="{a["link"]}" target="_blank" rel="noopener">قراءة الخبر</a></article>''')
    cards_html = "\n".join(cards)
    grid_pattern = r'(<div[^>]*class=["\'][^"\']*(?:news-grid|latest-news)[^"\']*["\'][^>]*>).*?(</div>)'
    html = re.sub(grid_pattern, rf'\1{cards_html}\2', html, count=1, flags=re.S | re.I)

    path.write_text(html, encoding="utf-8")
    print(f"Updated {len(articles)} articles at {now}")


if __name__ == "__main__":
    main()
