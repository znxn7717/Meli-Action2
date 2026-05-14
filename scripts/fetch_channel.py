import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def parse_message(el):
    msg = {}

    msg_id = el.get("data-post", "")
    msg["id"] = msg_id

    date_el = el.select_one(".tgme_widget_message_date time")
    if date_el:
        msg["date_raw"] = date_el.get("datetime", "")
        try:
            dt = datetime.fromisoformat(msg["date_raw"].replace("Z", "+00:00"))
            msg["date"] = dt.strftime("%H:%M · %d %b %Y")
        except Exception:
            msg["date"] = msg["date_raw"]
    else:
        msg["date"] = ""
        msg["date_raw"] = ""

    views_el = el.select_one(".tgme_widget_message_views")
    msg["views"] = views_el.get_text(strip=True) if views_el else ""

    text_el = el.select_one(".tgme_widget_message_text")
    if text_el:
        msg["text"] = text_el.get_text(separator="\n", strip=True)
    else:
        msg["text"] = ""

    photo_el = el.select_one(".tgme_widget_message_photo_wrap")
    if photo_el:
        style = photo_el.get("style", "")
        m = re.search(r"url\('(.+?)'\)", style)
        msg["photo"] = m.group(1) if m else ""
    else:
        msg["photo"] = ""

    album_photos = el.select(".tgme_widget_message_photo_wrap")
    msg["album"] = []
    for ph in album_photos:
        style = ph.get("style", "")
        m = re.search(r"url\('(.+?)'\)", style)
        if m:
            msg["album"].append(m.group(1))

    video_el = el.select_one("video")
    msg["video"] = video_el.get("src", "") if video_el else ""

    doc_el = el.select_one(".tgme_widget_message_document")
    if doc_el:
        title_el = doc_el.select_one(".tgme_widget_message_document_title")
        extra_el = doc_el.select_one(".tgme_widget_message_document_extra")
        msg["doc_title"] = title_el.get_text(strip=True) if title_el else ""
        msg["doc_extra"] = extra_el.get_text(strip=True) if extra_el else ""
    else:
        msg["doc_title"] = ""
        msg["doc_extra"] = ""

    fwd_el = el.select_one(".tgme_widget_message_forwarded_from")
    msg["forwarded_from"] = fwd_el.get_text(strip=True) if fwd_el else ""

    poll_el = el.select_one(".tgme_widget_message_poll")
    if poll_el:
        q = poll_el.select_one(".tgme_widget_message_poll_question")
        opts = poll_el.select(".tgme_widget_message_poll_option_text")
        msg["poll_question"] = q.get_text(strip=True) if q else ""
        msg["poll_options"] = [o.get_text(strip=True) for o in opts]
    else:
        msg["poll_question"] = ""
        msg["poll_options"] = []

    msg_url_el = el.select_one(".tgme_widget_message_date")
    msg["url"] = msg_url_el.get("href", "") if msg_url_el else ""

    return msg


def fetch_channel(channel, count):
    messages = []
    channel_info = {"name": channel, "title": "", "description": "", "avatar": "", "members": ""}
    base_url = f"https://t.me/s/{channel}"
    before = None

    print(f"[+] Fetching @{channel}")

    while len(messages) < count:
        url = base_url if before is None else f"{base_url}?before={before}"
        print(f"    → {url}")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"[!] Error fetching URL: {e}")
            break

        try:
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            print(f"[!] Error parsing HTML: {e}")
            break

        if before is None:
            try:
                title_el = soup.select_one(".tgme_channel_info_header_title")
                if title_el:
                    channel_info["title"] = title_el.get_text(strip=True)
                desc_el = soup.select_one(".tgme_channel_info_description")
                if desc_el:
                    channel_info["description"] = desc_el.get_text(strip=True)
                avatar_el = soup.select_one(".tgme_page_photo_image img, .tgme_channel_info_header_image img")
                if avatar_el:
                    channel_info["avatar"] = avatar_el.get("src", "")
                members_el = soup.select_one(".tgme_channel_info_counter .counter_value")
                if members_el:
                    channel_info["members"] = members_el.get_text(strip=True)
                print(f"[+] Channel: {channel_info['title']} ({channel_info['members']} members)")
            except Exception as e:
                print(f"[!] Error parsing channel info: {e}")

        try:
            bubbles = soup.select(".tgme_widget_message_wrap")
            if not bubbles:
                print("[!] No messages found.")
                break

            page_messages = []
            for b in bubbles:
                inner = b.select_one(".tgme_widget_message")
                if inner:
                    page_messages.append(parse_message(inner))

            if not page_messages:
                break

            messages = page_messages + messages
            ids = [int(m["id"].split("/")[-1]) for m in page_messages if m["id"]]
            if not ids:
                break
            before = min(ids)

            if len(messages) >= count:
                break

            time.sleep(0.8)
        except Exception as e:
            print(f"[!] Error processing messages: {e}")
            break

    messages = messages[-count:]
    print(f"[+] Got {len(messages)} messages")
    return messages, channel_info


