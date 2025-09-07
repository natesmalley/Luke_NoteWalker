"""
Apple Notes Research Bot - AI-powered research assistant for Apple Notes
"""

__version__ = "1.0.0"
__author__ = "CoralCollective"

from .monitor import NotesMonitor
from .analyzer import ContentAnalyzer
from .research_engine import ResearchEngine
from .formatter import NoteFormatter
from .config import Config

__all__ = [
    'NotesMonitor',
    'ContentAnalyzer', 
    'ResearchEngine',
    'NoteFormatter',
    'Config'
]