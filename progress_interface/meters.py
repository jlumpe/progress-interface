"""Progress meter implementations."""

import typing as t

from .base import AbstractProgressMeter, register


class TestProgressMeter(AbstractProgressMeter):
	"""Progress meter which displays no user information but does track progress information.

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
			raise RuntimeError('Attempted to moveto closed progress meter.')
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


@register('tqdm')
class TqdmProgressMeter(AbstractProgressMeter):
	"""Wrapper around a progress meter from the ``tqdm`` library."""

	def __init__(self, pbar: 'tqdm.std.tqdm'):
		self.pbar = pbar

	@property
	def n(self):
		return self.pbar.n

	@property
	def total(self):
		return self.pbar.total

	@property
	def closed(self):
		return False  # TODO

	def increment(self, delta: int = 1):
		self.pbar.update(delta)

	def moveto(self, n: int):
		self.pbar.moveto(n)

	def close(self):
		self.pbar.close()

	@classmethod
	def create(cls,
	           total: int,
	           *,
	           initial: int = 0,
	           desc: t.Optional[str] = None,
	           file: t.Optional[t.TextIO] = None,
	           **kw,
	           ):
		from tqdm import tqdm
		return cls(tqdm(total=total, desc=desc, initial=initial, file=file, **kw))


@register('click')
class ClickProgressMeter(AbstractProgressMeter):
	"""Wrapper around a progress bar from the ``click`` library."""

	def __init__(self, pbar):
		self.pbar = pbar

	@property
	def n(self):
		return self.pbar.pos

	@property
	def total(self):
		return self.pbar.length

	@property
	def closed(self):
		return self.pbar.finished

	def increment(self, delta: int = 1):
		self.pbar.update(delta)

	def moveto(self, n: int):
		self.pbar.update(n - self.pbar.pos)

	def close(self):
		self.pbar.finish()

	@classmethod
	def create(cls,
	           total: int,
	           *,
	           initial: int = 0,
	           desc: t.Optional[str] = None,
	           file: t.Optional[t.TextIO] = None,
	           **kw,
	           ):
		import click
		pbar = click.progressbar(length=total, label=desc, file=file, **kw)
		if initial != 0:
			pbar.update(initial)
		return cls(pbar)
