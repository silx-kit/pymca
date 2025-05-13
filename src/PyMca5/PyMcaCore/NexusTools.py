#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2018-2025 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#############################################################################*/
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import posixpath
try:
    # try to import hdf5plugin
    if hdf5plugin not in sys.modules:
        import hdf5plugin
except Exception:
    # but do not crash just because of it
    pass
import h5py
from h5py import File, Dataset, Group
try:
    from silx.io import is_dataset, is_group
except Exception:
    def is_dataset(something):
        return False

    def is_group(something):
        return False

from PyMca5.PyMcaIO.HDF5Utils import sort_h5items

import logging
_logger = logging.getLogger(__name__)

def isGroup(item):
    if isinstance(item, Group):
        return True
    elif hasattr(item, "keys"):
        return True
    elif is_group(item):
        return True
    else:
        return False

def isDataset(item):
    if isinstance(item, Dataset):
        return True
    elif is_dataset(item):
        return True
    else:
        return False


def getEntryName(path, h5file=None):
    """
    Retrieve the top level name (not h5py object) associated to a given path
    despite being or not an NXentry group.
    """
    entry_name = path
    candidate = posixpath.dirname(entry_name)
    while len(candidate) > 1:
        entry_name = candidate
        candidate = posixpath.dirname(entry_name)
    if h5file is not None:
        if entry_name not in h5file["/"]:
            # dealing with a external link?
            items_list = list(h5file["/"].items())
            for key, group in items_list:
                if not isGroup(group):
                    continue
                if group.name == entry_name:
                    link = h5file.get(key, getlink=True)
                    if isinstance(link, h5py.ExternalLink):
                        _logger.info("Dealing with external link")
                        _logger.info("External filename = <%s>" % link.filename)
                        _logger.info("External path = <%s>" % link.path)
                        entry_name = "/" + key
                        break
    return entry_name

def getTitle(h5file, path):
    """
    Retrieve the title associated to the entry asoociated to the provided path
    It returns an emptry string of not title is found
    """
    entry = h5file[getEntryName(path, h5file=h5file)]
    title = ''
    if isGroup(entry) and "title" in entry:
        title = entry["title"][()]
        if hasattr(title, "dtype"):
            _logger.warning("entry title should be a string not an array")
            if hasattr(title, "__len__"):
                if len(title) == 1:
                    title = title[0]
        if hasattr(title, "decode"):
            title = title.decode("utf-8")
    return title

def getNXdataList(h5file, path, objects=False):
    """
    Retrieve the hdf5 group names down a given path where the NXclass attribute
    is set to "NXdata".

    If groups is False (default) it returns the dataset names.
    If groups is True it returns the actual objects.
    """
    return getNXClassList(h5file, path, classes=["NXdata", b"NXdata"], objects=objects)

def getNXClassList(h5file, path, classes, objects=False):
    """
    Retrieve the hdf5 group names down a given path where the NXclass attribute
    is set to one of the items in the classes list.

    If objects is False (default) it returns the group names.
    If objects is True it returns the actual HDF5 group objects.
    """
    pathList =[]
    def visit_function(name, obj):
        if isGroup(obj):
            append = False
            forget = False
            namebased = False
            for key, value in obj.attrs.items():
                if key in ["NX_class", b"NX_class"]:
                    if value in classes:
                        append = True
                    else:
                        forget = True
            if append:
                if objects:
                    pathList.append(obj)
                else:
                    pathList.append(obj.name)
    if hasattr(h5file[path], "visititems"):
        # prevent errors dealing with toplevel datasets
        h5file[path].visititems(visit_function)
    return pathList

def _correct_entry_path(path, entry_in, entry_out):
    if entry_in in path:
        if path.index(entry_in) == 0:
            return entry_out + path[len(entry_in):]
    return path

def sanitizeFilePath(h5file, path, entry=None):
    """
    This deals with the ESRF case of having a top-level entry being an external link
    to another top-level entry but with different name
    """
    try:
        h5file[path]
    except KeyError:
        if entry is None:
            # this can still fail 
            # the case where it fails is when two external links point to two different
            # files with the same entry name. Easily found at ESRF with top level master
            path = _correct_entry_path(path, getEntryName(path), getEntryName(path, h5file))
        else:
            path = _correct_entry_path(path, getEntryName(path), entry)
    return path

