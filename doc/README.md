# Building the documentation

Run these commands from the repository root in your virtual environment:

```bash
python -m pip install -e .
python -m pip install -r doc/requirements.txt
python -m sphinx -b html -n -W --keep-going doc/source doc/build/html
```

The strict build checks cross-references and treats warnings as errors.
Intersphinx downloads reference inventories from the Python and pandas
documentation sites, so the first build requires network access.

Open `doc/build/html/index.html` to review the local site. To refresh the
checked-in HTML under `docs/`, use a separate doctree cache:

```bash
python -m sphinx -b html -n -W --keep-going -d doc/build/doctrees doc/source docs
```

The Makefile targets run from `doc/`:

```bash
make -C doc html
make -C doc epub
make -C doc pdf
```

PDF generation additionally requires a LaTeX installation with `latexmk`.
See [Sphinx](https://www.sphinx-doc.org/) for builder options.
