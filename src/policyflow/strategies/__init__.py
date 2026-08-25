"""Built-in resolution strategies."""

from .collect_all import CollectAll
from .collect_resolved_scopes import CollectResolvedScopes
from .first_match import FirstMatch
from .protocol import ResolutionStrategy
from .scope_traversal import ScopeTraversalStrategy
from .stop_on_first_resolved_scope import StopOnFirstResolvedScope

__all__ = [
    "CollectAll",
    "CollectResolvedScopes",
    "FirstMatch",
    "ResolutionStrategy",
    "ScopeTraversalStrategy",
    "StopOnFirstResolvedScope",
]
