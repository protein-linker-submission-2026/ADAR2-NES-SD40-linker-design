"""Record the executing interpreter and package versions without personal paths."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess


def command_output(command):
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--vina')
    parser.add_argument('--adt-python')
    args = parser.parse_args()
    data = {
        'label': args.label,
        'scope': 'Observed environment for this run, not a historical lockfile',
        'python': platform.python_version(),
        'system': platform.system(),
        'packages': sorted(
            [{'name': d.metadata['Name'], 'version': d.version}
             for d in importlib.metadata.distributions()],
            key=lambda d: d['name'].lower(),
        ),
    }
    if args.source:
        data['source_commit'] = command_output(['git', '-C', str(args.source), 'rev-parse', 'HEAD'])
        data['tracked_source_modified'] = bool(command_output(['git', '-C', str(args.source), 'status', '--porcelain', '--untracked-files=no']))
    if args.vina:
        data['vina_version'] = command_output([args.vina, '--version'])
    if args.adt_python:
        data['autodocktools_version'] = command_output([args.adt_python, '-c', 'import AutoDockTools; print(AutoDockTools.__version__)'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
