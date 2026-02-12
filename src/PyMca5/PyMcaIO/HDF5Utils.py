import os
import re
import sys
import h5py
import logging
import posixpath
from queue import Empty
from operator import itemgetter


_logger = logging.getLogger(__name__)


def get_hdf5_group_keys(file_path, data_path=None):
    """Note: segmentation faults seem to be caused only when iterating the HDF5 root.
    """
    os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
    with h5py.File(file_path, mode="r") as group:
        if data_path:
            group = group[data_path]
        else:
            group = group["/"]  # to preserve the order
        return list(group.keys())


def safe_hdf5_group_keys(file_path, data_path=None):
    return run_in_subprocess(
        get_hdf5_group_keys, file_path, data_path=data_path, default=list()
    )


def run_in_subprocess(target, *args, context=None, default=None, **kwargs):
    try: 
        import multiprocessing
        ctx = multiprocessing.get_context(context)
        queue = ctx.Queue(maxsize=1)
        p = ctx.Process(
            target=subprocess_main,
            args=(queue, target) + args,
            kwargs=kwargs,
        )
        p.start()
        try:
            p.join()
            try:
                return queue.get(block=False)
            except Empty:
                return default
        finally:
            try:
                p.kill()
            except AttributeError:
                p.terminate()
    except Exception:
        if getattr(sys, 'frozen', False):
            _logger.debug("Frozen executable. Using standard approach")
        else:
            _logger.warning("Multiprocessing is not available. Using standard approach")
        try:
            return target(*args, **kwargs)
        except Exception:
            return default


def subprocess_main(queue, method, *args, **kwargs):
    queue.put(method(*args, **kwargs))


def sort_h5items(h5_items, sorting_list=None):
    """
    :param h5_items: list of key and HDF5 item pairs
    :param sorting_list: list of HDF5 datasets names to sort on
    :returns: list of key and HDF5 item pairs
    """
    n = len(h5_items)
    if n < 2:
        return h5_items

    if sorting_list is None:
        sorting_list = ['start_time', 'end_time']

    # we have received items, not values
    # perform a first sort based on received names
    # this solves a problem with Eiger data where all the
    # external data have the same posixName. Without this sorting
    # they arrive "unsorted"
    h5_items.sort()
    try:
        posixNames = [h5_item.name for _, h5_item in h5_items]
    except AttributeError as ex:
        # Typical of broken external links
        _logger.debug(f"Cannot get posixNames: {ex}")
        return h5_items

    # This implementation only sorts entries
    if posixpath.dirname(posixNames[0]) != "/":
        return h5_items

    sorting_key = None
    first_h5_item = h5_items[0][1]
    if hasattr(first_h5_item, "items"):
        names = [k for k, _ in first_h5_item.items()]
        for name in sorting_list:
            if name in names:
                sorting_key = name
                break

    if sorting_key:
        try:
            if sorting_key == 'title':
                list_to_sort = [(_extract_h5title(item[1]), item) for item in h5_items]
            else:
                list_to_sort = [(item[1][sorting_key][()], item) for item in h5_items]
        except Exception as ex:
            list_to_sort = []
            _logger.warning("WARNING: Sorting by '%s' failed (%s)", sorting_key, ex)

        if _list_of_tuples_has_unique_first_item(list_to_sort):
            sorted_list = sorted(list_to_sort, key=itemgetter(0))
            return [item for _, item in sorted_list]

        sorting_list = [key for key in sorting_list if key != sorting_key]
        if sorting_list:
            return sort_h5items(h5_items, sorting_list=sorting_list)

    try:
        list_to_sort = [(_extract_sort_key_from_name(item[1].name), item) for item in h5_items]
    except Exception as ex:
        list_to_sort = []
        _logger.warning("WARNING: Sorting by name failed ('%s')", sorting_key, ex)

    if _list_of_tuples_has_unique_first_item(list_to_sort):
        sorted_list = sorted(list_to_sort, key=itemgetter(0))
        return [item for _, item in sorted_list]

    return h5_items


def _list_of_tuples_has_unique_first_item(list_of_tuples):
    if not list_of_tuples:
        return False
    first_items = [tpl[0] for tpl in list_of_tuples]
    return len(set(first_items)) == len(first_items)


def _extract_h5title(h5item):
    try:
        title = h5item["title"][()]
    except Exception:
        # allow the title to be missing
        title = ""
    if hasattr(title, "dtype"):
        if hasattr(title, "__len__"):
            if len(title) == 1:
                title = title[0]
    if hasattr(title, "decode"):
        title = title.decode("utf-8")
    return title


def _extract_sort_key_from_name(name):
    key = tuple(int(w) for w in _NON_NUMERIC_CHARS.split(name) if w)
    if key:
        return key
    return name

_NON_NUMERIC_CHARS = re.compile('[^0-9]')
