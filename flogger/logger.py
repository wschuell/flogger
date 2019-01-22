#!/usr/bin/env python
# coding: utf-8
"""
This module contains a data logging facility, to store various types of data under various forms, during an experiment.
As far as it can get with python, it provides an asynchronous handling of logging, which allows to avoid stopping the
experiment for logs.
"""
###########
# IMPORTS #
###########
import os.path
import os
import numpy as np
from multiprocessing import Manager
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
import datetime
import time
import logging
logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s [%(module)s:%(funcName)s:%(lineno)d] %(message)s")


#############
# SINGLETON #
#############
class Singleton(type):
    """
    Classic singleton metaclass.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


###############
# DATA LOGGER #
###############
class DataLogger(metaclass=Singleton):
    """Stores and save various type of data under various forms."""

    @staticmethod
    def _futures_callback(future: Future):
        """Called at future completion."""
        if future.exception():
            print(f"Future {future} raised the exception {repr(future.exception())}")

    @staticmethod
    def _push(managed, entry, value, time):
        """Push method called by the pool executors"""
        with managed.lockers[entry]:
            managed.data[entry][time] = value
            managed.counters[entry] += 1
            for f in managed.on_push_callables[entry]:
                try:
                    f(entry, managed.data[entry], path=managed.path)
                except Exception as e:
                    logging.getLogger("datalogger").warning(f"{managed.name} DataLogger: function {f} of {entry} failed: {e}")

    @staticmethod
    def _dump(managed, entry):
        """Dump method called by the pool executors"""
        with managed.lockers[entry]:
            for f in managed.on_dump_callables[entry]:
                try:
                    f(entry, managed.data[entry], path=managed.path)
                except Exception as e:
                    logging.getLogger("datalogger").warning(f"{managed.name} DataLogger: function {f} of {entry} failed: {e}")

    @staticmethod
    def _reset(managed, entry):
        """Inner reset method called by the pool executor"""
        with managed.lockers[entry]:
            for f in managed.on_reset_callables[entry]:
                try:
                    f(entry, managed.data[entry], path=managed.path)
                except Exception as e:
                    logging.getLogger("datalogger").warning(f"{managed.name} DataLogger: function {f} of {entry} failed: {e}")
            managed.data[entry].clear()
            managed.counters[entry] = 0

    def __init__(self):
        # Init and set attributes
        super(DataLogger, self).__init__()
        # Managed resources (accessible by remote threads or remote processes)
        self._manager = Manager()
        self._managed = self._manager.Namespace()
        self._managed.name = "data-logger"
        self._managed.path = "."
        self._managed.entries = self._manager.list()
        self._managed.data = self._manager.dict()
        self._managed.lockers = self._manager.dict()
        self._managed.counters = self._manager.dict()
        self._managed.on_push_callables = self._manager.dict()
        self._managed.on_reset_callables = self._manager.dict()
        self._managed.on_dump_callables = self._manager.dict()

        self.tick = datetime.datetime.now()
        self.futures = list()
        self.pool = ThreadPoolExecutor(max_workers=1)
        # Log
        logging.getLogger("datalogger").info("{} DataLogger initialized!".format(self._managed.name))

    def set_path(self, path):
        """Sets the root path of the logger. Used by all the handlers that write on disk.

        :param string path: A valid path to write the data in.
        """
        if len(self._managed.lockers) != 0:
            raise Exception("You tried to change logger path after having registered some entries.")
        os.makedirs(path, exist_ok=True)
        self._managed.path = path

    def set_pool(self, pool, n_par=5):
        """Sets the executor to be used to call handlers.

        :param string pool: The type of executor to use to call handlers. Either "thread" or "process".
        :param int n_par: The number of executor to use.
        """
        if len(self._managed.lockers) != 0:
            raise Exception("You tried to pool after having registered some entries.")
        if pool == "thread":
            self.pool = ThreadPoolExecutor(max_workers=n_par)
        elif pool == "process":
            self.pool = ProcessPoolExecutor(max_workers=n_par)
        else:
            raise Exception(f"Unknown pool type `{pool}`")

    def set_name(self, name):
        """Sets the name of the logger.

        :param string name: Name of the logger
        """
        self._managed.name = name

    def declare(self, entry, on_push_callables, on_dump_callables, on_reset_callables):
        """Register a recurring log entry.

        Registering an entry gives access to the `push`, `reset` and `dump` methods. Note that all the handlers must be
        able to handle the data that will be pushed.

        :param string entry: Name of the log entry.
        :param List[handlers] on_push_callables: Handlers called on data when `push` is called.
        :param List[handlers] on_reset_callables: Handlers called on data when `reset` is called.
        :param List[handlers] on_dump_callables: Handlers called on the data when `dump` is called.
        """
        if entry in self._managed.entries:
            raise Exception("You tried to declare an existing log entry")
        self._managed.entries.append(entry)
        self._managed.lockers[entry] = self._manager.RLock()
        self._managed.data[entry] = self._manager.dict()
        self._managed.counters[entry] = 0
        self._managed.on_push_callables[entry] = self._manager.list(on_push_callables)
        self._managed.on_reset_callables[entry] = self._manager.list(on_reset_callables)
        self._managed.on_dump_callables[entry] = self._manager.list(on_dump_callables)
        if os.path.dirname(entry) != "":
            os.makedirs(os.path.join(self._managed.path, os.path.dirname(entry)), exist_ok=True)

    def push(self, entry, value, time=None):
        """Append data to a recurring log.

        All handlers registered for the `on_push` event will be called.

        :param string entry: Name of the log entry
        :param Any value: Object containing the data to log. Should be of same type from call to call...
        :param int or None time: Date of the logging (epoch, iteration, tic ...). Will be used as key in the data
        dictionary. If `None`, the last data key plus one will be used.
        """
        future = self.pool.submit(DataLogger._push,
                                  self._managed,
                                  entry,
                                  value,
                                  time if time is not None else self._managed.counters[entry])
        future.add_done_callback(DataLogger._futures_callback)
        self.futures.append(future)

    def dump(self):
        """Calls handlers declared for `on_dump` event, for all registered log entries.
        """
        for entry in self._managed.entries:
            future = self.pool.submit(DataLogger._dump,
                                      self._managed,
                                      entry)
            future.add_done_callback(DataLogger._futures_callback)
            self.futures.append(future)

    def reset(self, entry):
        """Resets the data of a recurring log entry.

        All handlers registered for the `on_reset` event will be called before the storage is emptied.

        :param string entry: name of the log entry.
        """

        future = self.pool.submit(DataLogger._reset,
                                  self._managed,
                                  entry)
        future.add_done_callback(DataLogger._futures_callback)
        self.futures.append(future)

    def get_entry_length(self, entry):
        """Retrieves the number of data saved for a log entry.

        :param string entry: Name of the log entry
        :return: Number of data pieces in the entry storage
        :rtype: int
        """
        return self._managed.counters[entry]

    def get_serie(self, entry):
        """Returns the data in a list ordered by keys.

        :param string entry: Name of the log entry
        :return: Serie of data ordered by key
        :rtype: List[any]
        """
        return [i[1] for i in sorted(self._managed.data[entry].items())]

    def wait(self, log_durations=True):
        """Wait for the handling queue to be emptied.

        :param bool log_durations: Whether to log the wait duration.
        """
        b = datetime.datetime.now()
        while True:
            self.futures = list(filter(lambda x: not x.done(), self.futures))
            if self.futures:
                time.sleep(.1)
            else:
                break
        if log_durations:
            logging.getLogger("datalogger").info(f"{self._managed.name} DataLogger: Last wait occured {self.tick - b} ago.")
            logging.getLogger("datalogger").info(f"{self._managed.name} DataLogger: Waited {datetime.datetime.now() - b} for completion.")
        self.tick = datetime.datetime.now()
