# Environment reconstruction files

These files describe the independent 2026-10-03 TEST machine, not the historical production machine. Exact package versions are provided, but these are not wheel-hash locks. They do not include binary environments or model weights.

| File | Target | Status |
| --- | --- | --- |
| `rfdiffusion-test-pins.txt` | Linux x86_64, Python 3.9.23, torch 2.4.0, DGL CUDA 12.1 | Fresh dependency installation, isolation, pip check, CUDA tensor test and independent end-to-end smoke passed |
| `boltz-test-pins.txt` | Linux x86_64, Python 3.11.16, Boltz 2.2.1, torch 2.14.0/CUDA 13 | Fresh dependency installation, isolation, pip check, CUDA tensor test and independent end-to-end smoke passed |
| `windows_review_venv-test-pins.txt` | Windows, Python 3.12.14, result generation and validation | Versions observed in the fresh lightweight environment that passed validation |

The RF test uses NVIDIA SE3Transformer from DeepLearningExamples commit `729963dd47e7c8bd462ad10bfac7a7b0b604e6dd`. This is an additional source dependency, not the old `RFdiffusion/env/SE3nv.yml` installation recipe. Source is obtained from NVIDIA's official repository; retain its license notices. The DGL download has an explicit SHA256 after the cached and official builds were found to differ; both online and offline installation must use the verified official file.

Installation evidence: `../provenance/FRESH_ENVIRONMENT_TEST_20261003.json` verifies 76 RF dependency entries and 96 Boltz entries against the installed distributions. Separate source installs and packaging tools are also recorded in that snapshot. Sanitized installation logs are `../provenance/FRESH_INSTALL_rfdiffusion_20261003.txt` and `../provenance/FRESH_INSTALL_boltz_20261003.txt`. Read `../docs/FRESH_ENVIRONMENT_TEST_20261003.md` for the test boundary.

## Installation commands

Install Conda, git and a working Windows NVIDIA driver first. In WSL, `nvidia-smi` must work. Put the package, external source, environments, temporary files and caches on a disk with at least 80 GiB free. The tested hardware/runtime is documented in `../docs/REPRODUCTION_TEST_20261003.md`; this is not a blanket minimum-driver guarantee for all CUDA builds.

From the package root in WSL:

```bash
bash src/setup_external_sources.sh
bash src/install_gpu_environment.sh rfdiffusion "$PWD/.envs"
bash src/install_gpu_environment.sh boltz "$PWD/.envs"
```

The installer refuses to overwrite an existing environment. Failed attempts retain logs and partial environments for diagnosis. Use a new environment root for another independent attempt. Set `CONDA_EXE` if Conda is not on PATH. Set `EXTERNAL_ROOT` consistently for source setup and environment installation if using a custom source directory.

If the exact Python interpreter is already installed, set `BOOTSTRAP_PYTHON` to its executable to create an isolated venv instead of installing another Conda interpreter. This does not enable `--system-site-packages`. A venv shares its base interpreter/OS libraries, so its test is not a new-OS or new-driver test.

For a complete separately acquired wheelhouse, set `WHEELHOUSE` to its absolute path. Dependency installation then uses `--no-index`; the DGL requirement is resolved from the wheelhouse rather than redownloaded. Source retrieval for RF still requires the pinned source checkouts. Wheels and weights are not included in this code ZIP. Our test may reuse downloaded wheel archives, but never copies installed `site-packages` into the new environment.

Configure `src/local_paths.sh` with these new interpreters, source directories and cache path. Run `run_full.ps1 -CheckOnly`, followed by a separate `-Spans 15 -SmokeTest` run. Online MSA submits the input protein sequences to `https://api.colabfold.com`; obtain data authorization before running it.

The example local configuration uses the gitignored `.envs` directory under the package root. Place the package on the intended spacious disk first. Set `GPU_ENV_ROOT` to the actual installation root when it differs. The normal Conda/network branch is an installation recipe, not a tested clean-machine acceptance claim. The wheelhouse/bootstrap branch reuses only the base Python interpreter and original wheel archives, not the former installed dependencies. See the test record for the branch actually exercised.

Windows lightweight environment (use an installed Python 3.12.14 interpreter):

```powershell
python -m venv E:\ADAR2_review_env
E:\ADAR2_review_env\Scripts\python.exe -m pip install -r environments\windows_review_venv-test-pins.txt
powershell -ExecutionPolicy Bypass -File .\run.ps1 -Python E:\ADAR2_review_env\Scripts\python.exe
```

## External system tools

Vina and AutoDockTools are separate from the Python dependency lists. The current test used Vina 1.1.2 and MGLTools/ADT 1.5.6; the historical supplemental report describes ADT 1.5.7. Do not relabel either version as the other. Follow `../REPRODUCE_FROM_ZERO.md` for `ADT_PYTHON`, `ADT_UTILITIES` and `VINA_EXE`. Obtain installers only from the official Scripps sources linked in `../THIRD_PARTY_SOFTWARE.md`. Conda, OS packages and Windows drivers are external prerequisites, not bundled binaries.
