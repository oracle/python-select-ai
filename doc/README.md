Sphinx is used to generate documentation

```text
python -m pip install -r requirements.txt
```

For more information on Sphinx, please visit this page:

http://www.sphinx-doc.org

Once Sphinx is installed, the supplied Makefile can be used to build the
different targets, for example to build the HTML documentation, run::

    make

To make ePub documentation, run::

    make epub

To make PDF documentation, run::

    make pdf

The program ``latexmk`` may be required by Sphinx to generate PDF output.
