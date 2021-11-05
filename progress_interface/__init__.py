"""
Generic interface for displaying progress bars.
"""

__author__ = 'Jared Lumpe'
__email__ = 'mjlumpe@gmail.com'
__version__ = '0.1'

from .base import AbstractProgressMonitor, ProgressConfig, default_config, progress_config, \
	get_progress, register, iter_progress

from . import monitors
