# progress-interface

[![Build Status](https://github.com/jlumpe/progress-interface/actions/workflows/ci.yml/badge.svg)](https://github.com/jlumpe/progress-interface/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/progress-interface/badge/?version=latest)](https://progress-interface.readthedocs.io/en/latest/?badge=latest)


This package provides a generic interface for long-running tasks to report their progress without
being tied to a particular method or implementation. It is intended for use by library developers. 
Progress reporting can be added to a function so that the caller has full control over what is done
with the progress information, including:

* Displaying progress to the user using adapters for popular progress bar libraries such as
  [`tqdm`](https://github.com/tqdm/tqdm).
* Calling a callback function on each iteration.
* Just about anything else, by extending the `AbstractProgressMonitor` class.


## Example

The following example shows how to report progress within a function:

```python3
from progress_interface import get_progress

def do_work(items, progress=None):
    with get_progress(progress, len(items)) as monitor:
        for item in items:
            # Proces item...
            monitor.increment()
```

You can also use the convenience function `iter_progress`:

```python3
from progress_interface import iter_progress

def do_work(items, progress=None):
    with iter_progress(items, progress=None) as piter:
        for item in piter:
            # Process item...
```

Here the `progress` argument defines how to create a progress monitor object. It is ultimately
converted into a `ProgressConfig` object which serves this purpose, but accepts multiple alternate
types for user convenience:

* `None` or `False` - ignore progress information.
* `True` - use default settings to display a progress bar to the user. This attempts to import and
  use `tqdm` if it is installed. 
* A string, which uses a preset configuration registered under the given key. For example, `'tqdm'`
  displays a progress monitor using the `tqdm` library. Additional presets can be registered.
* A concrete subtype of `AbstractProgressMonitor`.
* A factory function which takes `total` and `initial` arguments and returns an
  `AbstractProgressMonitor` instance.
* An instance of `ProgressConfig` (see documentation for more details).

Note that for the most common use cases the caller does not even need to import `progress_interface`.


## Supported 3rd-party libraries

Support for the following libraries is included:

* `tqdm` - uses `tqdm.auto.tqdm`, registered under the `'tqdm'` key.
* `click` - uses `click.progressbar()`, registered under the `'click'` key.
