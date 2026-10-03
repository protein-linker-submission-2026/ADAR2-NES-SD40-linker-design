# Third-party software disclosure

| Software or service | Version or identifier | License/terms and official source | Use | Distribution in this package |
| --- | --- | --- | --- | --- |
| RFdiffusion | `86507b6538f51fce57b5a72477165f03999ed7ae` | BSD; https://github.com/RosettaCommons/RFdiffusion | Backbone generation | Configuration and invocation only |
| NVIDIA SE3Transformer (independent test environment) | DeepLearningExamples `729963dd47e7c8bd462ad10bfac7a7b0b604e6dd`, `DGLPyTorch/DrugDiscovery/SE3Transformer` | Retain upstream component license notices; https://github.com/NVIDIA/DeepLearningExamples | RFdiffusion dependency in the 2026-10-03 independent test, not asserted as historical production provenance | Fixed source retrieval and installation instructions; source is not redistributed here |
| ProteinMPNN | `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57` | MIT; https://github.com/dauparas/ProteinMPNN | Linker sequence design | Configuration and invocation only |
| Boltz | 2.2.1, Boltz-2 model | MIT; https://github.com/jwohlwend/boltz | Full-fusion prediction | Inputs, outputs, parameters; weights excluded |
| ColabFold MMseqs2 API | Historical server build and database snapshot unverified; invoked by Boltz 2.2.1 | Official project and citations: https://github.com/sokrypton/ColabFold | Production-batch MSA generation | Returned MSA and logs in full archives; detailed evidence in `docs/ONLINE_MSA_PROVENANCE.md` |
| AutoDock Vina | 1.1.2 | Apache-2.0; https://github.com/ccsb-scripps/AutoDock-Vina | PT-179/MIQ docking | Parameters and outputs; binary excluded |
| MGLTools / AutoDockTools | 1.5.7 reported for project-specified installation in the 2026-10-02 team audit; historical continuity unverified | Component-specific licenses; https://ccsb.scripps.edu/mgltools/downloads/ | Receptor/ligand preparation; configured through `ADT_PYTHON` and `ADT_UTILITIES` | Invocation code only; installation excluded; see `docs/ENVIRONMENT_VERIFICATION_SUPPLEMENT.md` |
| RCSB PDB | 5ED1, 8TNQ, 8TNR, 8TNP, MIQ | RCSB PDB data policies: https://www.rcsb.org/pages/policies | Structural references | Required reference structures with accession provenance |

Each third-party component remains governed by its original license or terms of use. The package does not claim ownership of pretrained model code, model weights, public PDB records, or service implementations.

## Recorded invocation and key parameters

The formal 11-20 A production batch was run in September 2026. Per-job timestamps, inputs, output paths, and console records are retained under `logs/` and in the full reproduction release. The reproducible invocation is encoded in `src/run_single_span.sh`, `src/docking_helper.py`, and `src/pipeline_config.sh`.

| Component | Recorded input and key parameters |
| --- | --- |
| RFdiffusion | Prepared ADAR2DD(E488Q)-NES and SD40 pose; contig `[A1-393/11/A394-428]`; three deterministic backbones per 11-20 A span; design indices/seeds 0, 1, 2 |
| ProteinMPNN | One validated RF backbone; only A394-A403 designed; 10 samples per backbone; temperature 0.15; per-backbone fixed seed; C/K/R biases −0.30/−0.10/−0.10 |
| ColabFold MMseqs2 | Full 439-aa fusion sequence; online MSA at `https://api.colabfold.com`; greedy pairing; returned MSA/status records retained |
| Boltz-2 | Full fusion sequence plus MSA; 3 recycling steps; 200 sampling steps; 3 diffusion samples; one parallel sample; full PAE; inference potentials; no optional kernels; SHA256-derived candidate seed |
| AutoDock Vina | Complete A1-A439 Boltz receptor and MIQ/PT-179 ligand; model-specific 36-residue SD40 box plus 5 A per-side margin; exhaustiveness 32; 9 modes; energy range 3 kcal/mol; deterministic candidate/model seed |

No commercial API or private model endpoint was used. The public MMseqs2 service is the only network inference dependency in the formal batch. No prompt-based generative service was used to generate candidate sequences or scores.

Online MSA evidence and limits are documented in `docs/ONLINE_MSA_PROVENANCE.md`. Client version, server software build and database snapshot are distinct. No verified historical server/database version was found; current service versions must not be substituted. Logs retain job identifiers, status and retries, but not every API request has an absolute timestamp.

