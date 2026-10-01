# Third-party software disclosure

| Software or service | Version or identifier | License/terms and official source | Use | Distribution in this package |
| --- | --- | --- | --- | --- |
| RFdiffusion | `86507b6538f51fce57b5a72477165f03999ed7ae` | BSD; https://github.com/RosettaCommons/RFdiffusion | Backbone generation | Configuration and invocation only |
| ProteinMPNN | `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57` | MIT; https://github.com/dauparas/ProteinMPNN | Linker sequence design | Configuration and invocation only |
| Boltz | 2.2.1, Boltz-2 model | MIT; https://github.com/jwohlwend/boltz | Full-fusion prediction | Inputs, outputs, parameters; weights excluded |
| ColabFold MMseqs2 API | online service | Official project and citations: https://github.com/sokrypton/ColabFold | Production-batch MSA generation | Derived records and returned MSA files only |
| AutoDock Vina | 1.1.2 | Apache-2.0; https://github.com/ccsb-scripps/AutoDock-Vina | PT-179/MIQ docking | Parameters and outputs; binary excluded |
| RCSB PDB | 5ED1, 8TNQ, 8TNR, 8TNP, MIQ | RCSB PDB data policies: https://www.rcsb.org/pages/policies | Structural references | Required reference structures with accession provenance |

Each third-party component remains governed by its original license or terms of use. The package does not claim ownership of pretrained model code, model weights, public PDB records, or service implementations.

