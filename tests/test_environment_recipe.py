"""Environment recipe checks without network, GPUs, or package installation."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))
from prepare_offline_requirements import DGL_REQUIREMENT, DGL_WHEEL, offline_lines, verify_dgl_wheel
from validate_submission import iter_package_files


class EnvironmentRecipeTests(unittest.TestCase):
    def test_local_runtime_not_part_of_anonymous_submission_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('.envs/pkg/info.txt', 'external/source.py', 'src/local_paths.sh', 'results/cache/record.txt', 'README.md'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
            self.assertEqual({p.relative_to(root).as_posix() for p in iter_package_files(root)}, {'results/cache/record.txt', 'README.md'})

    def test_known_dgl_url_maps_to_exact_offline_version(self):
        self.assertEqual(offline_lines([DGL_REQUIREMENT]), ['dgl==2.4.0+cu121'])

    def test_other_urls_are_not_silently_rewritten(self):
        other = DGL_REQUIREMENT.replace('2.4.0%2B', '2.5.0%2B')
        self.assertEqual(offline_lines([other, 'numpy==2.0.2']), [other, 'numpy==2.0.2'])

    def test_same_name_wrong_dgl_content_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / DGL_WHEEL).write_bytes(b'not the official wheel')
            with self.assertRaises(ValueError):
                verify_dgl_wheel(root)

    def test_all_dependency_requirements_have_exact_versions(self):
        for path in (ROOT / 'environments').glob('*-test-pins.txt'):
            for line in path.read_text().splitlines():
                if not line or line.startswith('#') or line.startswith('--'):
                    continue
                self.assertTrue('==' in line or line == DGL_REQUIREMENT, (path.name, line))

    def test_rf_recipe_uses_explicit_dgl_archive(self):
        lines = (ROOT / 'environments/rfdiffusion-test-pins.txt').read_text().splitlines()
        self.assertIn(DGL_REQUIREMENT, lines)


if __name__ == '__main__':
    unittest.main()
