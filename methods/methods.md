# Methods and thresholds

The cross-distance analysis uses only the online MMseqs2 batch for 11–20 Å.

1. Generate three RFdiffusion backbones per target span.
2. Request thirty ProteinMPNN linker sequences per span and retain unique sequences.
3. Apply sequence-composition QC.
4. Predict three Boltz-2 models per candidate.
5. Require linker C-alpha RMSD strictly below 2.0 Å in at least two of three models.
6. Require AutoDock Vina best score at or below -6.0 kcal/mol in at least two of three models.
7. Score SD40 geometry per model with 100 × (0.3×S_RMSD + 0.3×S_contact + 0.4×S_clash).
8. Use the median of three model scores as the candidate final score.
9. Compare formally scored candidates with the GGGGSGGGGS baseline score of 24.1035.
