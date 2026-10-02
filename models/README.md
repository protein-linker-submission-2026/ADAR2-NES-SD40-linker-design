# Model and weight acquisition

This project used pretrained third-party models only. No RFdiffusion, ProteinMPNN, or Boltz-2 weights were trained or fine-tuned for this submission.

| Component | Recorded version | Weight or invocation method |
| --- | --- | --- |
| RFdiffusion | commit `86507b6538f51fce57b5a72477165f03999ed7ae` | Install from the official RosettaCommons RFdiffusion repository and obtain the official inference checkpoints according to its model-download instructions. Set `RFDIFFUSION_DIR` and `RFDIFFUSION_PYTHON`. |
| ProteinMPNN | commit `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57` | Install from the official ProteinMPNN repository and use its distributed `v_48_020` weights. Set `PROTEIN_MPNN_DIR` and `PROTEIN_MPNN_PYTHON`. |
| Boltz-2 | `boltz==2.2.1` | Install the package, then invoke `boltz predict --model boltz2`; the official client downloads weights into the directory supplied by `--cache`. Production used `--no_kernels`. Set `BOLTZ_EXE`, `BOLTZ_PYTHON`, and `BOLTZ_CACHE`. |
| SD40 Linker Ranker | project version 0.1.0 | Project code and configuration are included under `ranker/`; it uses no learned project weight. |

Official sources, licenses, model roles, and public-data services are listed in `THIRD_PARTY_SOFTWARE.md`. Exact pipeline commands and configurable paths are in `src/README.md`, `src/pipeline_config.sh`, and `src/run_pipeline.sh`. Third-party weights are excluded to avoid redistribution and multi-gigabyte duplication.