def getMcaList(h5file, path, dataset=False, ignore=None):
    """
    Retrieve the hdf5 dataset names down a given path where the interpretation attribute
    is set to "spectrum".

    It also considers as eligible datasets, those whose last dimension is more than 1 and
    their name or parent group name start by mca.

    If dataset is False (default) it returns the dataset names.
    If dataset is True it returns the actual datasets.

    Apparently visititems ignores links. The following situation would not work:

    Actual dataset in /entry/detector/data with no interpretation attribute set
    and link to it named /entry/measurement/mca

    """
    _logger.debug("Received path %s" % path)
    # deal with ESRF external links with different names from the targets
    correct_entry_path = False
    entry_path = getEntryName(path)
    entry_file = getEntryName(path, h5file=h5file)
    _logger.debug("Associated entry name from path %s" % entry_path)
    _logger.debug("Associated entry name from file %s" % entry_file)

    if entry_path:
        if entry_path != entry_file:
            path = _correct_entry_path(path, entry_path, entry_file)
            correct_entry_path = True
    _logger.debug("Finally used path %s" % path)

    if ignore is None:
        ignore = ["channels",
                  "calibration",
                  "live_time",
                  "preset_time",
                  "elapsed_time",
                  "i0",
                  "it",
                  "i0_to_flux_factor",
                  "it_to_flux_factor",
                  "time",
                  "energy"]
    datasetList =[]
    def visit_function(name, obj):
        if is_dataset(obj):
            append = False
            forget = False
            namebased = False
            for key, value in obj.attrs.items():
                if key == "interpretation":
                    if value in ["spectrum", b"spectrum"]:
                        append = True
                    else:
                        forget = True
            if (not append) and (not forget):
                #support (risky) name based solutions too.
                # the dataset name starts with MCA or
                # the parent group starts with MCA
                if posixpath.basename(name).lower().startswith("mca") or \
                   posixpath.basename(posixpath.dirname(name)).lower().startswith("mca"):
                    append = True
                    namebased = True

            if append:
                # an actual MCA spectrum will have more than one channel
                if (not namebased) and ("measurement" in name):
                    # ALBA sets the interpretation attribute to spectrum
                    # to every counter in the measurement group
                    if len(obj.shape) == 1:
                        # I have to figure out if in fact it is just a
                        # misuse of the interpretation attribute
                        posnames = getScannedPositioners(h5file, path)
                        for motor in posnames:
                            if h5file[motor].size == obj.size:
                                append = False
            if append:
                # perform some name filtering
                if posixpath.basename(obj.name).lower() in ignore:
                    append = False

            if append:
                # the measurement group
                if len(obj.shape) > 0:
                    if obj.shape[-1] > 1:
                        if dataset:
                            datasetList.append(obj)
                        else:
                            name = obj.name
                            name = sanitizeFilePath(h5file, name)
                            datasetList.append(name)
    if hasattr(h5file[path], "visititems"):
        # prevent errors dealing with toplevel datasets
        h5file[path].visititems(visit_function)
    return datasetList

