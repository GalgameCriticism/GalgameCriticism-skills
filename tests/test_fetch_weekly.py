import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fetch', REPO / 'skills/xiaoheihe-weekly-sync/scripts/fetch_weekly.py')
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)

def fixture():
    articles = [{'id': 100, 'author_uid': 7, 'type': 4, 'dyn_id_str': '200', 'publish_time': 1000, 'title': '周报12期'}, {'id': 101, 'author_uid': 7, 'type': 4, 'dyn_id_str': '201', 'publish_time': 2000, 'title': '周报13期'}]
    collection = {'code': 0, 'data': {'articles': articles, 'list': {'articles_count': 2}, 'author': {'mid': 7, 'name': '测试作者'}}}
    def get(url, referer=None):
        if 'web/articles' in url:
            return json.dumps(collection).encode(), 'application/json'
        historical = '/200' in url or '/mobile/100' in url
        article = articles[0 if historical else 1]
        state = {'id': article['dyn_id_str'], 'detail': {'basic': {'uid': '7', 'rid_str': str(article['id'])}, 'modules': [{'module_title': {'text': article['title']}}, {'module_author': {'pub_ts': article['publish_time'], 'name': '测试作者'}}, {'module_content': {'paragraphs': [{'para_type': 3, 'line': {'pic': None, 'line_type': 1}}, {'para_type': 1, 'text': {'nodes': [{'type': 'TEXT_NODE_TYPE_WORD', 'word': {'words': '完整正文'}}]}}]}}]}}
        if '/opus/200' in url:
            return b'<html>unreadable desktop page</html>', 'text/html'
        return ('window.__INITIAL_STATE__=' + json.dumps(state) + ';').encode(), 'text/html'
    return get

class SourceRegression(unittest.TestCase):
    def test_divider_and_common_manifest(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(fetch, 'get', side_effect=fixture()):
            try:
                result = fetch.prepare('rl55', Path(tmp))
            except (ValueError, TypeError) as exc:
                self.fail(f'Complete source with a known divider must be supported: {exc}')
            self.assertTrue(any('──────────' in ''.join(n['text'] for n in b.get('nodes', [])) for b in result['blocks']))
            self.assertEqual(result['source_id'], '7:101')
            self.assertTrue((Path(tmp) / 'manifest.sha256').is_file())
            with self.assertRaisesRegex(ValueError, 'immutable'):
                fetch.prepare('rl55', Path(tmp))

    def test_requested_issue_and_mobile_fallback(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(fetch, 'get', side_effect=fixture()):
            try:
                result = fetch.prepare('rl55', Path(tmp), issue=12)
            except (ValueError, TypeError) as exc:
                self.fail(f'Requested historical issue must not use the latest article: {exc}')
            self.assertEqual(result['article_id'], 100)
            self.assertEqual(result['canonical_url'], 'https://www.bilibili.com/opus/200')

    def test_missing_issue_does_not_select_latest(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(fetch, 'get', side_effect=fixture()):
            try:
                fetch.prepare('rl55', Path(tmp), issue=11)
            except TypeError as exc:
                self.fail(f'Issue selection must be supported: {exc}')
            except ValueError as exc:
                self.assertIn('article-url', str(exc))
            else:
                self.fail('Missing requested issue must stop before a different issue is prepared')

    def test_explicit_mobile_article_for_missing_collection_entry(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(fetch, 'get', side_effect=fixture()):
            try:
                result = fetch.prepare('rl55', Path(tmp), issue=12, article_url='https://www.bilibili.com/read/cv100')
            except (ValueError, TypeError) as exc:
                self.fail(f'Explicit source URL must support a verified mobile article: {exc}')
            self.assertEqual(result['article_id'], 100)

    def test_explicit_article_still_checks_author(self):
        original = fixture()
        def wrong_author(url, referer=None):
            body, mime = original(url, referer)
            if 'mobile' in url:
                body = body.replace(b'"uid": "7"', b'"uid": "8"')
            return body, mime
        with tempfile.TemporaryDirectory() as tmp, patch.object(fetch, 'get', side_effect=wrong_author):
            with self.assertRaisesRegex(ValueError, 'author mismatch'):
                fetch.prepare('rl55', Path(tmp), issue=12, article_url='https://www.bilibili.com/read/cv100')
            self.assertFalse((Path(tmp) / 'manifest.json').exists())

    def test_explicit_article_cannot_substitute_other_issue(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(fetch, 'get', side_effect=fixture()):
            with self.assertRaisesRegex(ValueError, 'requested issue'):
                fetch.prepare('rl55', Path(tmp), issue=13, article_url='https://www.bilibili.com/read/cv100')
            self.assertFalse((Path(tmp) / 'manifest.json').exists())

if __name__ == '__main__':
    unittest.main()
