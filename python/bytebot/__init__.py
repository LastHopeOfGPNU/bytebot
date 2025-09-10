"""Bytebot - Open-Source AI Desktop Agent.

A Python implementation of the Bytebot AI desktop agent system.
"""

__version__ = "0.1.0"
__author__ = "Bytebot Team"
__email__ = "team@bytebot.ai"
__license__ = "Apache-2.0"

# Re-export commonly used classes and functions
from .core.config import settings
from .core.logging import get_logger

__all__ = [
    "settings",
    "get_logger",
    "__version__",
]