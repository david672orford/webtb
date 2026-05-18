import importlib.metadata

try:
    __version__ = importlib.metadata.version("webtb")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.1.0"
