import os
import re
import h5py
import logging
import posixpath
from queue import Empty
_logger = logging.getLogger(__name__)
from operator import itemgetter


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
    try:
        return run_in_subprocess(
            get_hdf5_group_keys, file_path, data_path=data_path, default=list()
        )
    except Exception:
        _logger.warning("run_in_subprocess not available")
        return get_hdf5_group_keys(file_path, data_path)


def run_in_subprocess(target, *args, context=None, default=None, **kwargs):
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


def subprocess_main(queue, method, *args, **kwargs):
    queue.put(method(*args, **kwargs))


def sort_h5items(h5_items, sorting_list=None):
    """
    :param h5_items: list of name and HDF5 item pairs
    :param sorting_list: list of HDF5 datasets names to sort on
    :returns: list of name and HDF5 item pairs
    """
    n = len(h5_items)
    if n < 2:
        return h5_items

    # Alphabetic sorting on names
    h5_items.sort()

    # Get full HDF5 item names
    try:
        posixNames = [h5_item.name for _, h5_item in h5_items]
    except AttributeError as ex:
        # Typical of broken external links
        _logger.debug(f"Cannot get posixNames: {ex}")
        return h5_items

    if posixpath.dirname(posixNames[0]) != "/":
        # First posix name is not a top-level name
        return h5_items

    # Names of the children whose values is used for sorting
    if sorting_list is None:
        child_names = ["start_time", "end_time"]
    elif set(sorting_list) == {"title"}:
        child_names = ["title", "start_time", "end_time"]
    elif "title" in sorting_list:
        child_names = list(sorting_list)
        child_names.remove("title")
        child_names.insert(0, "title")
    else:
        child_names = list(sorting_list)

    # Sort on HDF5 item names
    ordered = sorted(h5_items, key=_h5item_natural_sort_key)

    # Sort by all child values from lowest priority (last) to highest priority (first)
    for child_name in reversed(child_names):
        ordered = _sort_by_child_value(ordered, child_name)
    return ordered


def _sort_by_child_value(h5_items, child_name):
    """
    Sorts items by a given HDF5 child value, missing values last.
    """
    to_be_sorted = []
    for h5name, h5item in h5_items:
        child_value = _extract_child_value(h5item, child_name)
        # missing values (None) are sorted last
        sort_key = (child_value is None, _natural_sort_key(child_value))
        to_be_sorted.append((sort_key, h5name, h5item))

    sorted_by_key = sorted(to_be_sorted, key=itemgetter(0))
    return [(h5name, h5item) for _, h5name, h5item in sorted_by_key]


def _extract_child_value(parent, child_name):
    """
    Returns either

    - child value when a scalar or
    - first item of child value when a sequence or
    - None when missing
    """
    try:
        value = parent[child_name][()]
    except Exception:
        return None

    # Get first value in case it is a sequence
    if hasattr(value, "dtype"):
        if hasattr(value, "__len__"):
            if len(value) == 1:
                value = value[0]

    return value


def _natural_sort_key(name):
    """
    Split string in a sequence of types (str, int, str, int, ..., str),
    starts and ends with a string (could be a single string).
    """
    if isinstance(name, bytes):
        name = name.decode("utf-8", "ignore")
    if not isinstance(name, str):
        name = str(name)
    sort_key = []
    for chunk in _NUMERIC_CHARS.split(name):
        if chunk.isdigit():
            sort_key.append(int(chunk))
        else:
            sort_key.append(chunk)
    return tuple(sort_key)


def _h5item_natural_sort_key(item):
    """
    Return natural sort key of the HDF5 item name
    """
    _, h5item = item
    return _natural_sort_key(h5item.name)


_NUMERIC_CHARS = re.compile("([0-9]+)")
