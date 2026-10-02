# Model and weight acquisition

This project used pretrained third-party models only. No RFdiffusion, ProteinMPNN, or Boltz-2 weights were trained or fine-tuned for this submission.

| Component | Recorded version | Weight or invocation method |
| --- | --- | --- |
| RFdiffusion | commit `86507b6538f51fce57b5a72477165f03999ed7ae` | Install from the official RosettaCommons RFdiffusion repository and obtain the official inference checkpoints according to its model-download instructions. Set `RFDIFFUSION_DIR` and `RFDIFFUSION_PYTHON`. |
| ProteinMPNN | commit `8907e6671bfbfc92303b5f79c4b5e6ce47cdef57` | Install from the official ProteinMPNN repository and use its distributed `v_48_020` weights. Set `PROTEIN_MPNN_DIR` and `PROTEIN_MPNN_PYTHON`. |
| Boltz-2 | `boltz==2.2.1` | Install the package, then invoke `boltz predict --model boltz2`; the official client downloads weights into the directory supplied by `--cache`. Production used `--no_kernels`. Set `BOLTZ_EXE`, `BOLTZ_PYTHON`, and `BOLTZ_CACHE`. |
| SD40 Linker Ranker | project version 0.1.0 | Project code and configuration are included under `ranker/`; it uses no learned project weight. |

Official sources, licenses, model roles, and public-data services are listed in `THIRD_PARTY_SOFTWARE.md`. Exact installation and execution steps are in `REPRODUCE_FROM_ZERO.md`. Configurable paths are in `src/pipeline_config.sh` and `src/local_paths.example.sh`; the maintained full entry point is `run_full.ps1`.

`src/setup_external_sources.sh` retrieves the exact RFdiffusion and ProteinMPNN source revisions, downloads the required RFdiffusion `Base_ckpt.pt`, and verifies ProteinMPNN `v_48_020.pt`. Boltz 2.2.1 downloads its official Boltz-2 checkpoint and molecular cache on first prediction through the configured `BOLTZ_CACHE` directory.

Recorded weight checksums:

- RFdiffusion `Base_ckpt.pt`: SHA256 `0fcf7d7c32b4848030aca3a051e6768de194616f96ba6c38186351a33bfc6eca`
- ProteinMPNN `vanilla_model_weights/v_48_020.pt`: SHA256 `c9cb4a671d79604111231f8dbfc7c590e06f1197453b7a6854ac6661a642f5bd`

Third-party weights are excluded to avoid unauthorized redistribution, multi-gigabyte duplication, and accidental inclusion of mutable software caches. Their absence does not prevent result inspection: all final structures and standardized result tables used in the report are included.
