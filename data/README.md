# Data statement

## Sources and acquisition

- Project construct sequence: supplied project design; used to define ADAR2DD(E488Q), NES, linker, and SD40 boundaries. The identity-bearing source document is excluded from this anonymous package.
- RCSB PDB entries: 5ED1, 8TNQ, 8TNR, and 8TNP; acquired during the September 2026 workflow for structural preparation, comparison, and audit.
- RCSB Chemical Component Dictionary entry MIQ: used to verify PT-179/MIQ bond order, elements, and stereochemistry.
- MMseqs2/ColabFold MSA: online service output used for the 11-20 A production batch. The earlier 16 A sensitivity batch used a single-sequence MSA and is labeled separately.

Public structures and chemical-component records remain governed by RCSB PDB data-use policies. MMseqs2/ColabFold output remains governed by the service and upstream software terms. Accession-level provenance and links are listed in `DATA_SOURCES.md` and `THIRD_PARTY_SOFTWARE.md`.

## Preparation

Reference preparation selected the documented chains and residue ranges, removed unrelated complex components where required, and preserved candidate-to-source mappings. Exact chain, coordinate-unit, residue-boundary, hydrogen, and protonation conventions are in `docs/STRUCTURE_FILES.md` and the stage logs.

## Leakage and deduplication

No project-specific model was trained, so there is no project train/validation/test split. Candidate sequences were deduplicated before downstream evaluation. The historical single-sequence-MSA batch is not pooled with the online-MMseqs2 production batch for distance-effect claims. Identity-bearing source files are excluded from the anonymous submission.

## Package placement

Large scientific inputs are stored under `references/`, while this directory provides the Attachment 5 data-source and license statement. Derived tables are under `results/`; commands and parameters are under `src/`, `methods/`, and `logs/`.
