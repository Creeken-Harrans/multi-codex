"""Strategy registry."""

from .competitive import CompetitiveGenerationStrategy
from .council import CouncilStrategy
from .debate import DebateStrategy
from .map_reduce import MapReduceStrategy
from .role_split_review import RoleSplitReviewStrategy
from .slice_split_impl import SliceSplitImplementationStrategy

STRATEGIES = [
    MapReduceStrategy(),
    RoleSplitReviewStrategy(),
    SliceSplitImplementationStrategy(),
    CompetitiveGenerationStrategy(),
    DebateStrategy(),
    CouncilStrategy(),
]
