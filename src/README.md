# Source-code notes

The maintained clean-machine entry point is the repository-root `run_full.ps1`, implemented by `run_full_pipeline.ps1`. It coordinates WSL GPU stages, Windows PDBQT preparation and Vina, geometry ranking, and final standardized table generation.

Machine-specific WSL paths are read from `pipeline_config.sh` and may be overridden with environment variables or a gitignored `local_paths.sh` copied from `local_paths.example.sh`.

Key files:

- `setup_external_sources.sh`: clones the exact RFdiffusion and ProteinMPNN revisions and retrieves the required RFdiffusion checkpoint.
- `run_single_span.sh`: resumable WSL runner for one 11-20 A span through Boltz-2 and RMSD, or for post-docking rank/finalization.
- `docking_helper.py`: validates full A1-A439 receptors, prepares model-specific boxes, runs Vina, and applies the 2-of-3 gate.
- `collect_reproduction_results.py`: merges completed span runs into `results.csv` and `results.xlsx`.
- `run_pipeline.sh`: retained stage-development utility; it is not the complete cross-platform reproduction entry point.

The other runner scripts are retained as provenance for individual production and recovery batches. Paths appearing in historical logs describe the original local execution environment and are not required by the lightweight `predict.py` result-generation entry point.

Pretrained third-party repositories and model weights are not redistributed. Install them according to `REPRODUCE_FROM_ZERO.md`, then run `run_full.ps1 -CheckOnly` before starting GPU-intensive stages.
