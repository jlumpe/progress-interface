"""Test AbstractProgressMonitor implementations."""

import pytest

from progress_interface.base import NullProgressMonitor
from progress_interface.monitors import TqdmProgressMonitor, ClickProgressMonitor
from progress_interface.test import TestProgressMonitor


class TestNullProgressMonitor():
	"""Test the NullProgressMonitor class."""

	def test_methods(self):
		# All methods are no-ops so just test we can call interface funcs with no errors.
		monitor = NullProgressMonitor()
		monitor.increment()
		monitor.increment(10)
		monitor.moveto(100)
		monitor.close()

	def test_create(self):
		# Accepts standard arguments but ignores them
		assert isinstance(NullProgressMonitor.create(100), NullProgressMonitor)
		assert isinstance(NullProgressMonitor.create(100, initial=10), NullProgressMonitor)
		assert isinstance(NullProgressMonitor.create(100, foo=10), NullProgressMonitor)


class TestTestProgressMonitor:
	"""Test the TestProgressMonitor class."""

	def test_basic(self):
		kw = dict(foo=1, bar=True)
		pbar = TestProgressMonitor(100, **kw)

		assert pbar.total == 100
		assert pbar.n == 0
		assert not pbar.closed
		assert pbar.kw == kw

		pbar.increment()
		assert pbar.n == 1

		pbar.increment(10)
		assert pbar.n == 11

		pbar.increment(-1)
		assert pbar.n == 10

		pbar.moveto(50)
		assert pbar.n == 50

		pbar.moveto(40)
		assert pbar.n == 40

		with pytest.raises(ValueError):
			pbar.increment(100)

		with pytest.raises(ValueError):
			pbar.increment(-100)

		with pytest.raises(ValueError):
			pbar.moveto(101)

		with pytest.raises(ValueError):
			pbar.moveto(-1)

		pbar.close()
		assert pbar.closed

		with pytest.raises(RuntimeError):
			pbar.increment()

		with pytest.raises(RuntimeError):
			pbar.moveto(100)

	def test_no_allow_decrement(self):
		pbar = TestProgressMonitor(100, allow_decrement=False)

		# Moving forward
		pbar.increment()
		pbar.increment(0)
		pbar.increment(10)
		pbar.moveto(50)

		# Moving backward
		with pytest.raises(ValueError):
			pbar.increment(-1)

		with pytest.raises(ValueError):
			pbar.moveto(40)


class TestClickProgressMeter:
	"""Test the ClickProgressMonitor class."""
	# TODO


class TestTqdmProgressMeter:
	"""Test the TqdmProgressMonitor class."""
	# TODO
