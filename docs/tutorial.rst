Tutorial
========

Let's see how to use *flogger* from scratch.


Direct call to handler functions
********************************

In its simplest use, flogger provides *handlers* function that can be used to store different types of data. *Handlers*
are helper methods which follows the signature ``(entry: string, data: dict, ...)`` where:

   + ``entry`` represents the log entry
   + ``data`` contains ordered data; keys are integer increments and items are of various types depending on the handler.

*Handlers* can roughly be separated in two categories:

   + The ones that act on the whole ``data``
   + The ones that only act on the last ``data`` item, which by convention, end with ``_last``

Example of direct use of handlers::

    import flogger as fl
    fl.echo_last("main_function", {0: "Hey You"})
    fl.echo_last("main_function", {0: "Hey Again"})
    fl.save_to_mpl_lines("main_function", {0: 1, 1:5, 2: 3}, path="/home/user/logs")

Automating with recurring lof entries
*************************************

If you want to log a lot of different pieces of data into a lot of different forms, it can rapidly becomes bothering
to handle the storage of data and the calling to every handlers here and there in your code. *Flogger* allows you to
lighten your logging by declaring recurring log entries whose storage and handlers calling are automated. Example of use
of recurring log entries::
    import flogger as fl

    # We initialize the logger
    dl = fl.DataLogger()

    # We declare a recurring entries
    dl.declare("Loss", [fl.echo_last, fl.add_tsb_scalar_last],
                       [],
                       [fl.save_to_json, fl.save_to_mpl_lines])
    dl.declare("Performance", [],
                              [],
                              [fl.save_to_json])

    # We push some data into recurring entries
    dl.push("Loss", 0, 0.5)
    # Calls `fl.echo_last` and `fl.add_tsb_scalar_last` on `{0:0.5}`
    dl.push("Performance", 0, 0.7)
    # Calls nothing
    dl.push("Loss", 1, 0.6)
    # Calls `fl.echo_last` and `fl.add_tsb_scalar_last` on `{0:0.5, 1:0.6}`
    dl.push("Performance", 1, 0.8)
    # Calls nothing
    dl.dump()
    # Calls `fl.save_to_json` and `fl.save_to_mpl_lines` on `{0:0.5, 1:0.6}`
    # and `fl.save_to_json` on  `{0:0.7, 1:0.8}`


As shown in the example, you have to declare a log entry by using the ``declare(entry, ...)`` method. Doing so allows you
to use three methods to act on your data:
   + ``push(entry, time, data)`` to add new pieces of data under the entry
   + ``dump()`` to dump the data (along with all other managed by the logger)
   + ``reset(entry)`` to empty the storage related to the entry

Each time one of those methods is called, associated handlers will be called on the whole entry storage. Those handlers
are provided to the logger when the entry is declared. Indeed, three lists of handlers must be provided as extra
arguments to the ``declare`` method:
   + ``on_push_callables`` a list of handlers that will be called on the data at every call to the ``push`` method
   + ``on_dump_callables`` a list of handlers called when ``dump`` is called
   + ``on_reset_callables`` a list of handlers called when ``reset`` is called

.. Note::
   While ``push`` and ``reset`` are specific to an entry, the ``dump`` method act on every entries.

.. seealso::
    There is no much more to tell about! You can check the available handlers in the **API** section, but please be sure
    to check the **Remarks** section before using flogger.