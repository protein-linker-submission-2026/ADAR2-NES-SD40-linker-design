"""Use a separately acquired DGL wheel when installing from an offline wheelhouse."""
import argparse
import hashlib
from pathlib import Path

DGL_SHA256 = 'c2e9f089e52f6788553a6478fe9872cd96728a61f66f603356dc46fcb254efcf'
DGL_WHEEL = 'dgl-2.4.0+cu121-cp39-cp39-manylinux1_x86_64.whl'
DGL_REQUIREMENT = 'dgl @ https://data.dgl.ai/wheels/torch-2.4/cu121/dgl-2.4.0%2Bcu121-cp39-cp39-manylinux1_x86_64.whl#sha256=' + DGL_SHA256


def verify_dgl_wheel(wheelhouse):
    path = wheelhouse / DGL_WHEEL
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != DGL_SHA256:
        raise ValueError('Offline DGL wheel differs from the verified official archive; acquire the exact URL/hash in the dependency list')


def offline_lines(lines):
    return ['dgl==2.4.0+cu121' if line == DGL_REQUIREMENT else line for line in lines]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--wheelhouse', type=Path, required=True)
    args = parser.parse_args()
    lines = args.source.read_text(encoding='utf-8').splitlines()
    if DGL_REQUIREMENT in lines:
        verify_dgl_wheel(args.wheelhouse)
    lines = offline_lines(lines)
    args.output.write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
