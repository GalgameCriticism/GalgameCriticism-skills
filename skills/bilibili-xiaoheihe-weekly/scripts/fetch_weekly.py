#!/usr/bin/env python3
"""Prepare the latest owned Bilibili collection article for Heybox publishing."""
import argparse
import concurrent.futures
import json
import re
import urllib.parse
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


def prepare(collection, output, title=None):
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
    latest = max(articles, key=lambda item: (item["publish_time"], item["id"]))
    if latest.get("author_uid") != data["author"]["mid"]:
        raise ValueError("Article author does not match the collection author")
    opus = str(latest.get("dyn_id_str") or "")
    if latest.get("type") != 4 or not opus:
        raise ValueError("This helper handles modern opus articles; inspect legacy article HTML separately")
    source_url = f"https://www.bilibili.com/opus/{opus}"
    page = get(source_url)[0].decode("utf-8")
    marker = re.search(r"window\.__INITIAL_STATE__\s*=\s*", page)
    if not marker:
        raise ValueError("No readable initial state; do not substitute a summary for the article")
    state, _ = json.JSONDecoder().raw_decode(page[marker.end():])
    detail = state["detail"]
    if str(detail["basic"]["uid"]) != str(data["author"]["mid"]):
        raise ValueError("Opus author mismatch")
    if str(detail["basic"]["rid_str"]) != str(latest["id"]):
        raise ValueError("Opus article ID mismatch")
    modules = detail["modules"]
    paragraphs = next(m["module_content"]["paragraphs"] for m in modules if m.get("module_content"))
    full_title = next(m["module_title"]["text"] for m in modules if m.get("module_title"))
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

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(download, enumerate(images, 1)))
    result = {
        "schema_version": 1, "collection_id": collection_id, "article_id": latest["id"],
        "opus_id": opus, "source_url": source_url, "source_author": data["author"]["name"],
        "source_author_id": data["author"]["mid"], "publish_time": latest["publish_time"],
        "source_title": full_title, "title": target_title, "blocks": blocks,
    }
    manifest = output / "manifest.json"
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
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
    args = parser.parse_args()
    prepare(args.collection, args.output, args.title)
