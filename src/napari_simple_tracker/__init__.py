from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("napari-simple-tracker")
except PackageNotFoundError:
    # Fallback for editable/local use before installation metadata exists.
    __version__ = "0+unknown"

__all__ = ["__version__"]
