"""
The main module for :mod:`once`.

This defines the basics of memoizing code and saving each other.
"""
__version__ = "0.1.0"

import contextlib
import functools
import pickle
import typing


def unique_name(obj: typing.Any) -> str:
    """Come up with a unique string name for any Python object."""
    qualname = getattr(obj, "__qualname__", None) or ""
    name = getattr(obj, "__name__", None) or ""
    type_name = type(obj).__name__
    actual_obj_name = qualname or name or type_name
    module = getattr(obj, "__module__", None) or ""
    if not module:
        return actual_obj_name
    return ".".join((module, actual_obj_name))


class FunctionCall(typing.NamedTuple):
    """
    Immutable data structures that describes a function call.

    This data structure does not store return values of functions.
    It is approrpriate to be used as the key in a dictionary
    that stores the result of function calls as the value.
    """

    function_name: str
    args: typing.Tuple
    kwargs: typing.Tuple[typing.Tuple[str, typing.Any], ...]

    @classmethod
    def from_args(
        cls,
        function: typing.Callable,
        args: typing.Iterable,
        kwargs: typing.Dict[str, typing.Any],
    ):
        """
        Construct a FunctionCall object from a function and its arguments.

        This method handles the translation from a callable object to
        a unique(?) string that represents its value.
        """
        return cls(
            function_name=unique_name(function),
            args=tuple(args),
            kwargs=tuple(kwargs.items()),
        )


class FunctionReturn(typing.NamedTuple):
    """Contains the two outputs of a function--a return value or an exception."""

    retval: typing.Any
    exception: typing.Optional[BaseException]


_CACHE_TYPE = typing.Dict[FunctionCall, FunctionReturn]


_CENSOR_TYPE = typing.Callable[
    [typing.Callable, typing.Iterable, typing.Dict], FunctionCall
]


def _default_censor(function: typing.Callable, *args, **kwargs,) -> FunctionCall:
    """
    Does not censor anything. Returns a FunctionCall as given.
    """
    return FunctionCall.from_args(function=function, args=args, kwargs=kwargs,)


class Memoize:
    """
    Creates a common cache written to by any functions we wrap.
    """

    def __init__(self, cache: _CACHE_TYPE = None):
        """Initialize the memoize object."""
        self.cache: _CACHE_TYPE = cache or {}

    @classmethod
    def load_from_file(cls, filename: str, *, empty=False):
        """Unpickle a cache from a filename."""
        try:
            with open(filename) as handle:
                return cls.load(handle)
        except FileNotFoundError:
            if empty:
                return cls(cache=None)

    @classmethod
    def load(cls, handle):
        """Unpickle a cache object from a file handle. Returns a Memoize object."""
        cache = pickle.load(handle)
        return cls(cache=cache)

    @classmethod
    def loads(cls, serialized):
        """Unpickle a cache object from a string or a bytes-like object. Returns a Memoize object."""
        cache = pickle.loads(serialized)
        return cls(cache=cache)

    def dumps(self):
        """Dump the pickled cache to a string."""
        return pickle.dumps(self.cache)

    def dump(self, handle):
        """Dump a pickled cache to a file handle."""
        return pickle.dump(self.cache, handle)

    def wrap(  # pylint: disable=no-self-use
        self, function: typing.Callable, censor: _CENSOR_TYPE = _default_censor,
    ):
        """Wraps a function to cache results for subsequent calls."""

        class Wrapper:
            """
            Class that wraps a function, preserving its `__repr__()` method.

            This is similar to :func:`functools.wraps`, but
            :func:`functools.wraps` does not preserve `__repr__()`

            This is based on the following StackOverflow answer:
            https://stackoverflow.com/a/10875517/
            """

            def __init__(wrap_self):  # pylint: disable=no-self-argument
                functools.update_wrapper(wrap_self, function)

            def __repr__(wrap_self):  # pylint: disable=no-self-argument
                """Patch the wrapper function's repr() with the wrapped repr()."""
                return repr(function)

            def __call__(
                wrap_self, *args, **kwargs
            ):  # pylint: disable=no-self-argument
                """Call the wrapped function."""
                call = censor(function, *args, **kwargs)
                if call in self.cache:
                    if self.cache[call].exception:
                        raise self.cache[call].exception
                    return self.cache[call].retval

                try:
                    retval = function(*args, **kwargs)
                except BaseException as exc:
                    self.cache[call] = FunctionReturn(retval=None, exception=exc,)
                    raise
                else:
                    self.cache[call] = FunctionReturn(retval=retval, exception=None,)
                    return retval

        return Wrapper()


class MemoizeContext:
    """A context manager that manages the loading and saving of state to/from disk."""

    def __init__(self, filename: str):
        """Initialize the context manager."""
        self.filename = filename
        self.memoizer = None

    def __enter__(self):
        """Read the memoizer cache from a file, creating it if needed."""
        try:
            with open(self.filename, "rb") as handle:
                self.memoizer = Memoize.load(handle)
        except FileNotFoundError:
            self.memoizer = Memoize()
        return self.memoizer

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Save the memoizer cache back to the file we read the cache from."""
        with open(self.filename, "wb") as handle:
            self.memoizer.dump(handle)


class MemoizeClass:
    """Memoize a list of methods from a given class."""

    def __new__(cls, input_cls, method_list, memoizer):
        cls._memoizer = memoizer
        for method_name in method_list:
            setattr(
                cls, method_name, cls._memoizer.wrap(getattr(input_cls, method_name)),
            )
        return super().__new__(cls)
