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

sys.path.insert(0, os.path.join("..", "..", "src", "select_ai"))

autodocs_default_options = {
    "members": True,
    "inherited-members": True,
    "undoc-members": True,
}

project = "Select AI for Python"
copyright = "2025, Oracle and/or its affiliates. All rights reserved."
author = "Oracle"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.autodoc", "sphinx_toolbox.latex"]

# The suffix of source filenames.
source_suffix = ".rst"

# The root toctree document.
root_doc = master_doc = "index"


templates_path = ["_templates"]
exclude_patterns = []
global_vars = {}
local_vars = {}

version_file_name = os.path.join("..", "..", "src", "select_ai", "version.py")
with open(version_file_name) as f:
    exec(f.read(), global_vars, local_vars)
version = ".".join(local_vars["__version__"].split(".")[:2])
# The full version, including alpha/beta/rc tags.
release = local_vars["__version__"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

pygments_style = "sphinx"
