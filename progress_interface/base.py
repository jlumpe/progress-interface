"""Abstract interface for progress meters."""

from abc import ABC, abstractmethod
import typing as t
from warnings import warn


#: Registry of :class:`.ProgressConfig` instances to string keys
REGISTRY = dict()  # type Dict[str, ProgressConfig]


class AbstractProgressMeter(ABC):
	"""
	Abstract base class for an object which tracks the progress of a long-running task and possibly
	displays it to the user.

	Concrete subclasses must implement the :meth:`moveto` and :meth:`create` methods along with the
	:attr:`n`, :attr:`total`, and :attr:`closed` attributes. They may also optionally override
	:meth:`increment` and :meth:`close`.

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

	def increment(self, delta: int = 1):
		"""Increment the position of the meter by the given value."""
		self.moveto(self.n + delta)

	@abstractmethod
	def moveto(self, n: int):
		"""Set the meter's position to the given value."""
		pass

	def close(self):
		"""Stop tracking/displaying progress and perform whatever cleanup is necessary."""
		pass

	def __enter__(self) -> 'AbstractProgressMeter':
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
		"""Factory function with standardized signature to create instances of the class.

		Parameters
		----------
		total
			Total number of iterations to completion.
		initial
			Initial value of :attr:`n`.
		desc
			Description to display to the user, if applicable.
		file
			File-like object to write text output to, if applicable. Defaults to ``sys.stderr``.
		\\**kw
			Additional options depending on the subclass.
		"""
		pass

	@classmethod
	def config(cls, **kw) -> 'ProgressConfig':
		"""
		Get a ``ProgressConfig`` which creates instances of the class with the given default
		settings..

		Keyword arguments are passed on to :meth:`create`.
		"""
		return ProgressConfig(cls.create, kw)


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


#: Type alias for a factory function with signature ``(total: int, **kw) -> AbstractProgressMeter``.
ProgressFactoryFunc = t.Callable[[int], AbstractProgressMeter]


class ProgressConfig:
	"""Configuration settings used to create new progress meter instances.

	This allows callers to pass the desired progress meter type and other settings to a function
	without needing to know the total length and other details about the task, which can be
	determined within the function body.

	Attributes
	----------
	factory
		The :meth:`.AbstractProgressMeter.create` method of a concrete progress meter type, or
		another factory with the same signature which returns a progress meter instance.
	kw
		Keyword arguments to pass to ``factory``.
	"""
	factory: ProgressFactoryFunc
	kw: t.Dict[str, t.Any]

	def __init__(self, factory: ProgressFactoryFunc, kw: t.Dict[str, t.Any]):
		self.factory = factory
		self.kw = kw

	def create(self, total: int, **kw) -> AbstractProgressMeter:
		"""
		Create a progress meter instance by calling the factory function with the stored keyword
		arguments.

		The signature of this function is identical to :meth:`.AbstractProgressMeter.create`.
		"""
		final_kw = dict(self.kw)
		final_kw.update(kw)
		return self.factory(total, **final_kw)

	def update(self, *args: t.Mapping[str, t.Any], **kw) -> 'ProgressConfig':
		"""Update keyword arguments and return a new instance."""
		new_kw = dict(self.kw)
		new_kw.update(*args, **kw)
		return ProgressConfig(self.factory, new_kw)


def default_config() -> ProgressConfig:
	"""Get the default :class:`.ProgressConfig` instance to use.

	Currently attempts to use :class:`.TqdmProgressMeter`, if ``tqdm`` is not importable prints a
	warning and uses :class:`.NullProgressMeter`.
	"""
	try:
		from tqdm import tqdm
	except ImportError:
		warn('Could not import tqdm (not installed?), no default progress meter type available.')
		return NullProgressMeter.config()

	from .meters import TqdmProgressMeter
	return TqdmProgressMeter.config()


#: Type alias for argument to :func:`.get_config` and :func:`.get_progress`
ProgressArg = t.Union[ProgressConfig, str, bool, type, ProgressFactoryFunc, None]


def progress_config(arg: ProgressArg, **kw) -> ProgressConfig:
	"""Get a ``ProgressConfig`` instance from a variety argument types.

	Accepts the following types/values for the argument:

	- :class:`.ProgressConfig`
	- ``None`` - uses :class:`.NullProgressBar`.
	- ``True`` - uses value returned by :func:`.default_config`.
	- ``False`` - same as ``None``.
	- ``str`` key - Looks up progress bar class/factory function in :data:`.REGISTRY`.
	- :class:`.AbstractProgressMeter` subclass
	- ``Callable`` - factory function. Must have same signature as :meth:`.AbstractProgressMeter.create`.

	Parameters
	----------
	arg
		See above.
	\\**kw
		Additional keyword arguments to add to the returned config object.
	"""
	if arg is True:
		arg = default_config()
	if isinstance(arg, str):
		arg = REGISTRY[arg]
	if isinstance(arg, ProgressConfig):
		return arg.update(kw) if kw else arg
	if arg is None or arg is False:
		return NullProgressMeter.config()
	if isinstance(arg, type) and issubclass(arg, AbstractProgressMeter):
		return ProgressConfig(arg.create, kw)
	if callable(arg):
		return ProgressConfig(arg, kw)

	raise TypeError(arg)


def get_progress(arg: ProgressArg, total: int, initial: int = 0, **kw) -> AbstractProgressMeter:
	"""Create a progress meter instance.

	See :func:`.progress_config` for description of allowed types/values for the argument.

	Parameters
	----------
	arg
	total
		Number of expected iterations.
	initial
		Initial position of progress meter.
	\\**kw
		Additional keyword arguments to pass to progress meter class or factory function defined by
		``arg``..
	"""
	config = progress_config(arg)
	return config.create(total, initial=initial, **kw)


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


def register(key: str, arg: t.Optional[ProgressArg] = None, *, overwrite: bool=False):
	"""Register a progress meter class or factory function under the given key.

	If ``arg`` is not None, it is converted to a ``ProgressConfig`` instance and registered
	immediately. Otherwise a decorator function is returned which registers its argument under the
	given key.

	Parameters
	----------
	key
		Key to register under.
	arg
		None or any value that can be passed to :func:`.progress_config`.
	overwrite
		Whether to allow overwriting of existing keys.

	Returns
	-------
	Union[ProgressConfig, Callable]
		The ``ProgressConfig`` instance registered if ``arg`` is not None, otherwise a decorator
		function which registers its argument and returns it unchanged.
	"""
	def decorator(_arg: t.Union[type, t.Callable]):
		if not overwrite and key in REGISTRY:
			raise ValueError(f'Key {key!r} already exists in the registry')

		REGISTRY[key] = progress_config(_arg)
		return _arg

	if arg is None:
		return decorator
	else:
		return decorator(arg)
