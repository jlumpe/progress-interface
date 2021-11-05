"""Utilities for testing."""

import typing as t

from .base import AbstractProgressMonitor, ProgressConfig, progress_config


def capture_progress(config: ProgressConfig) -> t.Tuple[ProgressConfig, t.List[AbstractProgressMonitor]]:
	"""
	Creates a ``ProgressConfig`` which captures references to the progress monitor instances created
	with it.

	This is intended to be used for testing functions which create progress monitor instances
	internally that normally would not be accessible by the caller. The captured instance can be
	checked to ensure it has the correct attributes and went through the full range of iterations,
	for example.

	Returns
	-------
	Tuple[ProgressConfig, List[AbstractProgressMonitor]]
		The first item is a modified ``ProgessConfig`` instance which can be passed to the function
		to be tested. The second is a list which is initially empty, and is populated with progress
		monitor instances as they are created by it.
	"""
	instances = []

	def factory(total, **kw):
		monitor = config.create(total, **kw)
		instances.append(monitor)
		return monitor

	return progress_config(factory), instances


class TestProgressMonitor(AbstractProgressMonitor):
	"""Progress monitor which displays no user information but does track progress information.

	To be used for testing.
	"""

	# This prevents pytest from trying to collect this class as a test
	__test__ = False

	def __init__(self, total: int, initial: int = 0, allow_decrement: bool = True, **kw):
		self.n = initial
		self.total = total
		self.allow_decrement = allow_decrement
		self.kw = kw
		self.closed = False

	def increment(self, delta: int = 1):
		self.moveto(self.n + delta)

	def moveto(self, n: int):
		if self.closed:
			raise RuntimeError('Attempted to moveto closed progress monitor.')
		if n < 0:
			raise ValueError(f'Attempted to set n to negative value {n}')
		if n > self.total:
			raise ValueError(f'Attempted to set n to {n}, total is {self.total}')
		if not self.allow_decrement and n < self.n:
			raise ValueError(f'Attempted to decrease n from {self.n} to {n} with allow_decrement=False')
		self.n = n

	def close(self):
		self.closed = True

	@classmethod
	def create(cls, total: int, initial: int = 0, **kw):
		return cls(total, initial, **kw)
