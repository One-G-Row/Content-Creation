from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate
from django.utils.text import slugify
from django.contrib.auth.hashers import check_password
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.conf import settings
from datetime import datetime
from .models import Post, Event, Project, Volunteer
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import requests
import json
from urllib.parse import urljoin
try:
    import feedparser
except Exception:
    feedparser = None
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

DEFAULT_HASHTAGS = ["#G-TechRising", "#PlantHerTechFuture", "#RuralWomenInTech"]

AFRICAN_NEWS_RSS = [
    "https://techcabal.com/feed/",
    "https://disrupt-africa.com/feed/",
    "https://techpoint.africa/feed/",
    "https://www.itweb.co.za/rss/site/itweb-africa",
    "https://ventureburn.com/feed/",
    "https://cioafrica.com/feeds/all/",
]

INTERNATIONAL_NEWS_RSS = [
    "https://techcrunch.com/tag/africa/feed/",
    "https://thenextweb.com/news/africa/rss",
]

SUCCESS_STORIES_RSS = [
    "https://techcabal.com/tag/funding/feed/",
    "https://disrupt-africa.com/category/startups/funding/feed/",
]

EVENT_SOURCES = [
    {"name": "Eventbrite Africa Tech", "url": "https://www.eventbrite.com/d/africa/technology--events/"},
    {"name": "Eventbrite Free Virtual Tech", "url": "https://www.eventbrite.com/d/online/tech/?price=free"},
]


def _safe_get(obj, *keys, default=None):
    current = obj
    for key in keys:
        try:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                current = getattr(current, key, None)
        except Exception:
            return default
    return current if current is not None else default


def _first_non_empty(*values):
    for v in values:
        if v:
            return v
    return None


def extract_image_from_html(html_text):
    if not BeautifulSoup or not html_text:
        return None
    try:
        soup = BeautifulSoup(html_text, 'html.parser')
        img = soup.find('img')
        if img and img.get('src'):
            return img['src']
    except Exception:
        return None
    return None


def extract_image_from_entry(entry):
    def pick_url(obj):
        if isinstance(obj, dict):
            return obj.get('url')
        if isinstance(obj, list):
            for o in obj:
                if isinstance(o, dict) and o.get('url'):
                    return o['url']
        return None

    base_link = getattr(entry, 'link', '') or _safe_get(entry, 'link', default='') or ''

    # media:content / media:thumbnail
    image = pick_url(getattr(entry, 'media_content', None)) or pick_url(getattr(entry, 'media_thumbnail', None))
    if image:
        return urljoin(base_link, image)

    # enclosures
    enclosures = getattr(entry, 'enclosures', None) or []
    if isinstance(enclosures, list):
        for enc in enclosures:
            enc_type = (enc.get('type') or '') if isinstance(enc, dict) else ''
            href = (enc.get('href') or '') if isinstance(enc, dict) else ''
            if href and enc_type.startswith('image'):
                return urljoin(base_link, href)

    # links with rel='enclosure'
    for l in getattr(entry, 'links', []) or []:
        if isinstance(l, dict) and l.get('rel') == 'enclosure' and (l.get('type') or '').startswith('image') and l.get('href'):
            return urljoin(base_link, l['href'])

    # content[...].value and summary/description <img>
    content_list = getattr(entry, 'content', None)
    if content_list and isinstance(content_list, list):
        for c in content_list:
            src = extract_image_from_html(_safe_get(c, 'value', default=''))
            if src:
                return urljoin(base_link, src)

    summary_html = getattr(entry, 'summary', None) or getattr(entry, 'description', None)
    src = extract_image_from_html(summary_html)
    if src:
        return urljoin(base_link, src)
    return None


def fetch_rss_entries(feed_urls, limit=10):
    items = []
    if not feedparser:
        return items
    for url in feed_urls:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:limit]:
                image_url = extract_image_from_entry(entry)
                items.append({
                    "title": _safe_get(entry, "title", default=""),
                    "link": _safe_get(entry, "link", default=""),
                    "summary": _safe_get(entry, "summary", default="") or _safe_get(entry, "description", default=""),
                    "published": _safe_get(entry, "published", default=""),
                    "image": image_url,
                })
        except Exception:
            continue
    return items


def extract_open_graph(url):
    if not url:
        return {"image": None, "description": None}
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        if not BeautifulSoup:
            return {"image": None, "description": None}
        soup = BeautifulSoup(resp.text, 'html.parser')
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        tw_image = soup.find('meta', attrs={'name': 'twitter:image'})
        tw_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        return {
            "image": (og_image.get('content') if og_image else (tw_image.get('content') if tw_image else None)),
            "description": (og_desc.get('content') if og_desc else (tw_desc.get('content') if tw_desc else None))
        }
    except Exception:
        return {"image": None, "description": None}


