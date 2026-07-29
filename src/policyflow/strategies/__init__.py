"""Built-in resolution strategies."""

from .collect_all import CollectAll
from .first_match import FirstMatch
from .protocol import ResolutionStrategy

__all__ = ["CollectAll", "FirstMatch", "ResolutionStrategy"]
