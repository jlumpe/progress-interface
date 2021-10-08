"""Abstract interface for progress meters."""

from abc import ABC, abstractmethod
import typing as t
from warnings import warn


#: Registry of :class:`.ProgressConfig` instances to string keys
REGISTRY = dict()


class AbstractProgressMeter(ABC):
	"""Abstract base class for an object which displays progress to the user.

	Instances can be used as context managers, on exit the :meth:`close` method is called.

	Attributes
	----------
	n
		Number of completed iterations. Do not modify directly, use the :meth:`increment` and
		:meth:`moveto` methods instead.
	total
		Expected total number of iterations.
	closed
		Whether the meter has been closed/completed.
	"""
	n: int
	total: int
	closed: int

	@abstractmethod
	def increment(self, delta: int = 1):
		"""Increment the position of the meter by the given value."""
		pass

	@abstractmethod
	def moveto(self, n: int):
		"""Set the meter's position to the given value."""
		pass

	def close(self):
		"""Stop displaying progress and perform whatever cleanup is necessary."""
		pass

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.close()

	@classmethod
	@abstractmethod
	def create(cls,
	           total: int,
	           *,
	           initial: int = 0,
	           desc: t.Optional[str] = None,
	           file: t.Optional[t.TextIO] = None,
	           **kw,
	           ) -> 'AbstractProgressMeter':
		"""Factory function with standardized signature to create instances.

		Parameters
		----------
		total
			Total number of iterations to completion.
		initial
			Initial value of :attr:`n`.
		desc
			Description to display to the user.
		file
			File-like object to write to. Defaults to ``sys.stderr``.
		\\**kw
			Additional options depending on the subclass.
		"""
		pass

	@classmethod
	def config(cls, **kw) -> 'ProgressConfig':
		"""Create a factory function which creates instances with the given default settings.

		Keyword arguments are passed on to :meth:`create`.
		"""
		return ProgressConfig(cls.create, kw)


#: Type alias for a callable which takes ``total`` and keyword arguments and returns a progress meter instance.
ProgressFactoryFunc = t.Callable[[int], AbstractProgressMeter]


class ProgressConfig:
	"""Configuration settings used to create new progress meter instances.

	This allows callers to pass the desired progress meter type and other settings to API functions
	which can then create the instance themselves within the function body by specifying the total
	length and other final options.

	Attributes
	----------
	callable
		The :meth:`.AbstractProgressMeter.create` method of a concrete progress meter type, or
		another callable with the same signature which returns a progress meter instance.
	kw
		Keyword arguments to pass to callable.
	"""
	callable: ProgressFactoryFunc
	kw: t.Dict[str, t.Any]

	def __init__(self, callable: ProgressFactoryFunc, kw: t.Dict[str, t.Any]):
		self.callable = callable
		self.kw = kw

	def create(self, total: int, **kw) -> AbstractProgressMeter:
		"""Call the factory function with the stored keyword arguments to create a progress meter instance.

		The signature of this function is identical to :meth:`.AbstractProgressMeter.create`.
		"""
		final_kw = dict(self.kw)
		final_kw.update(kw)
		return self.callable(total, **final_kw)

	def update(self, *args: t.Mapping[str, t.Any], **kw) -> 'ProgressConfig':
		"""Update keyword arguments and return a new instance."""
		new_kw = dict(self.kw)
		new_kw.update(*args, **kw)
		return ProgressConfig(self.callable, new_kw)


def default_config() -> ProgressConfig:
	"""Get the default :class:`.ProgressConfig` instance to use.

	Currently attempts to use :class:`.TqdmProgressMeter`, if ``tqdm`` is not importable prints a
	warning and uses :class:`.NullProgressMeter`.
	"""
	try:
		from tqdm import tqdm
		from .lib import TqdmProgressMeter
		return TqdmProgressMeter.config()
	except ImportError:
		warn('Could not import tqdm (not installed?), no default progress meter type available.')
		return NullProgressMeter.config()


#: Type alias for argument to :func:`.get_config` and :func:`.get_progress`
ProgressArg = t.Union[ProgressConfig, str, bool, type, ProgressFactoryFunc, None]


def progress_config(arg: ProgressArg, **kw) -> ProgressConfig:
	"""Get a ``ProgressConfig`` instance from flexible argument types.

	See :func:`.get_progress` for description of allowed argument types/values.
	"""
	if isinstance(arg, ProgressConfig):
		return arg.update(kw) if kw else arg
	if arg is None or arg is False:
		return NullProgressMeter.config(**kw)
	if arg is True:
		return default_config()
	if isinstance(arg, type) and issubclass(arg, AbstractProgressMeter):
		return ProgressConfig(arg.create, kw)
	if isinstance(arg, str):
		return ProgressConfig(REGISTRY[arg], kw)
	if callable(arg):
		return ProgressConfig(arg, kw)

	raise TypeError(arg)


