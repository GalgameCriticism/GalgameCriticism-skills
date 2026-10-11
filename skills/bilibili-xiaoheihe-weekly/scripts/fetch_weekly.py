#!/usr/bin/env python3
"""Prepare a requested issue (or the latest) from a verified Bilibili author."""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import re
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path


def get(url, referer="https://www.bilibili.com/"):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": referer})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read(), response.headers.get_content_type()


def words(nodes):
    result = []
    for node in nodes:
        if node.get("type") != "TEXT_NODE_TYPE_WORD":
            raise ValueError("Unsupported rich-text node; inspect the source before publishing")
        word = node.get("word") or {}
        result.append({"text": word.get("words", ""), "marks": [k for k in ("bold", "italic", "underline", "strikethrough") if (word.get("style") or {}).get(k)]})
    return result


def read_state(page):
    marker = re.search(r"window\.__INITIAL_STATE__\s*=\s*", page)
    if not marker:
        raise ValueError("No readable initial state; do not substitute a summary for the article")
    return json.JSONDecoder().raw_decode(page[marker.end():])[0]


def prepare(collection, output, title=None, issue=None, article_url=None):
    output = Path(output)
    if (output / "manifest.json").exists():
        raise ValueError("Existing manifest is immutable; reuse it or choose a new output directory")
    match = re.search(r"(?:rl)?(\d+)(?:/)?$", collection)
    if not match:
        raise ValueError("Expected a Bilibili readlist URL or numeric collection ID")
    collection_id = int(match.group(1))
    payload = json.loads(get(f"https://api.bilibili.com/x/article/list/web/articles?id={collection_id}")[0])
    if payload.get("code") != 0:
        raise ValueError(f"Collection request failed: code={payload.get('code')}")
    data = payload["data"]
    articles = data.get("articles") or []
    if len(articles) != int(data["list"]["articles_count"]):
        raise ValueError("Incomplete collection response; cannot establish the latest issue")
    if article_url:
        parsed = urllib.parse.urlsplit(article_url)
        if parsed.scheme != "https" or parsed.hostname != "www.bilibili.com":
            raise ValueError("Expected an HTTPS www.bilibili.com article URL")
        article_match = re.fullmatch(r"/read/(?:cv|mobile/)(\d+)/?", parsed.path)
        opus_match = re.fullmatch(r"/opus/(\d+)/?", parsed.path)
        if not article_match and not opus_match:
            raise ValueError("Expected /read/cvID, /read/mobile/ID or /opus/ID")
        latest = {"id": int(article_match.group(1)) if article_match else None,
                  "dyn_id_str": opus_match.group(1) if opus_match else ""}
    elif issue is not None:
        matches = [item for item in articles if re.search(rf"(?:周报|速递)\s*(?:第)?\s*{int(issue)}\s*期", item.get("title", ""))]
        if len(matches) != 1:
            raise ValueError("Requested issue is absent or ambiguous; locate its source and pass --article-url")
        latest = matches[0]
    else:
        if not articles:
            raise ValueError("Collection is empty")
        latest = max(articles, key=lambda item: (item["publish_time"], item["id"]))
    if not article_url and str(latest.get("author_uid")) != str(data["author"]["mid"]):
        raise ValueError("Article author does not match the collection author")
    opus = str(latest.get("dyn_id_str") or "")
    if not article_url and (latest.get("type") != 4 or not opus):
        raise ValueError("This helper handles modern opus articles; inspect legacy article HTML separately")
    source_url = f"https://www.bilibili.com/opus/{opus}" if opus else f"https://www.bilibili.com/read/mobile/{latest['id']}"
    try:
        state = read_state(get(source_url)[0].decode("utf-8"))
    except (ValueError, urllib.error.URLError):
        if not opus or latest.get("id") is None:
            raise
        state = read_state(get(f"https://www.bilibili.com/read/mobile/{latest['id']}")[0].decode("utf-8"))
    detail = state["detail"]
    if str(detail["basic"]["uid"]) != str(data["author"]["mid"]):
        raise ValueError("Opus author mismatch")
    if latest.get("id") is not None and str(detail["basic"]["rid_str"]) != str(latest["id"]):
        raise ValueError("Opus article ID mismatch")
    latest["id"] = int(detail["basic"]["rid_str"])
    actual_opus = str(state.get("id") or opus)
    if not actual_opus.isdigit() or (opus and actual_opus != opus):
        raise ValueError("Missing or mismatched canonical opus ID")
    opus = actual_opus
    source_url = f"https://www.bilibili.com/opus/{opus}"
    modules = detail["modules"]
    paragraphs = next(m["module_content"]["paragraphs"] for m in modules if m.get("module_content"))
    full_title = next(m["module_title"]["text"] for m in modules if m.get("module_title"))
    if issue is not None and not re.search(rf"(?:周报|速递)\s*(?:第)?\s*{int(issue)}\s*期", full_title):
        raise ValueError("Source title does not match the requested issue")
    publish_time = next((m["module_author"].get("pub_ts") for m in modules if m.get("module_author")), None) or latest.get("publish_time")
    if not publish_time:
        raise ValueError("Source publication time is missing")
    target_title = title or full_title[:30]
    if len(target_title) > 30:
        raise ValueError("Heybox article title must be at most 30 characters")
    blocks = []
    if target_title != full_title:
        blocks.append({"type": "paragraph", "nodes": [{"text": full_title, "marks": ["bold"]}]})
    for module in modules:
        top = module.get("module_top") or {}
        for image in ((top.get("display") or {}).get("album") or {}).get("pics", []):
            blocks.append({"type": "image", "url": image["url"], "width": image.get("width"), "height": image.get("height")})
    for paragraph in paragraphs:
        kind = paragraph["para_type"]
        if kind in (1, 8):
            segment = paragraph["text" if kind == 1 else "heading"]
            block = {"type": "paragraph" if kind == 1 else "heading", "nodes": words(segment.get("nodes", []))}
            if kind == 8:
                block["level"] = segment.get("level", 1)
            blocks.append(block)
        elif kind == 2:
            for image in paragraph["pic"]["pics"]:
                blocks.append({"type": "image", "url": image["url"], "width": image.get("width"), "height": image.get("height")})
        elif kind == 3 and paragraph.get("line") == {"pic": None, "line_type": 1}:
            blocks.append({"type": "paragraph", "source_para_type": 3, "nodes": [{"text": "──────────", "marks": []}]})
        else:
            raise ValueError(f"Unsupported paragraph type {kind}; inspect before publishing")
    blocks.append({"type": "paragraph", "nodes": [{"text": f"同步自 {data['author']['name']} B站专栏：{source_url}", "marks": []}]})
    output.mkdir(parents=True, exist_ok=True)
    (output / "images").mkdir(exist_ok=True)
    images = [block for block in blocks if block["type"] == "image"]

    def download(index_and_image):
        index, image = index_and_image
        url = image["url"]
        if url.startswith("//"):
            url = "https:" + url
        if url.startswith("http:"):
            url = "https:" + url[5:]
        host = urllib.parse.urlsplit(url).hostname or ""
        if not host.endswith(".hdslb.com"):
            raise ValueError("Unexpected image host")
        body, mime = get(url, source_url)
        if not mime.startswith("image/"):
            raise ValueError("Image response has an unexpected content type")
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}.get(mime)
        if not suffix:
            raise ValueError("Unsupported image format")
        relative = f"images/{index:03d}{suffix}"
        (output / relative).write_bytes(body)
        image["path"] = relative
        image["url"] = url
        image["order"] = index
        image["sha256"] = hashlib.sha256(body).hexdigest()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(download, enumerate(images, 1)))
    result = {
        "schema_version": 1, "collection_id": collection_id, "article_id": latest["id"],
        "opus_id": opus, "source_url": source_url, "source_author": data["author"]["name"],
        "source_author_id": data["author"]["mid"], "publish_time": int(publish_time),
        "source_title": full_title, "title": target_title, "blocks": blocks,
        "source": "bilibili", "source_id": f"{data['author']['mid']}:{latest['id']}",
        "canonical_url": source_url, "author": {"name": data["author"]["name"], "id": str(data["author"]["mid"])},
        "published_at": datetime.datetime.fromtimestamp(int(publish_time), datetime.timezone.utc).isoformat(),
        "images": images,
    }
    manifest = output / "manifest.json"
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "manifest.sha256").write_text(hashlib.sha256(manifest.read_bytes()).hexdigest() + "\n", encoding="utf-8")
    lines = [f"# {full_title}", ""]
    for block in blocks:
        if block["type"] == "image":
            lines.extend([f"![配图]({block['path']})", ""])
        else:
            text = "".join(n["text"] for n in block["nodes"])
            lines.extend([("#" * min(block.get("level", 0), 6) + " " if block["type"] == "heading" else "") + text, ""])
    (output / "preview.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest), "article_id": latest["id"], "title": target_title, "author": result["source_author"], "images": len(images), "text_blocks": len(blocks) - len(images)}, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--title")
    parser.add_argument("--issue", type=int, help="Select this issue, never silently substitute the latest")
    parser.add_argument("--article-url", help="Explicit article URL when the issue is missing from the collection")
    args = parser.parse_args()
    prepare(args.collection, args.output, args.title, args.issue, args.article_url)
