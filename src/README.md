# Source-code notes

`run_pipeline.sh` is the primary full-pipeline entry point. Installation paths and executable locations are read from `pipeline_config.sh` and can be overridden with environment variables.

The other runner scripts are retained as provenance for individual production and recovery batches. Paths appearing in historical logs describe the original local execution environment and are not required by the lightweight `predict.py` result-generation entry point.

Pretrained third-party repositories and model weights are not redistributed. Install them according to their official documentation and set the corresponding environment variables before starting GPU-intensive stages.
