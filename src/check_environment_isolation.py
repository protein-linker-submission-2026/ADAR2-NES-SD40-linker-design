"""Verify isolated Python dependencies and record OS/GPU runtime evidence."""
import argparse
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def output(command):
    result = subprocess.run(command, capture_output=True, text=True)
    return {'exit_code': result.returncode, 'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=('rfdiffusion', 'boltz'), required=True)
    args = parser.parse_args()
    import torch
    import numpy
    import yaml
    modules = [torch, numpy, yaml]
    if args.mode == 'rfdiffusion':
        import dgl
        import se3_transformer
        import rfdiffusion
        modules.extend([dgl, se3_transformer, rfdiffusion])
    else:
        import boltz
        modules.append(boltz)
    prefix = Path(sys.prefix).resolve()
    for module in modules:
        source = Path(module.__file__).resolve()
        if prefix not in source.parents:
            raise RuntimeError(f'{module.__name__} was imported from outside the new environment')
    assert torch.cuda.is_available(), 'CUDA is unavailable'
    assert torch.ones(16, device='cuda').sum().item() == 16
    pip_check = output([sys.executable, '-m', 'pip', 'check'])
    if pip_check['exit_code']:
        raise RuntimeError(pip_check['stdout'])
    record = {
        'mode': args.mode, 'python': platform.python_version(),
        'packages_imported_from_new_environment': [m.__name__ for m in modules],
        'torch': torch.__version__, 'torch_cuda_build': torch.version.cuda,
        'libc': platform.libc_ver(),
        'os_release': Path('/etc/os-release').read_text() if Path('/etc/os-release').exists() else None,
        'gpu_driver': output(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader']),
        'system_library_packages': output(['dpkg-query', '-W', '-f=${Package}=${Version}\n', 'libc6', 'libstdc++6', 'libgomp1', 'zlib1g', 'gcc', 'g++']) if shutil.which('dpkg-query') else None,
        'pip_check': pip_check, 'cuda_tensor_test': 'PASS',
        'scope': 'New dependency environment on existing OS/driver and Python interpreter; not a fresh-machine installation',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
