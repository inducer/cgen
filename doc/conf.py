extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx_copybutton",
    #"sphinx.ext.viewcode"
    ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix of source filenames.
source_suffix = ".rst"

# The encoding of source files.
#source_encoding = "utf-8"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "cgen"
copyright = "2011, Andreas Kloeckner"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
ver_dic = {}
exec(compile(open("../cgen/version.py").read(), "../cgen/version.py", "exec"),
        ver_dic)
version = ".".join(str(x) for x in ver_dic["VERSION"])
# The full version, including alpha/beta/rc tags.
release = ver_dic["VERSION_TEXT"]

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_patterns = ["_build"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"


# Options for HTML output
# -----------------------

html_theme = "furo"


autoclass_content = "class"
autodoc_typehints = "description"

intersphinx_mapping = {
        "https://docs.python.org/3/": None,
        "https://numpy.org/doc/stable/": None,
        "https://documen.tician.de/pymbolic/": None,
        }
