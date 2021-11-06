from contextlib import contextmanager
from unittest.mock import patch

import pytest

from progress_interface.base import default_config, progress_config, get_progress, iter_progress, \
	NullProgressMonitor, REGISTRY
from progress_interface.test import TestProgressMonitor
from progress_interface.monitors import TqdmProgressMonitor, ClickProgressMonitor


@contextmanager
def no_import(name: str):
	"""Context manager which makes a module not importable even if installed."""

	# Setting value of a key to None in sys.modules will raise a ModuleNotFound error  on import,
	# even if the package is installed.
	with patch.dict('sys.modules', {name: None}):
		yield


@pytest.mark.parametrize('with_tqdm', [False, True])
class TestDefaultConfig:
	"""Test the default_config() function and get_progress(True)."""

	def test_default_config(self, with_tqdm):
		"""Test default_config() function."""

		if with_tqdm:
			pytest.importorskip('tqdm')
			conf = default_config()
			assert conf.factory == TqdmProgressMonitor.create

		else:
			with no_import('tqdm'):
				with pytest.warns(UserWarning):
					conf = default_config()
				assert conf.factory == NullProgressMonitor.create

	def test_progress_config_true(self, with_tqdm):
		"""Test passing True as argument to progress_config()."""
		if with_tqdm:
			pytest.importorskip('tqdm')  # Skip if tqdm not available.
			config = progress_config(True, foo=1)
			assert config.factory == TqdmProgressMonitor.create
			assert config.kw == dict(foo=1)

		else:
			with no_import('tqdm'):
				with pytest.warns(UserWarning):
					config = progress_config(True, foo=1)
				assert config.factory == NullProgressMonitor.create
				assert config.kw == dict(foo=1)


class TestProgressConfigFunc:
	"""Test the progress_config() function.

	The case where arg=True is tested in TestDefaultConfig.
	"""

	def test_null(self):
		"""Test passing None and False as argument."""
		for arg in [None, False]:
			config = progress_config(arg)
			assert config.factory == NullProgressMonitor.create

	def test_cls(self):
		"""Test passing AbstractProgressMonitor subclass as argument."""
		for cls in [NullProgressMonitor, TestProgressMonitor]:
			config = progress_config(cls, foo=1)
			assert config.factory == cls.create
			assert config.kw == dict(foo=1)

	def test_str(self):
		for key, config in REGISTRY.items():
			config2 = progress_config(key, foo=1)
			assert config2.factory == config.factory
			assert config2.kw == {**config.kw, 'foo': 1}

	def test_factory(self):
		"""Test passing a factory function as argument."""

		def factory(total, *, initial=None, **kw):
			return TestProgressMonitor.create(total, initial=initial, foo=1, **kw)

		config = progress_config(factory, foo=1)
		assert config.factory == factory
		assert config.kw == dict(foo=1)

	def test_progressconfig(self):
		"""Test passing a factory function as argument."""

		config = TestProgressMonitor.config(foo=1, bar=2)
		config2 = progress_config(config, bar=20, baz=3)

		assert config2.factory == TestProgressMonitor.create
		assert config2.kw == dict(foo=1, bar=20, baz=3)

	def test_invalid(selfj):
		with pytest.raises(TypeError):
			get_progress(0, 100)


class TestGetProgress:
	"""Test the get_progress() function.

	The case where arg=True is tested in TestDefaultConfig.
	"""

	@pytest.fixture()
	def total(self):
		return 100

	@pytest.fixture(params=[0, 10])
	def initial(self, request):
		return request.param

	def test_null(self, total, initial):
		"""Test passing None and False as argument."""
		for arg in [None, False]:
			assert isinstance(get_progress(arg, total, initial=initial), NullProgressMonitor)

	def test_cls(self, total, initial):
		"""Test passing AbstractProgressMonitor subclass as argument."""
		for cls in [NullProgressMonitor, TestProgressMonitor]:
			monitor = get_progress(cls, total, initial=initial)
			assert isinstance(monitor, cls)

			if cls is not NullProgressMonitor:
				assert monitor.total == total
				assert monitor.n == initial

	def test_str(self, total, initial):
		# TODO - use a type that doesn't require 3rd-party library
		monitor = get_progress('click', total, initial=initial)
		assert isinstance(monitor, ClickProgressMonitor)
		assert monitor.total == total
		assert monitor.n == initial

	def test_factory(self, total, initial):
		"""Test passing a factory function as argument."""

		def factory(total, *, initial=None, **kw):
			return TestProgressMonitor.create(total, initial=initial, foo=1, **kw)

		monitor = get_progress(factory, total, initial=initial, bar=2)

		assert isinstance(monitor, TestProgressMonitor)
		assert monitor.total == total
		assert monitor.n == initial
		assert monitor.kw == dict(foo=1, bar=2)

	def test_progressconfig(self, total, initial):
		"""Test passing a factory function as argument."""

		config = TestProgressMonitor.config(foo=1)
		monitor = get_progress(config, total, initial=initial, bar=2)

		assert isinstance(monitor, TestProgressMonitor)
		assert monitor.total == total
		assert monitor.n == initial
		assert monitor.kw == dict(foo=1, bar=2)

	def test_invalid(selfj):
		with pytest.raises(TypeError):
			get_progress(0, 100)


@pytest.mark.parametrize('pass_total', [False, True])
@pytest.mark.parametrize('abort_early', [False, True])
def test_iter_progress(pass_total, abort_early):
	"""Test the iter_progress() function."""
	import string
	items = string.ascii_letters
	abort_at = 10

	if pass_total:
		iterable = iter(items)
		total = len(items)
	else:
		iterable = items
		total = None

	with iter_progress(iterable, TestProgressMonitor, total=total, foo=1) as itr:
		assert isinstance(itr.monitor, TestProgressMonitor)
		assert itr.monitor.total == len(items)
		assert itr.monitor.kw == dict(foo=1)
		assert itr.monitor.n == 0
		assert not itr.monitor.closed

		for i, val in enumerate(itr):
			assert val == items[i]
			assert itr.monitor.n == i
			assert not itr.monitor.closed

			if abort_early and i == abort_at:
				break

		if abort_early:
			assert i == abort_at
			assert itr.monitor.n == abort_at
			assert not itr.monitor.closed
		else:
			assert i == len(items) - 1
			assert itr.monitor.n == len(items)
			assert itr.monitor.closed

	assert itr.monitor.closed  # Always closed after exiting context


class TestRegister:
	"""Test the register() function."""

	# TODO
