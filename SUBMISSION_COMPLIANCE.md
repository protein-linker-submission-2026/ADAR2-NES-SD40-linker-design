# Attachment 5 compliance matrix

This matrix maps the official code-submission requirements to evidence inside the anonymous package. It does not replace the official project evaluation form or narrated presentation.

| Requirement | Status | Package evidence |
| --- | --- | --- |
| README and complete commands | PASS | `README.md`, `run.sh`, `run.ps1`, `src/README.md` |
| Exact lightweight dependencies | PASS | `requirements.txt`, `environment.yml` |
| Full software, OS, CUDA, driver, and hardware versions | PASS | `docs/VERSIONS.md`, `README.md` |
| Data source, acquisition, purpose, license, and preprocessing | PASS | `data/README.md`, `DATA_SOURCES.md`, `docs/DATA_SOURCES.md` |
| Leakage and deduplication controls | PASS | `data/README.md`, `DATA_SOURCES.md` |
| Core source code | PASS | `src/`, `methods/`, `ranker/` |
| Main executable entry | PASS | `run.sh`, `run.ps1`, `predict.py` |
| Model versions and weight/invocation instructions | PASS | `models/README.md`, `MODEL_CARD.md`, `THIRD_PARTY_SOFTWARE.md` |
| Executable demonstration notebook | PASS | `notebooks/workflow_demo.ipynb` |
| Standardized machine-readable output | PASS | `results/results.csv`, `results/results.xlsx` |
| Candidate ID, track, sequence, metrics, versions, and notes | PASS | columns in `results/results.csv` |
| Structure files correspond to result rows | PASS | relative RFdiffusion and three-model Boltz-2 PDB columns in `results/results.csv` |
| Chain, units, residue ranges, and protonation conventions | PASS | `docs/STRUCTURE_FILES.md` |
| Logs, parameters, and seeds | PASS | `logs/`, `results/inputs/`, `results/state/` |
| Model Card and limitations | PASS | `MODEL_CARD.md`, `results/report.pdf` |
| Ranking logic and uncertainty | PASS | `methods/methods.md`, `MODEL_CARD.md`, `results/report.pdf` |
| Third-party tools, services, parameters, and outputs | PASS | `THIRD_PARTY_SOFTWARE.md`, `src/`, `logs/`, `results/` |
| Anonymous, relative-path package | PASS after validation | `validate_submission.py`, `provenance/` |
| Wet-laboratory validation | NOT PERFORMED | explicitly disclosed in `README.md`, `MODEL_CARD.md`, and `results/report.pdf` |

Run `bash run.sh` or `powershell -ExecutionPolicy Bypass -File .\run.ps1` before submission. A valid package prints `VALIDATION PASS` and verifies the required files, record counts, 588 Boltz-2 PDB files, structure-row mappings, and forbidden identity/path patterns.
