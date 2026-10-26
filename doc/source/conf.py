# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

import sphinx_prompt

sys.modules["sphinx-prompt"] = sphinx_prompt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "src")
    ),
)

autodoc_default_options = {
    "members": True,
    "inherited-members": True,
    "undoc-members": True,
}

project = "Select AI for Python"
copyright = "2026, Oracle and/or its affiliates. All rights reserved."
author = "Oracle"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_toolbox.latex",
    "sphinx_toolbox_latex_compat",
    "sphinx.ext.autosectionlabel",
]

autosectionlabel_prefix_document = True

# Resolve standard-library and DataFrame API types to their own references.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
}

# The suffix of source filenames.
source_suffix = ".rst"

# The root toctree document.
root_doc = master_doc = "index"


templates_path = ["_templates"]
exclude_patterns = []
global_vars = {}
local_vars = {}

version_file_name = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "src", "select_ai", "version.py"
    )
)
with open(version_file_name) as f:
    exec(f.read(), global_vars, local_vars)
version = ".".join(local_vars["__version__"].split(".")[:2])
# The full version, including alpha/beta/rc tags.
release = local_vars["__version__"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "python_docs_theme"
html_static_path = (
    ["_static"]
    if os.path.isdir(os.path.join(os.path.dirname(__file__), "_static"))
    else []
)

pygments_style = "sphinx"

latex_elements = {
    "maxlistdepth": "10",  # Increase the maximum list nesting depth
}