def get_progress(arg: ProgressArg, total: int, initial: int = 0, **kw) -> AbstractProgressMeter:
	"""Get a progress meter instance.

	Meant to be used within API funcs in which the caller wants to specify the type and
	parameters of the progress meter but cannot pass an actual instance because the total number of
	iterations is determined within the body of the function. Instead the API function can take
	a single ``progress`` argument which specifies this information, then create the instance by
	by calling this function with than information along with the total length.

	Accepts the following types/values for the argument:

	- :class:`.ProgressConfig`
	- ``None`` - uses :class:`.NullProgressBar`.
	- ``True`` - uses class returned by :func:`.default_progress_cls`.
	- ``False`` - same as ``None``.
	- ``str`` key - Looks up progress bar class/factory function in :data:`.REGISTRY`.
	- :class:`.AbstractProgressMeter` subclass
	- ``callable`` - factory function. Must have same signature as :meth:`.AbstractProgressMeter.create`.

	Parameters
	----------
	arg
		See above.
	total
		Length of progress meter to create.
	initial
		Initial position of progress meter.
	\\**kw
		Additional keyword arguments to pass to progress meter class or factory function defined by
		``arg``..
	"""
	config = progress_config(arg)
	return config.create(total, initial=initial, **kw)


def register(key: str, arg: t.Union[type, ProgressConfig, t.Callable] = None, *, overwrite: bool=False):
	"""Register a progress meter class or factory function under the given key.

	Parameters
	----------
	key
		Key to register under.
	arg
		:class:`ProgressConfig` instance, :class:`AbstractProgressMeter` subclass, or factory
		function. If None will return a decorator that performs the registration.
	overwrite
		Whether to allow overwriting of existing keys.

	Returns
	-------
	Union[None, Callable]
		None if ``cls_or_func`` has a value, otherwise a decorator function which registers its
		argument under the given key and returns it unchanged.
	"""
	def decorator(_arg: t.Union[type, t.Callable]):
		if not overwrite and key in REGISTRY:
			raise ValueError(f'Key {key!r} already exists in the registry')

		REGISTRY[key] = progress_config(_arg)
		return _arg

	if arg is None:
		return decorator
	else:
		decorator(arg)
		return None


class ProgressIterator(t.Iterator):
	itr: t.Iterator
	meter: AbstractProgressMeter

	def __init__(self, iterable: t.Iterable, meter: AbstractProgressMeter):
		self.itr = iter(iterable)
		self.meter = meter
		self._first = True

	def __next__(self):
		if not self._first:
			self.meter.increment()
		self._first = False

		try:
			value = next(self.itr)
		except StopIteration:
			self.meter.close()  # Close on reaching end
			raise

		return value

	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.meter.close()


def iter_progress(iterable: t.Iterable,
                  progress: ProgressArg = True,
                  total: t.Optional[int] = None,
                  **kw,
                  ) -> ProgressIterator:
	"""Display a progress meter while iterating over an object.

	The returned iterator object can also be used as a context manager to ensure that the progress
	meter is closed properly even if iteration does not finish.

	Parameters
	----------
	itarable
		Iterable object.
	progress
		Passed to :func:`get_progress`.
	total
		Total number of expected iterations. Defaults to ``len(iterable)``.
	\\**kw
		Additional keyword arguments to pass to progress meter factory.

	Returns
	-------
	.ProgressIterator
		Iterator over values in ``iterable`` which advances a progress meter.
	"""
	if total is None:
		total = len(iterable)

	meter = get_progress(progress, total, **kw)
	return ProgressIterator(iterable, meter)


def capture_progress(config: ProgressConfig) -> t.Tuple[ProgressConfig, t.List[AbstractProgressMeter]]:
	"""
	Creates a ``ProgressConfig`` which captures references to the progress meter instances created
	with it.

	This is intended to be used for testing other API functions which create progress meter instances
	internally that normally would not be accessible by the caller. The captured instance can be
	checked to ensure it has the correct attributes and went through the full range of iterations,
	for example.

	Returns
	-------
	Tuple[ProgressConfig, List[AbstractProgressMeter]]
		The first item is a modified ``ProgessConfig`` instance which can be passed to the function
		to be tested. The second is a list which is initially empty, and is populated with progress
		meter instances as they are created by it.
	"""
	instances = []

	def factory(total, **kw):
		meter = config.create(total, **kw)
		instances.append(meter)
		return meter

	return progress_config(factory), instances


class NullProgressMeter(AbstractProgressMeter):
	"""Progress meter which does nothing."""

	def increment(self, delta: int = 1):
		pass

	def moveto(self, n: int):
		pass

	def close(self):
		pass

	@classmethod
	def create(cls, total: int, initial: int = 0, **kw):
		return cls()


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