def simple_summarize(text, max_chars=300):
    if not text:
        return ""
    text = BeautifulSoup(text, 'html.parser').get_text() if BeautifulSoup else text
    text = ' '.join(text.split())
    return text[:max_chars]


def maybe_openai_summarize(text, max_tokens=100):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return simple_summarize(text)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = (
            "Summarize the following tech news for an African audience in 2-3 sentences. "
            "Keep it neutral, clear, and include the impact.\n\n" + text
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return simple_summarize(text)


@cache_page(60)
def ai_generate(request):
    content_type = request.GET.get('type', 'news')  # news | events | success
    limit = int(request.GET.get('limit', '12'))

    payload = []

    if content_type == 'news':
        entries = fetch_rss_entries(AFRICAN_NEWS_RSS, limit=limit)
        if len(entries) < limit:
            entries += fetch_rss_entries(INTERNATIONAL_NEWS_RSS, limit=max(0, limit - len(entries)))
        for e in entries[:limit]:
            og = extract_open_graph(e.get('link'))
            summary_text = e.get('summary') or og.get('description')
            summarized = maybe_openai_summarize(summary_text or "")
            payload.append({
                "type": "news",
                "title": e.get('title'),
                "summary": summarized,
                "url": e.get('link'),
                "image": _first_non_empty(e.get('image'), og.get('image')),
                "hashtags": DEFAULT_HASHTAGS,
            })

    elif content_type == 'success':
        entries = fetch_rss_entries(SUCCESS_STORIES_RSS, limit=limit)
        for e in entries[:limit]:
            og = extract_open_graph(e.get('link'))
            summary_text = e.get('summary') or og.get('description')
            summarized = maybe_openai_summarize(summary_text or "")
            payload.append({
                "type": "success",
                "title": e.get('title'),
                "summary": summarized,
                "url": e.get('link'),
                "image": _first_non_empty(e.get('image'), og.get('image')),
                "hashtags": DEFAULT_HASHTAGS,
            })

    elif content_type == 'events':
        # Lightweight scraping of listing pages to pick top anchors
        items = []
        for src in EVENT_SOURCES:
            try:
                r = requests.get(src["url"], timeout=8)
                if r.ok and BeautifulSoup:
                    soup = BeautifulSoup(r.text, 'html.parser')
                    for a in soup.select('a[href]'):
                        href = a.get('href')
                        text = a.get_text(strip=True)
                        if not href or not text:
                            continue
                        if 'eventbrite.com' in href and ('event' in href or '/e/' in href):
                            items.append({"title": text[:120], "link": href})
                if len(items) >= limit:
                    break
            except Exception:
                continue
        # Deduplicate by link
        seen = set()
        deduped = []
        for it in items:
            if it['link'] in seen:
                continue
            seen.add(it['link'])
            og = extract_open_graph(it['link'])
            summarized = maybe_openai_summarize(og.get('description') or it['title'])
            deduped.append({
                "type": "event",
                "title": it['title'],
                "summary": summarized,
                "url": it['link'],
                "image": og.get('image'),
                "hashtags": DEFAULT_HASHTAGS,
            })
            if len(deduped) >= limit:
                break
        payload = deduped
    else:
        return JsonResponse({"error": "Invalid type"}, status=400)

    return JsonResponse({"items": payload})


@csrf_exempt
def post_to_linkedin(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=405)
    try:
        data = json.loads(request.body)
        text = data.get('text')
        share_url = data.get('url')
        image_url = data.get('image')
        hashtags = data.get('hashtags') or DEFAULT_HASHTAGS

        access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        org_urn = os.getenv('LINKEDIN_ORG_URN')  # e.g., urn:li:organization:123456
        if not access_token or not org_urn:
            return JsonResponse({"error": "LinkedIn credentials not configured"}, status=500)

        # Build UGC post with optional link; include image URL in text as fallback preview
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json',
        }
        body_text = f"{text}\n\n{image_url or ''}\n\n{' '.join(hashtags)}".strip()
        payload = {
            "author": org_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": body_text[:1200]},
                    "shareMediaCategory": "ARTICLE" if share_url else "NONE",
                    "media": [{
                        "status": "READY",
                        "originalUrl": share_url,
                        "title": {"text": text[:200]}
                    }] if share_url else []
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
        resp = requests.post(
            'https://api.linkedin.com/v2/ugcPosts',
            headers=headers,
            data=json.dumps(payload),
            timeout=15
        )
        if not resp.ok:
            return JsonResponse({"error": "LinkedIn API error", "details": resp.text}, status=resp.status_code)
        return JsonResponse({"message": "Posted to LinkedIn", "result": resp.json()})
    except Exception as e:
        return JsonResponse({"error": f"Failed to post to LinkedIn: {str(e)}"}, status=500)