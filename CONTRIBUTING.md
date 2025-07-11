## Getting started

### Clone this repo

```bash
git clone git@orahub.oci.oraclecorp.com:adbs/python-select-ai.git
cd python-select-ai
```

### Install development dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install --upgrade pip setuptools build pre-commit

python3 -m pip install -e . # installs project in editable mode

pre-commit install # install git hooks
pre-commit run --all-files
```

### Build


```bash
python -m build
```
