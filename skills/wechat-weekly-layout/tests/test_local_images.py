import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bs4 import BeautifulSoup
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/wechat_layout.py'
sys.path.insert(0, str(SCRIPT.parent))
from image_policy import MAX_BYTES, POLICY_VERSION, prepare_image
from zipline_images import prepare_payload_images

spec = importlib.util.spec_from_file_location('wechat_layout', SCRIPT)
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


class LocalImageTests(unittest.TestCase):
    def test_local_only_still_exports_copyable_embedded_images(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'assets').mkdir()
            image = root / 'assets' / 'local.png'
            Image.new('RGBA', (32, 32), (12, 80, 130, 110)).save(image)
            original = image.read_bytes()
            item = {'path': 'assets/local.png', 'width': 32, 'height': 32}
            data = {'issue': '1', 'title': '本地稿', 'subtitle': '无需图床', 'cover': 'local',
                    'assets': {'local': item}, 'sections': [{'name': '新作', 'banner': 'local', 'stories': ['n1']}],
                    'stories': [{'id': 'n1', 'number': 1, 'title': '标题', 'paragraphs': ['正文'], 'lead': 'local'}]}
            layout.save(root / 'source/article.json', data)
            subprocess.run([sys.executable, str(SCRIPT), 'render', '--data', str(root / 'source/article.json'),
                            '--out', str(root / 'output'), '--local-only'], check=True, capture_output=True)
            for name in ('wechat.html', 'wechat-expanded.html', 'wechat-safe.html'):
                soup = BeautifulSoup((root / 'output' / name).read_text(), 'html.parser')
                self.assertEqual(len(soup.find_all('img')), 3)
                for img in soup.find_all('img'):
                    self.assertTrue(img['src'].startswith('data:image/jpeg;base64,'))
                    self.assertLessEqual(len(base64.b64decode(img['src'].split(',', 1)[1])), MAX_BYTES)
            preview = BeautifulSoup((root / 'output/preview.html').read_text(), 'html.parser')
            payload = json.loads(preview.select_one('#local-payload').string)
            self.assertIn('<section', payload['templates']['wechat.html'])
            self.assertEqual(payload['image_policy'], POLICY_VERSION)
            self.assertNotIn('fetch(', preview.find_all('script')[-1].string)
            report = layout.load(root / 'output/validation.json')
            self.assertTrue(report['export_ready'])
            self.assertFalse(report['external_image_requests_required'])
            self.assertEqual(image.read_bytes(), original)

    def test_body_palette_transparency_is_composited_on_white(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / 'palette.png'
            palette = Image.new('P', (48, 48), 0)
            palette.putpalette([10, 20, 30, 255, 240, 230] + [0] * 762)
            palette.save(image, transparency=0)
            sources, _ = layout.local_image_data({'p': {'path': 'palette.png'}}, root, root / 'output')
            source = next(iter(sources.values()))
            self.assertTrue(source.startswith('data:image/jpeg;base64,'))
            from io import BytesIO
            with Image.open(BytesIO(base64.b64decode(source.split(',', 1)[1]))) as result:
                self.assertTrue(all(channel >= 250 for channel in result.getpixel((0, 0))))

    def test_init_copies_all_six_framework_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cover = root / 'cover.png'
            Image.new('RGB', (32, 20), 'white').save(cover)
            project = root / 'issue'
            subprocess.run([sys.executable, str(SCRIPT), 'init', '--out', str(project), '--issue', '1',
                            '--title', '本地周报', '--cover', str(cover)], check=True, capture_output=True)
            data = layout.load(project / 'source/article.json')
            framework = [item for item in data['assets'].values() if item.get('role')]
            self.assertEqual(len(framework), 6)
            self.assertEqual(set(data['gallery_hints']), {'fold', 'swipe'})
            for item in framework:
                self.assertTrue((project / item['path']).is_file())
            self.assertEqual(len(data['sections']), 3)

    def test_animation_bytes_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / 'motion.gif'
            frames = [Image.new('RGB', (24, 24), color) for color in ('red', 'blue')]
            frames[0].save(image, save_all=True, append_images=frames[1:], duration=120, loop=0)
            sources, report = layout.local_image_data({'gif': {'path': 'motion.gif'}}, root, root / 'output')
            source = next(iter(sources.values()))
            self.assertTrue(source.startswith('data:image/gif;base64,'))
            self.assertEqual(base64.b64decode(source.split(',', 1)[1]), image.read_bytes())
            self.assertEqual(report['optimized_images'], 0)

    def test_large_static_image_meets_byte_and_width_limits(self):
        from io import BytesIO
        buffer = BytesIO()
        Image.effect_noise((2200, 1600), 100).convert('RGB').save(buffer, 'PNG')
        data, mime, audit = prepare_image(buffer.getvalue())
        self.assertEqual(mime, 'image/jpeg')
        self.assertLessEqual(len(data), MAX_BYTES)
        self.assertLessEqual(audit['size'][0], 1600)
        self.assertEqual(prepare_image(data)[0], data, 'upload must not re-encode a prepared JPEG')

    def test_decoration_keeps_transparency_but_cannot_exceed_cap(self):
        from io import BytesIO
        buffer = BytesIO()
        Image.new('RGBA', (16, 16), (0, 0, 0, 0)).save(buffer, 'PNG')
        raw = buffer.getvalue()
        self.assertEqual(prepare_image(raw, decoration=True)[0], raw)
        large = BytesIO()
        Image.effect_noise((1200, 1200), 100).convert('RGB').save(large, 'PNG')
        self.assertGreater(len(large.getvalue()), MAX_BYTES)
        with self.assertRaisesRegex(ValueError, '500 KiB'):
            prepare_image(large.getvalue(), decoration=True)
        self.assertEqual(prepare_image(large.getvalue(), original=True)[0], large.getvalue())

    def test_upload_preflight_compresses_original_mode_payload_and_rejects_legacy(self):
        from io import BytesIO
        buffer = BytesIO()
        Image.new('RGBA', (50, 50), (0, 0, 0, 0)).save(buffer, 'PNG')
        source = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
        payload = {'image_policy': POLICY_VERSION, 'image_roles': {}, 'images': {'body': source}}
        largest = prepare_payload_images(payload)
        self.assertLessEqual(largest, MAX_BYTES)
        self.assertTrue(payload['images']['body'].startswith('data:image/jpeg;base64,'))
        with self.assertRaisesRegex(ValueError, 'render'):
            prepare_payload_images({'images': {'body': source}})

    def test_oversized_animation_is_rejected_without_losing_frames(self):
        from io import BytesIO
        buffer = BytesIO()
        first = Image.effect_noise((1000, 1000), 100).convert('P')
        second = Image.effect_noise((1000, 1000), 100).convert('P')
        first.save(buffer, 'GIF', save_all=True, append_images=[second], duration=100)
        raw = buffer.getvalue()
        self.assertGreater(len(raw), MAX_BYTES)
        with self.assertRaisesRegex(ValueError, '500 KiB'):
            prepare_image(raw)
        self.assertEqual(prepare_image(raw, original=True)[0], raw)


if __name__ == '__main__':
    unittest.main()