def getMcaObjectPaths(h5file, mcaPath):
    """
    Given an h5py instance and the path to a dataset, try to retrieve all the
    paths with associated information needed to build an McaSpectrumObject.

    McaSpectrumObject is a DataObject where data are the counts and the info
    part contains the information below

    - live_time
    - preset_time
    - elapsed_time
    - counts
    - channels
    - calibration

    The information below will be read but is not used as it does not belong to the
    detector but to a yet-to-be-defined PyMca XRF application definition. Please do
    not rely on it.
    
    - i0
    - it
    - i0_to_flux_factor
    - it_to_flux_factor

    """
    if not mcaPath.startswith("/"):
        # this is needed in order to avoid posixpath to return
        # an empty string
        mcaPath = "/" + mcaPath
    mca = {}
    mca["counts"] = mcaPath
    mca["target"] = mcaPath
    mcaKeys = ["channels",
               "calibration",
               "live_time",
               "preset_time",
               "elapsed_time",
               "i0",
               "it",
               "i0_to_flux_factor",
               "it_to_flux_factor"]

    # This initialization is not needed (at least for the time being)
    #mca["channels"] = None
    #mca["live_time"] = None
    #mca["elapsed_time"] = None
    #mca["preset_time"]= None
    #mca["calibration"] = [0.0, 1.0, 0.0]
    #mca["i0"] = None
    #mca["it"] = None
    #mca["i0_to_flux_factor"] = 1.0
    #mca["it_to_flux_factor"] = 1.0

    _logger.info("Input path <%s>" % (mcaPath,))

    # check entry
    entry_item = getEntryName(mcaPath)
    entry_file = getEntryName(mcaPath, h5file=h5file)
    if entry_item != entry_file:
        mcaPath = _correct_entry_path(mcaPath, entry_item, entry_file)

    _logger.info("Used path <%s>" % (mcaPath,))
    
    # look at the same level as the dataset
    parentPath = posixpath.dirname(mcaPath)
    searchPaths =[parentPath]

    # look at a container group named info at the same level
    if "info" in h5file[parentPath]:
        infoPath = posixpath.join(parentPath, "info")
        searchPaths.append(infoPath)

    # look at one level higher if the container is an NXdetector
    detectorPath = posixpath.dirname(parentPath)
    nxClass = ""
    obj = h5file[detectorPath]
    for key, value in obj.attrs.items():
        if key in ["NX_class", b"NX_class"]:
            if value in ["NXdetector", b"NXdetector"]:
                searchPaths.append(detectorPath)

    # look for the relevant information in those groups
    for path in searchPaths:
        group = h5file[path]
        items_list = list(group.items())
        for key, item in items_list:
            baseKey = posixpath.basename(key)
            if (baseKey in mcaKeys) and (key != mcaPath):
                if baseKey not in mca:
                    mca[baseKey] = sanitizeFilePath(h5file, item.name)

    if len(mca) == 2:
        # we found nothing
        # check if we are dealing with a soft link
        basename = posixpath.basename(mcaPath)
        link = h5file[parentPath].get(basename, getlink=True)
        if hasattr(link, "path"):
            if hasattr(link, "filename"):
                # external link
                filename = link.filename
                if os.path.exists(filename):
                    # it should always exist
                    h5file = File(filename, "r")
                    mca = getMcaObjectPaths(h5file, link.path)
                    keys = list(mca.keys())
                    for key in keys:
                        mca[key] = filename + "::" + mca[key]
            else:
                # soft link
                mca = getMcaObjectPaths(h5file, link.path)
            mca["counts"] = mcaPath
    return mca

def getNXClassGroups(h5file, path, classes, single=False):
    """
    Retrieve the hdf5 groups inside a given path where the NX_class attribute
    matches one of the items in the classes list.
    """

    groups = []
    items_list = list(h5file[path].items())
    if ("NXentry" in classes) or (b"NXentry" in classes):
        items_list = sort_h5items(items_list)

    for key, group in items_list:
        if not isGroup(group):
            continue
        for attr in group.attrs:
            if attr in ["NX_class", b"NX_class"]:
                if group.attrs[attr] in classes:
                    groups.append(group)
                    if single:
                        break
        link = h5file.get(key, getlink=True)
        if isinstance(link, h5py.ExternalLink):
            _logger.info("External filename = <%s>" % link.filename)
            _logger.info("External file path = <%s>" % link.path)
    return groups

def getPositionersGroup(h5file, path):
    """
    Retrieve the positioners group associated to a path
    retrieving them from the same entry.

    It assumes they are either in:

    - NXentry/NXinstrument/positioners or
    - NXentry/measurement/pre_scan_snapshot

    """
    entry_path = getEntryName(path, h5file=h5file)
    instrument = getNXClassGroups(h5file, entry_path, ["NXinstrument", b"NXinstrument"], single=True)
    positioners = None
    if len(instrument):
        instrument = instrument[0]
        for key in instrument.keys():
            if key in ["positioners", b"positioners"]:
                try:
                    positioners = instrument[key]
                except KeyError:
                    positioners = None
                    _logger.info("BrokenLink %s %s" % (instrument, key))
                    return positioners
                if not isGroup(positioners):
                    positioners = None
    if positioners is None:
        # sardana stores the positioners inside measurement/pre_scan_snapshot
        entry = h5file[entry_path]
        sardana = "measurement/pre_scan_snapshot"
        if sardana in entry:
            group = entry[sardana]
            if isGroup(group):
                positioners = group
    return positioners

