from __future__ import unicode_literals
from concurrent.futures import Future
from functools import wraps
from types import MethodType
import inspect
import sys

from java.lang import Runnable, Thread
from java.util.concurrent import (
    ThreadPoolExecutor,
    LinkedBlockingQueue,
    Callable,
    TimeUnit,
)

__all__ = ("RunnableWrapper", "CallableWrapper", "setDefaultExceptionHandler")


class RunnableWrapper(Runnable):
    """
    Wraps a callable and its arguments for use in Java code that requires a
    :class:`~java.lang.Runnable`.

    """

    def __init__(self, func, args, kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        self._func(*self._args, **self._kwargs)


class CallableWrapper(Callable):
    """
    Wraps a callable and its arguments for use in Java code that requires a
    :class:`~java.util.concurrent.Callable`.

    """

    def __init__(self, func, args, kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def call(self):
        return self._func(*self._args, **self._kwargs)


class PythonUncaughtExceptionHandler(Thread.UncaughtExceptionHandler):
    def __init__(self, handler):
        self.handler = handler

    def uncaughtException(self, thread, exception):
        self.handler(thread, exception)


def setDefaultExceptionHandler(func):
    """
    Sets the default handler for uncaught exceptions for all threads.
    A value of ``None`` removes the default handler.

    The handler is called with two arguments: the java.lang.Thread object and
    the exception instance.

    """

    if func is None:
        handler = None
    else:
        argspec = inspect.getargspec(func)
        min_args = 3 if isinstance(func, MethodType) else 2
        if len(argspec.args) < min_args and not argspec.varargs:
            raise TypeError("The handler must accept at least two positional arguments")

        handler = PythonUncaughtExceptionHandler(func)

    Thread.setDefaultUncaughtExceptionHandler(handler)


class _AsyncRunnable(RunnableWrapper):
    def __init__(self, func, args, kwargs):
        RunnableWrapper.__init__(self, func, args, kwargs)
        self.future = Future()

    def run(self):
        if self.future.set_running_or_notify_cancel():
            try:
                result = self._func(*self._args, **self._kwargs)
                self.future.set_result(result)
            except BaseException as e:
                if hasattr(self.future, "set_exception_info"):
                    self.future.set_exception_info(*sys.exc_info()[1:])
                else:
                    self.future.set_exception(e)


class TaskExecutor(ThreadPoolExecutor):
    """
    This is a configurable thread pool for executing background tasks.

    :param coreThreads: Minimum number of threads
    :param maxThreads: Maximum number of threads
    :param keepalive: Time in seconds to keep idle non-core threads alive
    :param queue: The queue implementation, defaults to a
                  :class:`~java.util.concurrent.LinkedBlockingQueue`

    .. seealso:: :class:`java.util.concurrent.ThreadPoolExecutor`

    """

    def __init__(self, coreThreads=1, maxThreads=1, keepalive=5, queue=None):
        queue = queue or LinkedBlockingQueue()
        ThreadPoolExecutor.__init__(
            self, coreThreads, maxThreads, keepalive, TimeUnit.SECONDS, queue
        )

    def runBackground(self, func, *args, **kwargs):
        """
        Queues a (Python) callable for background execution in this thread
        pool. Any extra positional and keyword arguments will be passed to the
        target callable.

        """
        runnable = _AsyncRunnable(func, args, kwargs)
        self.execute(runnable)
        return runnable.future
