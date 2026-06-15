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


    keys = list(sorting_list)
    if "title" in keys:
        # move "title" to be priority
        # add standard keys to sort if "title" is the only key
        keys.remove("title")
        if not keys:
            keys = ["start_time", "end_time"]
        keys.insert(0, "title")

    ordered = sorted(h5_items, key=_sort_name)
    # Sort by all keys from lowest priority (last) to highest priority (first)
    for key in reversed(keys):
        ordered = _stable_sort_by_key(ordered, key)
    return ordered


def _stable_sort_by_key(h5_items, key):
    """
    Sorts items by a given HDF5 key, placing items with missing values last
    while preserving the existing order of ties.
    """
    if key == "title":
        # title is never missing
        to_be_sorted = [(False, _natural_sort_key(_extract_h5title(item[1])), item)
                        for item in h5_items]
    else:
        to_be_sorted = []
        for item in h5_items:
            try:
                # natural order like titles ("1.2" is before "1.12")
                # remove `_natural_sort_key` to have regular order
                # it do not affect the time stamps
                missing, value = False, _natural_sort_key(item[1][key][()])
            except Exception:
                missing, value = True, None
            to_be_sorted.append((missing, value, item))

    n_total = len(to_be_sorted)
    n_missing = sum(missing for missing, _, _ in to_be_sorted)
    if n_missing == n_total:
        _logger.debug("Sort by '%s' skipped: not present in any entry", key)
        return h5_items
    try:
        sorted_by_key = sorted(to_be_sorted, key=itemgetter(0, 1))
    except (TypeError, ValueError) as ex:
        # should not appear
        # but potentialy can if same key in different groups have different types
        _logger.debug("Sort by '%s' skipped: values not comparable (%s)", key, ex)
        return h5_items
    if n_missing:
        _logger.debug("Sorted by '%s' (%d of %d entries miss it)", key, n_missing, n_total)
    else:
        _logger.debug("Sorted by '%s'", key)
    return [item for _, _, item in sorted_by_key]


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
    return title


def _sort_name(item):
    return _natural_sort_key(item[1].name)


def _natural_sort_key(name):
    if isinstance(name, bytes):
        name = name.decode("utf-8", "ignore")
    if not isinstance(name, str):
        name = str(name)
    key = []
    for chunk in _NUMERIC_CHARS.split(name):
        if chunk.isdigit():
            key.append(int(chunk))
        else:
            key.append(chunk)
    return tuple(key)

_NUMERIC_CHARS = re.compile('([0-9]+)')
