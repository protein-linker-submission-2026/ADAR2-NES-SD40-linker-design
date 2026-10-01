# Data sources and provenance

## Construct sequence

The full ADAR2DD(E488Q)-NES-linker-SD40 construct sequence was derived from the project construct design. Only the ten linker residues were treated as designable. The identity-bearing source file is not included in the anonymous package; the final sequence boundaries and checksums are documented in the pipeline records.

## Public structural data

The project uses public Protein Data Bank structures including 5ED1 for ADAR2DD preparation and 8TNQ for SD40 and PT-179/MIQ structural reference. 8TNR and 8TNP were consulted as related structural references. PDB entries are redistributed only as needed for reproducibility and remain subject to RCSB PDB data-use terms.

## MSA generation

The cross-distance production batch used online MMseqs2/ColabFold MSA generation. The earlier 16 A sensitivity batch used a single-sequence MSA. These batches are labeled separately and are not treated as a pure distance comparison.

## Included and excluded data

All derived candidate tables, model-level metrics, final RFdiffusion backbones, and all 588 Boltz-2 PDB structures used in the main analysis are included. Large intermediate A3M/NPZ arrays, model caches, pretrained weights, Conda environments, temporary files, and duplicate artifacts are retained in the separate full archive and indexed in `provenance/source_inventory.csv`.

## Leakage control

The project does not train a new model and therefore has no project-specific train/validation/test split. Public pretrained models were used as inference tools. Candidate evaluation uses structure and docking criteria derived from the stated references and thresholds; it is not an estimate from a hidden experimental test set.

