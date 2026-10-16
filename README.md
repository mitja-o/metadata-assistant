# `massi` - a multi-agent metadata construction prototype

This is the repository behind `massi` - a prototype LLM-based multi-agent system for metadata construction.

The general idea is to, given a dataset with one or more data files and a target metadata schema, construct a valid metadata instance.

## Directory structure

- [`massi/`](./massi/) - implementation of the prototype system.
- [`evaluation/`](./evaluation/) - the local evaluation evaluation framework.
- [`analysis/`](./analysis/) - notebooks for analysis of the evaluation results.
- [`_data/`](./_data/) - instrumental directory for the downloaded evaluation dataset.

## Tooling

Various development utilities are collected in the `Makefile`.
Here are the highlighted few:

### Development utilities

- `make format` - format the source code.
- `make check` - type check the source code.
- `make test` - run `massi` software tests: e.g. unit tests, doctests, ...
- `make clean-build` - build `massi` source code.

### Evaluation utilities

- `make evaluate` - unpack the evaluation dataset and run the evaluation framework

### Local infrastructure

- `make prep-analysis` - make sure evaluation results are available for analysis.
- `make start-local-notebook` - start a local Jupyter Lab, e.g. for analysis runs.

## Dependencies

Here is what is needed for working on this repository:

### Libraries

- All project library dependencies are managed using `uv` package manager in `pyproject.toml`.  
  To set up your local environment, run: `uv init`.

### Environmental variables

- The current evaluation setup uses external LLM APIs.  
  To access them, please copy `.env.example` into `.env` and fill in your values.  
  You can also use it to configure alternative LLM backends.

### System requirements

- The `massi` prototype does not require any special system configurations and relies on libraries discussed above.
- Analysis notebooks in `analysis/` directory do use local GPUs for analyses and may request up to `24GB` RAM.