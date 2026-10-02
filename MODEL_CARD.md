# Model card

## System purpose

This project ranks ten-residue linker candidates for an ADAR2DD(E488Q)-NES-linker-SD40 fusion construct. It combines pretrained structure-generation, sequence-design, structure-prediction, docking, and project-specific geometry-ranking components.

## Components

| Component | Version | Project use |
| --- | --- | --- |
| RFdiffusion | commit `86507b6538f51fce57b5a72477165f03999ed7ae` | Generate linker backbones under fixed-domain geometry |
| ProteinMPNN | commit `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57` | Design the ten linker residues on each backbone |
| Boltz | package 2.2.1, model Boltz-2 | Predict three full-fusion structures per candidate |
| AutoDock Vina | 1.1.2 | Screen PT-179/MIQ docking around SD40 |
| SD40 Linker Ranker | project version 0.1.0 | Score SD40 RMSD, reference-contact recovery, and clashes |

No component was newly trained or fine-tuned for this project. The project contribution is the fusion-construct definition, fixed-domain/linker design strategy, QC rules, multi-model gating, PT-179/SD40 evaluation, geometry ranker, and reproducible evidence chain.

## Inputs and outputs

Inputs include the fusion-protein sequence, prepared public PDB structures, target endpoint spans, and software configuration. Outputs include linker sequences, RFdiffusion backbones, Boltz-2 structures, RMSD and Vina gates, and candidate rankings.

## Intended use

The system is intended for computational hypothesis generation and prioritization alongside laboratory work. The team confirms accompanying wet-laboratory work; its methods, raw data and conclusions are outside this computational package. It is not a clinical, diagnostic, or therapeutic decision system.

## Known limitations

- Structure predictions depend on model and MSA quality.
- Linker RMSD measures consistency with an RFdiffusion backbone, not functional activity.
- Vina scores are approximate screening scores, not measured affinities.
- The geometry ranker uses project-defined weights and requires experimental calibration.
- Candidate ranking does not establish expression, stability, localization, editing activity, specificity, or safety.

