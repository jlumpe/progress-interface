from contextlib import contextmanager
from unittest.mock import patch

import pytest

from progress_interface.base import default_config, progress_config, get_progress, iter_progress, \
	capture_progress, NullProgressMeter, REGISTRY
from progress_interface.meters import TestProgressMeter, TqdmProgressMeter, ClickProgressMeter


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
			assert conf.factory == TqdmProgressMeter.create

		else:
			with no_import('tqdm'):
				with pytest.warns(UserWarning):
					conf = default_config()
				assert conf.factory == NullProgressMeter.create

	def test_progress_config_true(self, with_tqdm):
		"""Test passing True as argument to progress_config()."""
		if with_tqdm:
			pytest.importorskip('tqdm')  # Skip if tqdm not available.
			config = progress_config(True, foo=1)
			assert config.factory == TqdmProgressMeter.create
			assert config.kw == dict(foo=1)

		else:
			with no_import('tqdm'):
				with pytest.warns(UserWarning):
					config = progress_config(True, foo=1)
				assert config.factory == NullProgressMeter.create
				assert config.kw == dict(foo=1)


class TestProgressConfigFunc:
	"""Test the progress_config() function.

	The case where arg=True is tested in TestDefaultConfig.
	"""

	def test_null(self):
		"""Test passing None and False as argument."""
		for arg in [None, False]:
			config = progress_config(arg)
			assert config.factory == NullProgressMeter.create

	def test_cls(self):
		"""Test passing AbstractProgressMeter subclass as argument."""
		for cls in [NullProgressMeter, TestProgressMeter]:
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
			return TestProgressMeter.create(total, initial=initial, foo=1, **kw)

		config = progress_config(factory, foo=1)
		assert config.factory == factory
		assert config.kw == dict(foo=1)

	def test_progressconfig(self):
		"""Test passing a factory function as argument."""

		config = TestProgressMeter.config(foo=1, bar=2)
		config2 = progress_config(config, bar=20, baz=3)

		assert config2.factory == TestProgressMeter.create
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
			assert isinstance(get_progress(arg, total, initial=initial), NullProgressMeter)

	def test_cls(self, total, initial):
		"""Test passing AbstractProgressMeter subclass as argument."""
		for cls in [NullProgressMeter, TestProgressMeter]:
			meter = get_progress(cls, total, initial=initial)
			assert isinstance(meter, cls)

			if cls is not NullProgressMeter:
				assert meter.total == total
				assert meter.n == initial

	def test_str(self, total, initial):
		meter = get_progress('click', total, initial=initial)
		assert isinstance(meter, ClickProgressMeter)
		assert meter.total == total
		assert meter.n == initial

	def test_factory(self, total, initial):
		"""Test passing a factory function as argument."""

		def factory(total, *, initial=None, **kw):
			return TestProgressMeter.create(total, initial=initial, foo=1, **kw)

		meter = get_progress(factory, total, initial=initial, bar=2)

		assert isinstance(meter, TestProgressMeter)
		assert meter.total == total
		assert meter.n == initial
		assert meter.kw == dict(foo=1, bar=2)

	def test_progressconfig(self, total, initial):
		"""Test passing a factory function as argument."""

		config = TestProgressMeter.config(foo=1)
		meter = get_progress(config, total, initial=initial, bar=2)

		assert isinstance(meter, TestProgressMeter)
		assert meter.total == total
		assert meter.n == initial
		assert meter.kw == dict(foo=1, bar=2)

	def test_invalid(selfj):
		with pytest.raises(TypeError):
			get_progress(0, 100)


def test_capture_progress():
	"""Test the capture_progress() function."""
	config, instances = capture_progress(TestProgressMeter.config())
	assert instances == []

	instance1 = config.create(10)
	assert instances == [instance1]

	instance2 = config.create(20)
	assert instances == [instance1, instance2]

	instance3 = config.create(30)
	assert instances == [instance1, instance2, instance3]


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

	with iter_progress(iterable, TestProgressMeter, total=total, foo=1) as itr:
		assert isinstance(itr.meter, TestProgressMeter)
		assert itr.meter.total == len(items)
		assert itr.meter.kw == dict(foo=1)
		assert itr.meter.n == 0
		assert not itr.meter.closed

		for i, val in enumerate(itr):
			assert val == items[i]
			assert itr.meter.n == i
			assert not itr.meter.closed

			if abort_early and i == abort_at:
				break

		if abort_early:
			assert i == abort_at
			assert itr.meter.n == abort_at
			assert not itr.meter.closed
		else:
			assert i == len(items) - 1
			assert itr.meter.n == len(items)
			assert itr.meter.closed

	assert itr.meter.closed  # Always closed after exiting context


class TestRegister:
	"""Test the register() function."""

	# TODO