def getStartingPositionersGroup(h5file, path):
    """
    Retrieve the start positioners group associated to a path
    retrieving them from the same entry.

    It assumes they are either in:

    - NXentry/NXinstrument/positioners_start or 
    - NXentry/NXinstrument/positioners or
    - NXentry/measurement/pre_scan_snapshot

    """
    entry_path = getEntryName(path, h5file=h5file)
    instrument = getNXClassGroups(h5file, entry_path, ["NXinstrument", b"NXinstrument"], single=True)
    positioners = None
    if len(instrument):
        instrument = instrument[0]
        for key in instrument.keys():
            if key in ["positioners_start", b"positioners_start"]:
                try:
                    positioners = instrument[key]
                except KeyError:
                    positioners = None
                    _logger.info("BrokenLink %s %s" % (instrument, key))
                    return positioners
                if not isGroup(positioners):
                    positioners = None
    if positioners is None:
        positioners = getPositionersGroup(h5file, path)
    return positioners

def getStartingPositionerValues(h5file, path):
    """
    Retrieve the start positioners names, values and units associated to a path
    retrieving them from the same entry.

    It assumes they are either in:

    - NXentry/NXinstrument/positioners_start or 
    - NXentry/NXinstrument/positioners or
    - NXentry/measurement/pre_scan_snapshot

    """
    nxpositioners = getStartingPositionersGroup(h5file, path)
    positions = list()
    if nxpositioners is None:
        return positions
    for name, dset in nxpositioners.items():
        if not isinstance(dset, h5py.Dataset):
            continue
        idx = (0,) * dset.ndim
        positions.append((name, dset[idx], dset.attrs.get("units", "")))
    return positions

def getMeasurementGroup(h5file, path):
    """
    Retrieve the measurement group associated to a path
    retrieving them from the same entry.

    It looks for:

    - A group named measurement at the entry level
    - The NXdata group at the entry level with the greater number of datasets

    """
    if path in ["/", b"/", "", b""]:
        raise ValueError("path cannot be the toplevel root")
    entry_path = getEntryName(path, h5file=h5file)
    entry = h5file[entry_path]

    if hasattr(entry, "items"):
        items_list = entry.items()
    else:
        # we have received a top level dataset
        return None
    measurement = None
    for key, group in items_list:
        if key in ["measurement", b"measurement"]:
            if isGroup(group):
                measurement = group
    if measurement is None:
        # try to get the default NXdata groups as measurement group
        default = None
        for attr in entry.attrs:
            if attr in ["default", b"default"]:
                default = entry.attrs[attr]
        # hdf5 stores in utf-8 the paths if we got bytes, they need to be converted
        if hasattr(default, "decode"):
            default = default.decode()
        if default is None:
            # get the NXdata group just behind entry that contains more items inside
            # and take it as measurement group
            nxdatas = getNXClassGroups(h5file, entry_path, ["NXdata", b"NXdata"], single=False)
            if len(nxdatas):
                measurement = nxdatas[0]
                nitems = len(measurement)
            for group in nxdatas:
                if len(group) > nitems:
                    measurement = group
                    nitems = len(measurement)
        else:
            # default could be anything ... crashes should be prevented
            if default in entry:
                group = entry[default]
                if isGroup(group):
                    measurement = group
    return measurement

def getInstrumentGroup(h5file, path):
    entry_name = getEntryName(path, h5file=h5file)
    groups = getNXClassGroups(h5file, entry_name, ["NXinstrument", b"NXinstrument"] , single=False)
    n = len(groups)
    if n == 0:
        return None
    else:
        if n > 1:
            _logger.warning("More than one instrument associated to the same entry")
        return groups[0]

