#!/usr/bin/env python3
"""Upload an existing local preview to Zipline and export a hosted copy.

Credentials are read at runtime; no token is embedded in generated HTML or maps.
"""
import argparse
import base64
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
import requests

from image_policy import MAX_BYTES, POLICY_VERSION, prepare_image


def prepare_payload_images(payload, original_images=False):
    if payload.get('image_policy') != POLICY_VERSION:
        raise ValueError('预览尚未使用当前 500 KiB 图片策略，请先用当前 skill 重新 render')
    roles = payload.get('image_roles', {})
    prepared, largest = {}, 0
    for path, source in payload['images'].items():
        try:
            header, encoded = source.split(',', 1)
            if not header.startswith('data:image/') or ';base64' not in header:
                raise ValueError('图片数据格式无效')
            raw = base64.b64decode(encoded, validate=True)
            data, mime, _ = prepare_image(raw, decoration=bool(roles.get(path)), original=original_images)
        except ValueError:
            raise ValueError('图片预处理失败：' + path + '；请检查图片或先处理超出 500 KiB 的装饰图/动图') from None
        largest = max(largest, len(data))
        prepared[path] = 'data:' + mime + ';base64,' + base64.b64encode(data).decode('ascii')
    payload['images'] = prepared
    return largest


class ApiFailure(RuntimeError):
    def __init__(self, method, path, response):
        super().__init__(f'{method} {path}: HTTP {response.status_code}')
        self.status = response.status_code
        try:
            self.retry_after = min(60, max(1, int(response.headers.get('Retry-After', '60'))))
        except ValueError:
            self.retry_after = 60


def session_for(url):
    session = requests.Session()
    host = urlsplit(url).hostname
    try:
        private = ipaddress.ip_address(host).is_private
    except ValueError:
        private = host == 'localhost' or (host or '').endswith('.local')
    if private:
        session.trust_env = False
    return session


def api_call(session, base, method, path, **kwargs):
    response = session.request(method, base + path, timeout=(10, 90), allow_redirects=False, **kwargs)
    if not 200 <= response.status_code < 300:
        # Response bodies may contain credentials, so do not echo them.
        raise ApiFailure(method, path, response)
    return response.json()


