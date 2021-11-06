"""Progress monitor implementations."""

import typing as t
from importlib import import_module

from .base import AbstractProgressMonitor, register


@register('tqdm')
class TqdmProgressMonitor(AbstractProgressMonitor):
	"""Wrapper around a progress bar from the ``tqdm`` library."""

	def __init__(self, pbar):
		"""
		Parameters
		----------
		pbar
			``tqdm`` instance.
		"""
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
	           tqdm: t.Union[type, str] = 'tqdm.auto:tqdm',
	           **kw,
	           ):
		"""
		Parameters
		----------
		tqdm
			``tqdm`` class to use. Can be a string formatted like ``'tqdm.std:tqdm'``.
		\\**kw
			Passed to ``tqdm`` constructor.
		"""
		if isinstance(tqdm, str):
			modname, name = tqdm.split(':')
			module = import_module(modname)
			tqdm = getattr(module, name)

		return cls(tqdm(total=total, desc=desc, initial=initial, file=file, **kw))


register('tqdm-std', TqdmProgressMonitor.config(tqdm='tqdm.std:tqdm'))
register('tqdm-notebook', TqdmProgressMonitor.config(tqdm='tqdm.notebook:tqdm'))


@register('click')
class ClickProgressMonitor(AbstractProgressMonitor):
	"""Wrapper around a progress bar from the ``click`` library, using ``click.progressbar()``."""

	def __init__(self, pbar):
		"""
		Parameters
		----------
		pbar
			Progress bar object returned by ``click.progressbar``.
		"""
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
		"""
		Parameters
		----------
		\\**kw
			Passed to ``click.progressbar``.
		"""
		import click
		pbar = click.progressbar(length=total, label=desc, file=file, **kw)
		if initial != 0:
			pbar.update(initial)
		return cls(pbar)