def getScannedPositioners(h5file, path):
    """
    Try to retrieve the positioners (aka. motors) that were moved.

    For that:

        - Look for datasets present at measurement and positioners groups
        - Look for positioners with more than one single value
        - Look for datasets present at measurement and title
    """
    entry_name = getEntryName(path, h5file=h5file)
    try:
        title = getTitle(h5file, path)
    except Exception:
        _logger.warning("Error getting title from entry <%s>" % entry_name)
        title = ""
    measurement = getMeasurementGroup(h5file, entry_name)
    scanned = []
    if measurement is not None:
        positioners = getPositionersGroup(h5file, entry_name)
        if positioners is not None:
            priorityPositioners = False
            if priorityPositioners:
                counters = [key for key, item in measurement.items() if isDataset(item)]
                scanned = [item.name for key, item in positioners.items() if key in counters]
            else:
                motors = [key for key, item in positioners.items() if isDataset(item)]
                scanned = [item.name for key, item in measurement.items() if key in motors]
                if len(scanned) > 1:
                    # check that motors are not duplicated without reason
                    scanned = [item.name for key, item in measurement.items() if \
                                          (key in motors) and \
                                          (hasattr(item, "size") and (item.size > 1))]
            if not len(scanned):
                # look for datasets with more than one single value inside positioners
                scanned = [item.name for key, item in positioners.items() if \
                                            isDataset(item) and \
                                            (hasattr(item, "size") and (item.size > 1))]

        if len(title) and hasattr(title, "split"):
            if not len(scanned) or "fscan " in title:
                tokens = title.split()
                scanned = scanned + [item.name for key, item in measurement.items() if \
                                                isDataset(item) and \
                                                (key in tokens)]

        # provide proper sorting
        if len(scanned) > 1 and sys.version_info > (3, 3):
            # sort irrespective of capital or lower case
            scanned.sort(key=str.casefold)
            if len(title) and hasattr(title, "split"):
                indices = []
                tokens = title.split()
                offset = len(tokens) + len(scanned)
                for key in scanned:
                    short = posixpath.basename(key) 
                    if short in tokens:
                        indices.append((tokens.index(short), key))
                    else:
                        indices.append((offset + scanned.index(key), key))
                indices.sort()    
                scanned = [key for idx, key in indices]
    return scanned

if __name__ == "__main__":
    import h5py
    try:
        sourcename=sys.argv[1]
    except Exception:
        print("Usage: NexusTools <file> <key>")
        sys.exit()
    try:
        from silx.io import open as h5open
        h5 = h5open(sourcename)
    except Exception:
        h5 = h5py.File(sourcename, 'r')
    entries = getNXClassGroups(h5, "/", ["NXentry", b"NXentry"], single=False)
    print("entries = ", entries)
    if not len(entries):
        entries = [item for name, item in h5["/"].items() if isGroup(item)]
    for entry in entries:
        if "title" in entry:
            print("Entry title = %s" % entry["title"][()])
        measurement = getMeasurementGroup(h5, entry.name)
        if measurement is None:
            print("No measurement")
        else:
            print("Measurement name = %s " % measurement.name)
        instrument = getInstrumentGroup(h5, entry.name)
        if instrument is None:
            print("No instrument")
        else:
            print("Instrument name = %s " % instrument.name)
        positioners = getPositionersGroup(h5, entry.name)
        if positioners is None:
            print("No positioners")
        else:
            print("Positioners name = %s " % positioners.name)
        scanned = getScannedPositioners(h5, entry.name)
        if len(scanned):
            for i in range(len(scanned)):
                print("Scanned motors %d = %s" % (i, scanned[i]))
        else:
            print("Unknown scanned motors")
        mca = getMcaList(h5, entry.name, dataset=False)
        if len(mca):
            for i in range(len(mca)):
                print("MCA dataset %d = %s" % (i, mca[i]))
                info = getMcaObjectPaths(h5, mca[i])
                for key in info:
                    print('mca["%s"] = %s' % (key, info[key]))
        else:
            print("No MCA found")
