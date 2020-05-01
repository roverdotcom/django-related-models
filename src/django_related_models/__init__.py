"""
Bundle all of the core functionality from this application.

Modules:
========
related_models: Fetch all related models of an instance and their data.

Miscellaneous objects:
======================
    Except the above, all other objects in this module are to be considered implementation details.
"""

__author__ = (
    'Marius Mucenicu <marius_mucenicu@rover.com>',
    'Mihai Gociu <mihai_gociu@rover.com>',
    'Mike Hansen <mike@rover.com>',
)

__version__ = '0.1.1'

__all__ = [
    'get_related_objects',
    'get_related_objects_mapping',
    'RelatedModels',
]

from .related_models import RelatedModels
from .related_models import get_related_objects
from .related_models import get_related_objects_mapping
