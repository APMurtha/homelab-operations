import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from engineering import markdown_links


class MarkdownLinksTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def write(self, relative_path: str, content: str = '') -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip('\n'), encoding='utf-8')
        return path

    def test_collect_broken_links_handles_nested_paths_images_and_fragments(self):
        self.write('docs/guide.md', '# guide\n')
        self.write('docs/assets/pic one.png', 'img')
        note = self.write(
            'docs/notes/readme.md',
            '''
            [guide](../guide.md)
            [guide fragment](../guide.md#section)
            ![img](../assets/pic%20one.png)
            [missing](../missing.md)
            [missing image](../assets/ghost.png)
            [external](https://example.com/x)
            [mail](mailto:test@example.com)
            [fragment](#local)
            ''',
        )

        broken = markdown_links.collect_broken_links([str(note)])

        self.assertEqual(
            broken,
            [
                markdown_links.BrokenLink(
                    str(note.resolve()),
                    4,
                    '../missing.md',
                    str((note.parent / '../missing.md').resolve()),
                ),
                markdown_links.BrokenLink(
                    str(note.resolve()),
                    5,
                    '../assets/ghost.png',
                    str((note.parent / '../assets/ghost.png').resolve()),
                ),
            ],
        )

    def test_fenced_code_blocks_require_matching_fence_length(self):
        readme = self.write(
            'README.md',
            '''
            ````python
            [ignored-in-code](missing-in-code.md)
            ```
            still code
            ````
            [broken-after-fence](missing-after.md)
            ```
            [ignored-normal-fence](also-missing.md)
            ```
            [ok](present.md)
            ''',
        )
        self.write('present.md', 'ok\n')

        broken = markdown_links.collect_broken_links([str(readme)])

        self.assertEqual(
            broken,
            [
                markdown_links.BrokenLink(
                    str(readme.resolve()),
                    6,
                    'missing-after.md',
                    str((readme.parent / 'missing-after.md').resolve()),
                ),
            ],
        )

    def test_main_returns_nonzero_and_reports_source_line(self):
        readme = self.write(
            'docs/readme.md',
            '''
            [missing](nope.md)
            ''',
        )

        result = subprocess.run(
            [sys.executable, str(Path(markdown_links.__file__).resolve()), str(self.root / 'docs')],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn(f'{readme.resolve()}:1: broken relative link: nope.md', result.stderr)

    def test_main_returns_zero_when_no_broken_links(self):
        self.write('docs/target.md', 'ok\n')
        self.write(
            'docs/readme.md',
            '''
            [target](target.md)
            ![image](<target.md>)
            ''',
        )

        result = subprocess.run(
            [sys.executable, str(Path(markdown_links.__file__).resolve()), str(self.root / 'docs')],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