def get_token(args):
    if args.keychain:
        service, account = args.keychain.split('/', 1)
        result = subprocess.run(['security', 'find-generic-password', '-s', service, '-a', account, '-w'], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('无法从钥匙串读取图床凭证')
        token = result.stdout.strip()
    elif args.token_file:
        token = Path(args.token_file).expanduser().read_text().strip()
    else:
        token = os.environ.get(args.token_env or 'ZIPLINE_TOKEN', '').strip()
    if not token:
        raise ValueError('请先提供图床 API Token：环境变量、凭证文件或钥匙串引用')
    if '\n' in token or '\r' in token:
        raise ValueError('图床凭证含非法换行')
    return token


def write_json(path, data):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def verify_image(session, url, expected_hash, expected_size):
    # Public fetch has no token or cookie; validate content, not merely HTTP 200.
    if urlsplit(url).scheme != 'https':
        return False
    try:
        with session.get(url, timeout=(10, 45), stream=True, allow_redirects=False) as response:
            if response.status_code != 200 or not response.headers.get('Content-Type', '').lower().startswith('image/'):
                return False
            size, digest = 0, hashlib.sha256()
            for chunk in response.iter_content(256 * 1024):
                size += len(chunk)
                if size > expected_size:
                    return False
                digest.update(chunk)
            return size == expected_size and digest.hexdigest() == expected_hash
    except requests.RequestException:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', required=True)
    parser.add_argument('--api-base', required=True, help='Zipline API origin; explicit private LAN HTTP is supported')
    parser.add_argument('--public-base', required=True, help='Public HTTPS origin for image links')
    parser.add_argument('--cache', help='Persistent upload map; contains URLs, never credentials')
    parser.add_argument('--folder', required=True, help='Folder for newly uploaded images, e.g. the issue number')
    parser.add_argument('--original-images', action='store_true', help='仅在明确要求时跳过 500 KiB 限制，按输入字节上传')
    credentials = parser.add_mutually_exclusive_group()
    credentials.add_argument('--keychain', help='macOS Keychain service/account')
    credentials.add_argument('--token-file')
    credentials.add_argument('--token-env', help='Environment variable name; default ZIPLINE_TOKEN')
    args = parser.parse_args()
    api, public = args.api_base.rstrip('/'), args.public_base.rstrip('/')
    for value in [api, public]:
        parts = urlsplit(value)
        if parts.username or parts.password or parts.query or parts.fragment or parts.path:
            raise ValueError('图床地址须为不含凭证和路径的 origin')
    if urlsplit(public).scheme != 'https':
        raise ValueError('公众号图片直链必须使用 HTTPS')
    if urlsplit(api).scheme != 'https':
        try:
            private = ipaddress.ip_address(urlsplit(api).hostname).is_private
        except ValueError:
            private = urlsplit(api).hostname == 'localhost'
        if urlsplit(api).scheme != 'http' or not private:
            raise ValueError('API 只允许 HTTPS 或显式指定的私有内网 HTTP 地址')
    preview = Path(args.preview).resolve()
    original = preview.read_text(encoding='utf-8')
    if 'function copySource(' not in original:
        raise ValueError('预览模板版本较旧，请用当前 skill 重新 render 后再上传')
    soup = BeautifulSoup(original, 'html.parser')
    payload = json.loads(soup.select_one('#local-payload').string)
    if not payload.get('images'):
        raise ValueError('预览不含本地图片数据，请先 render')
    largest_image = prepare_payload_images(payload, args.original_images)
    client, anonymous = session_for(api), session_for(public)
    client.headers['Authorization'] = get_token(args)
    user = api_call(client, api, 'GET', '/api/user')['user']
    owner = str(user['id'])
    cache_path = Path(args.cache).expanduser().resolve() if args.cache else preview.parent / 'image-host-map.json'
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {'public_base': public, 'owner': owner, 'images': {}}
    if cache.get('public_base') != public or cache.get('owner') != owner:
        raise ValueError('上传缓存属于其他图床或账号，请指定独立 --cache')
    folders = api_call(client, api, 'GET', '/api/user/folders?noincl=true')
    folder = next((x for x in folders if x['name'] == args.folder), None)
    if folder is None:
        folder = api_call(client, api, 'POST', '/api/user/folders', json={'name': args.folder, 'isPublic': False})
    uploaded = reused = 0
    mapping, verified = {}, {}
    extensions = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/gif': '.gif', 'image/webp': '.webp'}
    for index, (path, source) in enumerate(payload['images'].items(), 1):
        header, encoded = source.split(',', 1)
        mime = header.removeprefix('data:').split(';')[0]
        if mime not in extensions or ';base64' not in header:
            raise ValueError('不支持的本地图片格式')
        data = base64.b64decode(encoded, validate=True)
        digest = hashlib.sha256(data).hexdigest()
        if digest in verified:
            mapping[path] = verified[digest]
            continue
        item = cache['images'].get(digest)
        if item and urlsplit(item['url']).netloc == urlsplit(public).netloc and verify_image(anonymous, item['url'], digest, len(data)):
            reused += 1
        else:
            filename = hashlib.sha256(owner.encode() + b'\0' + data).hexdigest()
            expected_url = public + '/u/' + filename + extensions[mime]
            item = None
            for attempt in range(3):
                try:
                    reply = api_call(client, api, 'POST', '/api/upload', headers={
                        'x-zipline-filename': filename,
                        'x-zipline-folder': folder['id'],
                        'x-zipline-deletes-at': 'never',
                        'x-zipline-extensionless': 'false',
                    }, files={'file': ('image' + extensions[mime], data, mime)})
                    file = reply['files'][0]
                    if urlsplit(file['url']).netloc != urlsplit(public).netloc:
                        raise ValueError('上传结果的域名与 public-base 不一致')
                    item = {'url': file['url'], 'id': file['id'], 'bytes': len(data), 'mime': mime}
                    if not verify_image(anonymous, item['url'], digest, len(data)):
                        raise RuntimeError('公网图片字节校验未通过')
                    break
                except (requests.RequestException, RuntimeError) as error:
                    # A timed-out POST may have succeeded. Recover its deterministic
                    # URL before retrying, to avoid duplicate uploads.
                    if verify_image(anonymous, expected_url, digest, len(data)):
                        item = {'url': expected_url, 'bytes': len(data), 'mime': mime}
                        break
                    if attempt == 2:
                        raise RuntimeError(f'图片 {index} 上传或公网验证失败；缓存已保留，可重新执行') from None
                    delay = error.retry_after if isinstance(error, ApiFailure) and error.status == 429 else 2 ** (attempt + 1)
                    print(f'图片 {index} 等待 {delay} 秒后重试', flush=True)
                    time.sleep(delay)
            cache['images'][digest] = item
            write_json(cache_path, cache)
            uploaded += 1
        mapping[path] = verified[digest] = item['url']
        print(f'已核验 {len(verified)} 张独立图片（素材 {index}/{len(payload["images"])})', flush=True)
    # Preserve offline visual preview, but put only small HTTPS URLs on clipboard.
    payload['remoteImages'] = mapping
    payload['imageHostVerifiedAt'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    soup.select_one('#local-payload').string = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c')
    for name, fragment in payload['templates'].items():
        fragment_soup = BeautifulSoup(fragment, 'html.parser')
        for img in fragment_soup.find_all('img'):
            img['src'] = mapping[img['src']]
        hosted_name = name.removesuffix('.html') + '-hosted.html'
        text = str(fragment_soup).replace('viewbox=', 'viewBox=').replace('attributename=', 'attributeName=')
        (preview.parent / hosted_name).write_text(text, encoding='utf-8')
        for link in soup.find_all('a', href=name):
            link['href'] = hosted_name
    hosted_preview = str(soup).replace('viewbox=', 'viewBox=').replace('attributename=', 'attributeName=')
    (preview.parent / 'preview-hosted.html').write_text(hosted_preview, encoding='utf-8')
    write_json(preview.parent / 'image-host-verification.json', {
        'unique_images': len(verified), 'uploaded': uploaded, 'reused': reused,
        'public_anonymous_byte_verification': True,
        'verified_at': payload['imageHostVerifiedAt'],
        'wechat_editor_roundtrip_verified': False,
        'max_image_bytes': largest_image,
        'image_cap_enforced': not args.original_images,
        'image_policy': POLICY_VERSION,
    })
    print(f'已生成 preview-hosted.html：上传 {uploaded}，复用 {reused}；凭证未写入产物。')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, requests.RequestException) as exc:
        # Exception bodies/requests may contain sensitive headers: show only
        # controlled messages, never requests' raw exception representation.
        print(str(exc) if isinstance(exc, (ValueError, RuntimeError)) else '网络请求失败；请检查地址、连接和上传缓存。')
        raise SystemExit(1)
