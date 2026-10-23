"""Keep the Sphinx LaTeX support files when sphinx-toolbox writes documents."""


def setup(app):
    """Restore the asset-copy step omitted by sphinx-toolbox's LaTeX builder."""
    from sphinx_toolbox.latex import PatchedLaTeXBuilder

    original_write = PatchedLaTeXBuilder.write

    def write_with_assets(self, *args, **kwargs):
        original_write(self, *args, **kwargs)
        self.copy_assets()

    PatchedLaTeXBuilder.write = write_with_assets
    return {"version": "1"}
