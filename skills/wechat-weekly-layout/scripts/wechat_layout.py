#!/usr/bin/env python3
"""Rebuild a WeChat weekly article from editable content and an inline-style theme."""
import argparse
import copy
import hashlib
import html
import json
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


def load(p):
    return json.loads(Path(p).read_text())


def save(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def paragraphs(docx):
    with ZipFile(docx) as z:
        tree = ET.fromstring(z.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    return [''.join(t.text or '' for t in p.findall('.//w:t', ns)).strip()
            for p in tree.findall('.//w:p', ns)]


def norm(s):
    return re.sub(r'\s+', '', re.sub(r'^（简）', '', s))


def capture(args):
    import requests
    ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0.55'
    r = requests.get(args.url, headers={'User-Agent': ua}, timeout=40)
    r.raise_for_status()
    if 'id="js_content"' not in r.text:
        raise SystemExit('参考文章未读到正文，可能需要微信验证；请使用浏览器保存的 HTML。')
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(r.text)
    print(args.out)


def import_reference(args):
    from bs4 import BeautifulSoup
    from concurrent.futures import ThreadPoolExecutor
    import requests
    from PIL import Image
    root = Path(args.out).resolve()
    (root / 'assets').mkdir(parents=True, exist_ok=True)
    soup = BeautifulSoup(Path(args.html).read_text(), 'html.parser')
    content = soup.select_one('#js_content')
    if content is None or not content.find('strong'):
        raise SystemExit('HTML 中没有可用的文章正文。')
    content = copy.deepcopy(content.section)
    assets = {}
    for img in content.find_all('img'):
        url = img.get('data-src') or img.get('src')
        if not url or not url.startswith('https://mmbiz.qpic.cn/'):
            raise ValueError('本导入器只接受微信图床图片，请检查素材 URL。')
        key = hashlib.sha256(url.encode()).hexdigest()[:16]
        ext = '.jpg' if 'wx_fmt=jpeg' in url else '.png'
        assets[key] = {'url': url, 'path': f'assets/{key}{ext}'}
        img.attrs = {'src': '{{asset:' + key + '}}', 'style': img.get('style', ''), 'width': '100%', 'alt': ''}
    def fetch(pair):
        key, item = pair
        dst = root / item['path']
        if not dst.exists():
            r = requests.get(item['url'], timeout=40)
            r.raise_for_status()
            if not r.headers.get('Content-Type', '').startswith('image/'):
                raise ValueError('图片返回了非图片内容：' + key)
            dst.write_bytes(r.content)
        with Image.open(dst) as image:
            item['width'], item['height'] = image.size
        return key, item
    with ThreadPoolExecutor(max_workers=6) as pool:
        assets = dict(pool.map(fetch, assets.items()))
    for tag in content.find_all():
        for attr in list(tag.attrs):
            if attr in ('class', 'nodeleaf', 'leaf', 'id') or attr.startswith('data-') or attr.startswith('on'):
                del tag[attr]
    for tag in content.find_all(['script', 'iframe', 'mp-style-type']):
        tag.decompose()
    templates = {}
    stories = []
    card_nodes = []
    for title in content.find_all('strong'):
        card = title
        while card.parent and len(card.parent.find_all('strong')) == 1:
            card = card.parent
        card_nodes.append((title, card))
    for i, (title, card) in enumerate(card_nodes, 1):
        title_text = title.get_text(' ', strip=True)
        key = f'news-{i:02d}'
        number = card.find('b')
        sequence = int(number.get_text(strip=True))
        number.clear(); number.append('{{number}}')
        title.clear(); title.append('{{title}}')
        body = next(x for x in card.find_all('section')
                    if re.search(r'font-size:\s*15px', x.get('style', '')) and x.find('p'))
        body_text = [p.get_text('', strip=True) for p in body.find_all('p') if p.get_text(strip=True)]
        body.clear(); body.append('{{body}}')
        image_ids = []
        for img in card.find_all('img'):
            image_ids.append(re.search(r'\{\{asset:(.*?)\}\}', img['src'])[1])
            img['src'] = '{{image:' + str(len(image_ids) - 1) + '}}'
        mode = 'fold' if card.find('animate') else ('swipe' if 'overflow-x: auto' in str(card) else 'none')
        templates[key] = str(card)
        stories.append({'id': key, 'layout': key, 'number': sequence, 'title': title_text,
                        'paragraphs': body_text, 'images': image_ids, 'gallery_mode': mode,
                        'lead': image_ids[0], 'gallery': {'mode': mode, 'images': [k for k in image_ids[1:] if assets[k]['height'] / assets[k]['width'] > .12]}})
        card.replace_with('{{story:' + key + '}}')
    lines = paragraphs(args.docx)
    nonempty = [p for p in lines if p]
    indices = []
    for story in stories:
        matches = [i for i, line in enumerate(lines) if norm(line) == norm(story['title'])]
        if len(matches) != 1:
            raise ValueError('原稿标题无法唯一对应：' + story['title'])
        indices.append(matches[0])
    if indices != sorted(indices):
        raise ValueError('原稿与参考文章的新闻顺序不一致。')
    for i, story in enumerate(stories):
        end = indices[i+1] if i+1 < len(indices) else len(lines)
        story['paragraphs'] = [p for p in lines[indices[i]+1:end] if p and p not in ('新作', '汉化', '周边')]
        if not story['paragraphs']:
            raise ValueError('缺少正文：' + story['title'])
    # Structural anchors come from story order rather than brittle section indices.
    cover = content.find('img')['src']
    image_nodes = content.find_all('img')
    chapter_ids = [re.search(r'\{\{asset:(.*?)\}\}', image_nodes[i]['src'])[1] for i in (1, 2, 3)]
    # The remaining image order is cover / three chapter banners / footer assets.
    chapter_names = ['新作', '汉化', '周边']
    groups = []
    group = None
    for story in stories:
        if story['number'] == 1:
            group = {'name': chapter_names[len(groups)], 'banner': chapter_ids[len(groups)], 'stories': []}
            groups.append(group)
        group['stories'].append(story['id'])
    staff = []
    for p in content.find_all('p'):
        t = p.get_text('', strip=True)
        if t and not t.startswith('Galgame留言板'):
            staff.append('排版：Agent · 参考版式：铃茵' if t.startswith('排版：') else t)
    # Mark this remake's typesetting credit while retaining the original template designer.
    for p in content.find_all('p'):
        if p.get_text('', strip=True).startswith('排版：'):
            p.clear(); p.append('排版：Agent · 参考版式：铃茵')
    recommendations = []
    for a in content.find_all('a'):
        if a.find('img'):
            recommendations.append({'title': a.get_text(' ', strip=True) or '往期推荐', 'url': a['href'], 'image': re.search(r'\{\{asset:(.*?)\}\}', a.img['src'])[1]})
    full_title = (soup.select_one('#activity-name') or soup.title).get_text(' ', strip=True)
    issue_match = re.search(r'(\d+)\s*期', nonempty[0])
    data = {'schema_version': 1, 'issue': issue_match[1] if issue_match else '',
            'title': full_title, 'subtitle': nonempty[1], 'account': 'Galgame批评',
            'source_docx': Path(args.docx).name, 'reference_url': args.url,
            'cover': re.search(r'\{\{asset:(.*?)\}\}', cover)[1],
            'sections': groups, 'stories': stories,
            'staff': staff, 'recommendations': recommendations, 'assets': assets}
    theme = {'shell': str(content), 'cards': templates}
    save(root / 'source/article.json', data)
    save(root / 'source/theme.json', theme)
    print(f'已导入 {len(stories)} 条新闻 / {len(assets)} 张去重图片。')


def init_issue(args):
    import shutil
    from PIL import Image
    root = Path(args.out).resolve()
    if (root / 'source/article.json').exists():
        raise SystemExit('目标已有 source/article.json，请选择新目录或直接编辑现有内容。')
    brand = Path(__file__).parent.parent / 'assets/brand'
    assets = load(brand / 'manifest.json')
    (root / 'assets').mkdir(parents=True, exist_ok=True)
    for item in assets.values():
        shutil.copy2(brand / Path(item['path']).name, root / item['path'])
    cover_path = Path(args.cover).resolve()
    key = hashlib.sha256(cover_path.read_bytes()).hexdigest()[:16]
    dst = 'assets/' + key + cover_path.suffix.lower()
    shutil.copy2(cover_path, root / dst)
    with Image.open(cover_path) as im:
        assets[key] = {'path': dst, 'url': '', 'width': im.width, 'height': im.height}
    names = ['新作', '汉化', '周边']
    sections = [{'name': name, 'banner': k, 'stories': []} for name, k in zip(names, list(assets)[:3])]
    save(root / 'source/article.json', {'schema_version': 1, 'issue': args.issue, 'title': args.title, 'subtitle': args.title, 'account': 'Galgame批评', 'cover': key, 'sections': sections, 'stories': [], 'staff': [], 'recommendation_banner': 'bdf51f10e69ae164', 'recommendations': [], 'assets': assets})
    print(root / 'source/article.json')


def image_tag(src, alt=''):
    return f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}" width="100%" style="display:block;width:100%;max-width:100%;height:auto;vertical-align:middle;box-sizing:border-box;">'


def generic_gallery(gallery, resolve, assets, static=False):
    ids = gallery.get('images', [])
    if not ids:
        return ''
    mode = gallery.get('mode', 'swipe')
    if mode == 'swipe' and not static:
        tiles = ''.join('<section style="display:inline-block;vertical-align:middle;width:80%;padding:0 5px;box-sizing:border-box;white-space:normal;">' + image_tag(resolve(k)) + '</section>' for k in ids)
        return '<section style="margin:12px 0;overflow-x:auto;white-space:nowrap;width:100%;box-sizing:border-box;"><p style="margin:0 0 8px;text-align:center;font-size:12px;color:#999;">← 左右滑动查看更多图片 →</p>' + tiles + '</section>'
    stack = ''.join('<section style="margin:0 0 2%;line-height:0;">' + image_tag(resolve(k)) + '</section>' for k in ids)
    if mode != 'fold' or static:
        return '<section style="margin:12px 0;">' + stack + '</section>'
    # The image stack has zero flow height. The transparent SVG is the animated spacer.
    # Animating viewBox changes intrinsic height while width stays bounded at 100%.
    ratio = sum(assets[k]['height'] / assets[k]['width'] + .02 for k in ids) + .10
    if ratio <= .6:
        return '<section style="margin:12px 0;">' + stack + '</section>'
    hint = '<section style="font-size:12px;color:#999;text-align:center;line-height:1.8;padding:1% 0;">点击图片展开全部 ↓</section>'
    return f'''<section style="margin:12px 0;overflow:hidden;width:100%;border-radius:12px;background:#fcfcfc;box-sizing:border-box;">
<section style="height:0;overflow:visible;">{hint}{stack}</section>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60" width="100%" style="display:block;width:100%;max-width:100%;height:auto;pointer-events:none;">
<rect width="100%" height="100%" style="opacity:0;pointer-events:auto;"><animate attributeName="width" begin="click + 0.1s" dur="0.01s" to="0" fill="freeze"/></rect>
<animate attributeName="viewBox" begin="click" dur="0.8s" from="0 0 100 60" to="0 0 100 {ratio * 100:.6f}" fill="freeze" restart="never"/>
</svg></section>'''


def bound_layout(fragment):
    """Keep every layout box within its parent, including interactive galleries."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(fragment, 'html.parser')
    for element in soup.find_all('section'):
        style = element.get('style', '')
        props = dict((k.strip().lower(), v.strip()) for k, v in
                     (part.split(':', 1) for part in style.split(';') if ':' in part))
        width = re.fullmatch(r'([\d.]+)%', props.get('width', ''))
        if width and float(width[1]) > 100:
            # Old Xiumi tracks had width: 320%, with four 25% tiles. The
            # equivalent flex row keeps a bounded 100% box and 80% flex tiles.
            factor = float(width[1]) / 100
            tiles = element.find_all('section', recursive=False)
            if not tiles:
                raise ValueError('超宽图组没有可识别的图片项。')
            for tile in tiles:
                tile_style = tile.get('style', '')
                match = re.search(r'(?:^|;)\s*width:\s*([\d.]+)%', tile_style)
                if not match:
                    raise ValueError('无法计算超宽图组的图片项宽度。')
                tile_width = min(100, float(match[1]) * factor)
                tile['style'] = re.sub(r'(?:^|;)\s*width:[^;]*', '', tile_style).strip(';') + f';width:{tile_width:g}%;max-width:100%;min-width:0;flex:0 0 {tile_width:g}%;box-sizing:border-box;'
            element['style'] = 'display:flex;flex-flow:row nowrap;width:100%;max-width:100%;min-width:0;box-sizing:border-box;'
        elif 'flex' in props and props.get('flex', '').startswith('100 100'):
            element['style'] = style.rstrip(';') + ';min-width:0;'
    for svg in soup.find_all('svg'):
        animation = svg.find('animate', recursive=False)
        if not animation or animation.get('attributename', '').lower() != 'width':
            continue
        target = re.fullmatch(r'([\d.]+)%', animation.get('to', ''))
        viewbox = svg.get('viewbox', '').split()
        if not target or len(viewbox) != 4:
            raise ValueError('无法把旧 SVG 宽度展开转换为有界 viewBox 展开。')
        # Imported folds mix image ratios with fixed-pixel margins. The old
        # spacer was sized for a wider editor and clipped the last image at
        # 320px. Reserve 12 viewBox units (30px at the narrowest tested frame).
        final_height = float(viewbox[3]) * float(target[1]) / 100 + 12
        animation['attributename'] = 'viewBox'
        animation['from'] = ' '.join(viewbox)
        animation['to'] = ' '.join(viewbox[:3]) + f' {final_height:.6f}'
        svg['style'] = 'display:block;width:100%;max-width:100%;height:auto;pointer-events:none;box-sizing:border-box;'
    result = str(soup).replace('viewbox=', 'viewBox=').replace('attributename=', 'attributeName=')
    return result


def render(args):
    from bs4 import BeautifulSoup
    data_path = Path(args.data).resolve()
    data = load(data_path)
    project = data_path.parent.parent
    theme = load(args.theme) if args.theme else None
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    assets = data['assets']
    story_ids = [s['id'] for s in data['stories']]
    section_ids = [sid for section in data['sections'] for sid in section['stories']]
    if not story_ids or len(story_ids) != len(set(story_ids)) or sorted(story_ids) != sorted(section_ids):
        raise SystemExit('每条新闻必须有唯一 ID，且恰好归属一个章节；正文不能为空。')
    for story in data['stories']:
        if not story['title'].strip() or not story['paragraphs'] or any(not isinstance(p, str) or not p.strip() for p in story['paragraphs']):
            raise SystemExit('存在空标题或空正文：' + story['id'])
    if not args.local_only and any(not a.get('url', '').startswith('https://') for a in assets.values()):
        raise SystemExit('存在未绑定 HTTPS 图床地址的素材。先用 --local-only 预览；真实 URL 写回后再导出。')
    errors = []
    for key, item in assets.items():
        if not (project / item['path']).is_file():
            errors.append('缺少图片：' + key)
    if errors:
        raise SystemExit('\n'.join(errors))
    generic_theme = load(Path(__file__).parent.parent / 'assets/components.json')
    def output_body(local=False, static=False, compatible=False):
        use_theme = theme if not compatible else None
        def resolve(key):
            if key not in assets:
                raise ValueError('未注册的素材：' + key)
            if local:
                return output_asset_path(project / assets[key]['path'], out)
            return assets[key]['url']
        cards = {}
        for story in data['stories']:
            body = ''.join('<p style="white-space:normal;margin:0;padding:0;box-sizing:border-box;">' + html.escape(p) + '</p>' for p in story['paragraphs'])
            layout = story.get('layout') if use_theme else None
            if layout:
                if not theme or layout not in theme['cards']:
                    raise ValueError('找不到新闻版式：' + str(layout))
                card = theme['cards'][layout]
                card = re.sub(r'\{\{image:(\d+)\}\}', lambda m: html.escape(resolve(story['images'][int(m[1])]), quote=True), card)
            else:
                card = generic_theme['odd' if int(story['number']) % 2 else 'even']
                lead = image_tag(resolve(story['lead'])) if story.get('lead') else ''
                gallery = generic_gallery(story.get('gallery', {}), resolve, assets, static)
                card = card.replace('{{lead}}', lead).replace('{{gallery}}', gallery)
            cards[story['id']] = card.replace('{{number}}', str(int(story['number']))).replace('{{title}}', html.escape(story['title'])).replace('{{body}}', body)
        if use_theme:
            result = re.sub(r'\{\{story:([^}]+)\}\}', lambda m: cards.pop(m[1]), theme['shell'])
            if cards:
                raise ValueError('新闻数量或 ID 已改变，请移除 --theme，使用通用组件模式。')
        else:
            parts = [image_tag(resolve(data['cover']))]
            for section in data['sections']:
                parts.append('<section style="margin:16px 0;line-height:0;">' + image_tag(resolve(section['banner']), section['name']) + '</section>')
                parts.extend(cards[sid] for sid in section['stories'])
            parts.append('<section style="margin:24px 0;font-size:13px;text-align:center;line-height:1.8;color:#999;">' + '<br>'.join(html.escape(p) for p in data.get('staff', [])) + '</section>')
            if data.get('recommendations') and data.get('recommendation_banner'):
                parts.append('<section style="margin:16px 0;line-height:0;">' + image_tag(resolve(data['recommendation_banner']), '推荐阅读') + '</section>')
            for recommendation in data.get('recommendations', []):
                parts.append('<section style="margin:16px 0;">' + '<a href="' + html.escape(recommendation['url'], quote=True) + '">' + image_tag(resolve(recommendation['image']), recommendation['title']) + '</a></section>')
            result = '<section style="letter-spacing:1px;line-height:1.8;font-size:16px;color:#3e3e3e;text-align:justify;box-sizing:border-box;">' + ''.join(parts) + '</section>'
        result = re.sub(r'\{\{asset:([^}]+)\}\}', lambda m: html.escape(resolve(m[1]), quote=True), result)
        result = bound_layout(result)
        if '{{' in result:
            raise ValueError('输出包含未填充的模板变量。')
        if static:
            soup = BeautifulSoup(result, 'html.parser')
            for svg in list(soup.find_all('svg')):
                if not svg.parent: continue
                if svg.find('animate'):
                    spacer = svg.parent.parent.parent
                    stack = spacer.find_previous_sibling('section')
                    if stack and 'height: 0px' in stack.get('style', ''):
                        stack['style'] = 'height:auto;overflow:visible;box-sizing:border-box;'
                        spacer.decompose()
            result = str(soup).replace('viewbox=', 'viewBox=').replace('attributename=', 'attributeName=')
        return result
    local = output_body(local=True)
    (out / 'article-local.html').write_text(document(data['title'], local))
    remote = output_body(local=args.local_only)
    if args.local_only:
        for name in ('wechat.html', 'wechat-expanded.html', 'wechat-safe.html', 'article.html', 'article-expanded.html', 'article-safe.html'):
            (out / name).unlink(missing_ok=True)
    else:
        expanded = output_body(static=True)
        compatible = output_body(static=True, compatible=True)
        (out / 'wechat-safe.html').write_text(compatible)
        (out / 'article-safe.html').write_text(document(data['title'], compatible))
        (out / 'wechat.html').write_text(remote)
        (out / 'wechat-expanded.html').write_text(expanded)
        (out / 'article.html').write_text(document(data['title'], remote))
        (out / 'article-expanded.html').write_text(document(data['title'], expanded))
    template = (Path(__file__).parent.parent / 'assets/preview.html').read_text()
    nav = ''.join('<a href="#chapter-' + str(i) + '"><span>' + str(i+1).zfill(2) + '</span>' + html.escape(s['name']) + '<small>' + str(len(s['stories'])) + '</small></a>' for i, s in enumerate(data['sections']))
    # Anchors belong to the preview wrapper only; the exported article has no app controls.
    soup = BeautifulSoup(local, 'html.parser')
    for i, section in enumerate(data['sections']):
        banner_path = output_asset_path(project / assets[section['banner']]['path'], out)
        image = soup.find('img', src=banner_path)
        if image: image['id'] = 'chapter-' + str(i)
    for story, b in zip(data['stories'], soup.find_all('b')):
        node = b
        while node.parent and len(node.parent.find_all('strong')) == 1: node = node.parent
        node['id'] = story['id']
    values = {'DATA_PATH': html.escape(output_asset_path(data_path, out), quote=True), 'EXPORT_READY': 'false' if args.local_only else 'true', 'TITLE': html.escape(data['title']), 'ISSUE': html.escape(str(data['issue'])),
              'SUBTITLE': html.escape(data['subtitle']), 'ARTICLE': str(soup).replace('viewbox=', 'viewBox=').replace('attributename=', 'attributeName='),
              'NAV': nav, 'COUNT': str(len(data['stories'])), 'ASSETS': str(len(assets))}
    for key, value in values.items(): template = template.replace('<!--' + key + '-->', value)
    (out / 'preview.html').write_text(template)
    parsed = BeautifulSoup(remote, 'html.parser')
    oversized = []
    for element in parsed.find_all(style=True):
        widths = re.findall(r'(?:^|;)\s*(?:max-)?width:\s*([\d.]+)%', element['style'])
        if any(float(width) > 100 for width in widths):
            oversized.append(element['style'])
    if oversized:
        raise ValueError('输出仍含超宽元素：' + str(oversized))
    report = {'oversized_width_styles': oversized, 'stories': len(data['stories']), 'paragraphs': sum(len(s['paragraphs']) for s in data['stories']),
              'unique_assets': len(assets), 'missing_assets': errors,
              'smil_galleries': len(BeautifulSoup(remote, 'html.parser').select('svg > animate')),
              'export_ready': not args.local_only, 'published_or_uploaded': False, 'wechat_editor_roundtrip_verified': False}
    save(out / 'validation.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def output_asset_path(asset, out):
    import os
    return Path(os.path.relpath(asset, out)).as_posix()


def document(title, body):
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + html.escape(title) + '</title><style>body{margin:0;background:#fff;font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue","PingFang SC","Hiragino Sans GB","Microsoft YaHei",Arial,sans-serif;}main{max-width:677px;margin:0 auto;padding:20px;overflow:hidden;word-wrap:break-word;}p{margin:0;}img{max-width:100%;}section{box-sizing:border-box;}</style><main>' + body + '</main></html>'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    x = commands.add_parser('init'); x.add_argument('--out', required=True); x.add_argument('--issue', required=True); x.add_argument('--title', required=True); x.add_argument('--cover', required=True); x.set_defaults(run=init_issue)
    x = commands.add_parser('capture'); x.add_argument('--url', required=True); x.add_argument('--out', required=True); x.set_defaults(run=capture)
    x = commands.add_parser('extract-docx'); x.add_argument('docx'); x.add_argument('--out', required=True)
    x.set_defaults(run=lambda a: save(a.out, {'paragraphs': paragraphs(a.docx)}))
    x = commands.add_parser('import-reference'); x.add_argument('--html', required=True); x.add_argument('--docx', required=True); x.add_argument('--url', required=True); x.add_argument('--out', required=True); x.set_defaults(run=import_reference)
    x = commands.add_parser('render'); x.add_argument('--data', required=True); x.add_argument('--theme'); x.add_argument('--out', required=True); x.add_argument('--local-only', action='store_true'); x.set_defaults(run=render)
    args = p.parse_args(); args.run(args)


if __name__ == '__main__':
    main()