def render_markdown(messages, channel_info, channel, fetch_time):
    lines = []

    title = channel_info.get("title") or f"@{channel}"
    members = channel_info.get("members", "")
    desc = channel_info.get("description", "")
    avatar = channel_info.get("avatar", "")

    # Header
    lines.append(f"<div align=\"center\">")
    if avatar:
        lines.append(f"\n<img src=\"{avatar}\" width=\"80\" height=\"80\" style=\"border-radius:50%\"/>\n")
    lines.append(f"\n# 📡 {title}\n")
    lines.append(f"**@{channel}**")
    if members:
        lines.append(f" · 👥 {members} عضو")
    lines.append(f"\n\n")
    if desc:
        lines.append(f"*{desc}*\n\n")
    lines.append(f"🕐 آپدیت: `{fetch_time}` · 📨 {len(messages)} پیام\n")
    lines.append(f"\n[![باز کردن در تلگرام](https://img.shields.io/badge/باز_کردن_در_تلگرام-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/{channel})\n")
    lines.append(f"\n</div>\n\n")
    lines.append("---\n\n")

    # Messages (newest last)
    for m in messages:
        # Forwarded
        if m.get("forwarded_from"):
            lines.append(f"> ↪ **فوروارد از:** {m['forwarded_from']}\n\n")

        # Album (multiple photos)
        if m.get("album") and len(m["album"]) > 1:
            for i, ph in enumerate(m["album"]):
                lines.append(f"[![photo {i+1}]({ph})]({ph})\n")
            lines.append("\n")
        elif m.get("photo"):
            lines.append(f"[![photo]({m['photo']})]({m['photo']})\n\n")

        # Video
        if m.get("video"):
            lines.append(f"🎬 **[دانلود ویدیو]({m['video']})**\n\n")

        # Document
        if m.get("doc_title"):
            lines.append(f"📄 **{m['doc_title']}** `{m['doc_extra']}`\n\n")

        # Poll
        if m.get("poll_question"):
            lines.append(f"📊 **{m['poll_question']}**\n\n")
            for opt in m.get("poll_options", []):
                lines.append(f"- {opt}\n")
            lines.append("\n")

        # Text
        if m.get("text"):
            text = m["text"]
            lines.append(f"{text}\n\n")

        # Footer
        footer_parts = []
        if m.get("views"):
            footer_parts.append(f"👁 {m['views']}")
        if m.get("date") and m.get("url"):
            footer_parts.append(f"[{m['date']}]({m['url']})")
        elif m.get("date"):
            footer_parts.append(m["date"])

        if footer_parts:
            lines.append(f"<sub>{' · '.join(footer_parts)}</sub>\n\n")

        lines.append("---\n\n")

    return "".join(lines)


def main():
    try:
        parser = argparse.ArgumentParser(description="Fetch Telegram channel messages")
        parser.add_argument("--channel", required=True, help="Channel username (without @)")
        parser.add_argument("--count", type=int, default=100, help="Number of messages to fetch")
        args = parser.parse_args()

        channel = args.channel.lstrip("@").strip()
        if not channel:
            print("[!] Error: Channel name is empty")
            sys.exit(1)

        count = max(10, min(args.count, 200))
        print(f"[*] Parameters: channel=@{channel}, count={count}")

        messages, channel_info = fetch_channel(channel, count)

        if not messages:
            print("[!] No messages fetched.")
            sys.exit(1)

        now = datetime.utcnow()
        fetch_time = now.strftime("%Y-%m-%d %H:%M UTC")
        file_date = now.strftime("%Y-%m-%d_%H-%M")

        md = render_markdown(messages, channel_info, channel, fetch_time)

        out_dir = Path("channels")
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"[+] Created directory: {out_dir}")
        except Exception as e:
            print(f"[!] Error creating directory: {e}")
            sys.exit(1)

        filename = f"{channel}_{file_date}.md"
        out_file = out_dir / filename
        
        try:
            out_file.write_text(md, encoding="utf-8")
            file_size = out_file.stat().st_size
            print(f"[✓] Saved: {out_file} ({file_size} bytes)")
        except Exception as e:
            print(f"[!] Error writing file: {e}")
            sys.exit(1)

    except Exception as e:
        print(f"[!] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
