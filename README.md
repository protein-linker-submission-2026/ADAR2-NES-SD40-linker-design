# ADAR2 NES SD40 Linker Design Competition Submission

This is the anonymous reproducibility package for the ADAR2DD(E488Q)-NES-linker-SD40 computational design project. It contains the complete derived result tables, all final RFdiffusion and Boltz-2 PDB structures, docking and RMSD evidence, analysis code, key logs, a journal-style report, and provenance manifests.

## Main result

The online MMseqs2 batch covers target spans from 11 to 20 A. It contains 302 candidate-level records and 588 Boltz-2 model-level records. Twenty-two candidates scored strictly above the GGGGSGGGGS baseline. The current top candidate is LRELLERLLT at 15 A with a median ranker score of 60.5687.

These are computational screening results. Vina scores are internal screening metrics and are not experimental binding free energies. Final selection requires expression, binding, editing-activity, localization, and cytotoxicity experiments.

## Package contents

```text
README.md
requirements.txt
environment.yml
run.sh
run.ps1
predict.py
validate_submission.py
MODEL_CARD.md
DATA_SOURCES.md
THIRD_PARTY_SOFTWARE.md
notebooks/
  workflow_demo.ipynb
src/
  Full pipeline, QC, docking, and ranking source code
methods/
  Report rebuild code and documented thresholds
results/
  results.xlsx
  results.csv
  all_candidate_records.csv
  all_model_records.csv
  top_candidates_above_baseline.csv
  span_summary.csv
  report.pdf
  figures/
  structures/rfdiffusion/
  structures/boltz2/
  rmsd/
  docking/
logs/
  Key run logs and parameter records
provenance/
  Source inventory, validation report, anonymization report, and checksums
archive_reference/
  Full-archive location and integrity information
```

## Quick reproduction

The lightweight entry point rebuilds the standardized candidate list from the included candidate-level table without rerunning GPU-intensive models.

Linux or WSL:

```bash
bash run.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Equivalent direct command:

```bash
python predict.py --input results/all_candidate_records.csv --output results/results.csv
python validate_submission.py
```

## Full computational pipeline

The full GPU pipeline is preserved under `src/`. It requires separately installed RFdiffusion, ProteinMPNN, Boltz-2, and AutoDock Vina environments. Their source code and pretrained weights are not redistributed in this package. Configure installation paths in `src/pipeline_config.sh`, then run:

The main paths are configurable through `RFDIFFUSION_DIR`, `RFDIFFUSION_PYTHON`, `PROTEIN_MPNN_DIR`, `PROTEIN_MPNN_PYTHON`, `BOLTZ_EXE`, `BOLTZ_PYTHON`, `BOLTZ_CACHE`, and `VINA_WSL_EXE`. The submission does not depend on a participant-specific home directory.

```bash
bash src/run_pipeline.sh --check-only
bash src/run_pipeline.sh --run-expensive rf
bash src/run_pipeline.sh --run-expensive mpnn
bash src/run_pipeline.sh --run-expensive boltz
```

Docking is a separately reviewed stage because receptor and ligand PDBQT preparation must be checked before Vina execution. See the source comments and `methods/methods.md`.

## Decision rules

- Three RFdiffusion backbones per target span.
- ProteinMPNN sequences are designed only at the ten linker positions.
- Three Boltz-2 models per candidate.
- Linker C-alpha RMSD must be strictly below 2.0 A in at least two of three models.
- Vina best score must be at or below -6.0 kcal/mol in at least two of three models.
- Per-model geometry score: `100 * (0.3*S_RMSD + 0.3*S_contact + 0.4*S_clash)`.
- Candidate score: median of the three model scores.
- Baseline sequence: GGGGSGGGGS, online-batch score 24.1035.

## Anonymity and integrity

This package intentionally excludes Git history, account names, personal names, institutional identifiers, API keys, and local absolute paths. Scientific sequences, coordinates, random seeds, scores, and numeric arrays are not modified during anonymization. Run `validate_submission.py` before upload and keep the generated SHA256 file with the submitted ZIP.

## Large files

All final PDB structures used in the reported analysis are included. Large intermediate MSA arrays, model caches, Conda environments, pretrained weights, duplicate artifacts, and temporary files remain in the separately preserved full archive and are indexed by relative path and SHA256 in `provenance/source_inventory.csv`.

