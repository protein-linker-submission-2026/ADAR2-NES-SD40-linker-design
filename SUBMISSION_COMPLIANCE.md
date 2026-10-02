# Attachment 5 compliance matrix

This matrix maps the official code-submission requirements to evidence inside the anonymous package. It does not replace the official project evaluation form or narrated presentation.

Status correction (2026-10-02): document presence and lightweight validation do not establish clean-machine end-to-end reproducibility. See `docs/REPRODUCIBILITY_STATUS.md`. PASS entries below refer only to the stated package evidence, not certification by the competition.

| Requirement | Status | Package evidence |
| --- | --- | --- |
| README and complete commands | PASS | `README.md`, `JUDGES_GUIDE.md`, `REPRODUCE_FROM_ZERO.md` |
| Exact lightweight dependencies | PASS | `requirements.txt`, `environment.yml` |
| Full software, OS, CUDA, driver, and hardware versions | PARTIAL; archived principal versions present, full inference lock pending | `docs/VERSIONS.md`, historical `logs/`, `docs/REPRODUCIBILITY_STATUS.md`; current organizer computer is not production evidence |
| Data source, acquisition, purpose, license, and preprocessing | PASS | `data/README.md`, `DATA_SOURCES.md`, `docs/DATA_SOURCES.md` |
| Leakage and deduplication controls | PASS | `data/README.md`, `DATA_SOURCES.md` |
| Core source code | PASS | `src/`, `methods/`, `ranker/` |
| Main executable entry | PASS | quick review: `run.sh`, `run.ps1`, `predict.py`; full clean-machine flow: `run_full.ps1` |
| Model versions and weight/invocation instructions | PASS | `models/README.md`, `MODEL_CARD.md`, `THIRD_PARTY_SOFTWARE.md`, `src/setup_external_sources.sh` |
| Executable demonstration notebook | PASS | `notebooks/workflow_demo.ipynb` |
| Standardized machine-readable output | PASS | `results/results.csv`, `results/results.xlsx` |
| Candidate ID, track, sequence, metrics, versions, and notes | PASS | columns in `results/results.csv` |
| Structure files correspond to result rows | PASS | relative RFdiffusion and three-model Boltz-2 PDB columns in `results/results.csv` |
| Chain, units, residue ranges, and protonation conventions | PASS | `docs/STRUCTURE_FILES.md` |
| Logs, parameters, and seeds | PASS | `logs/`, `results/inputs/`, `results/state/` |
| Model Card and limitations | PASS | `MODEL_CARD.md`, `results/report.pdf` |
| Ranking logic and uncertainty | PASS | `methods/methods.md`, `MODEL_CARD.md`, `results/report.pdf` |
| Third-party tools, services, dates, parameters, and outputs | DISCLOSED; historical MGLTools patch version unverified | `THIRD_PARTY_SOFTWARE.md`, `docs/VERSIONS.md`, `src/`, `logs/`, `results/` |
| Clean-machine design to final-list demonstration | NOT YET VERIFIED | Entry and instructions supplied; no fresh-install GPU-to-docking acceptance record |
| Third-party weight redistribution | NOT REQUIRED | exact official retrieval/call method supplied; final project structures and result tables included |
| Anonymous, relative-path package | PASS after validation | `validate_submission.py`, `provenance/` |
| Wet-laboratory work | TEAM-CONFIRMED; evidence not included here | Separate experimental methods, raw data, statistics and conclusions remain to be supplied |

Run `bash run.sh` or `powershell -ExecutionPolicy Bypass -File .\run.ps1` for lightweight evidence validation. Run `run_full.ps1 -CheckOnly` after installing GPU and docking dependencies, then `run_full.ps1` for a fresh design-to-final-list calculation. A valid lightweight package prints `VALIDATION PASS` and verifies required files, record counts, 588 Boltz-2 PDB files, structure-row mappings, and forbidden identity/path patterns.
