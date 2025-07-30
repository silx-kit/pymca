#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2019-2025 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
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
__author__ = "Wout De Nolf"
__contact__ = "wout.de_nolf@esrf.eu"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import h5py
import time
import datetime
import numpy
import os
import errno
from collections import Counter
from contextlib import contextmanager
from .. import version

try:
    unicode
except NameError:
    unicode = str


nxcharUnicode = h5py.special_dtype(vlen=unicode)
nxcharBytes = h5py.special_dtype(vlen=bytes)


def asNxChar(s, raiseExtended=True):
    """
    Convert to Variable-length string (array or scalar).
    Uses UTF-8 encoding when possible, otherwise byte-strings
    are used (unless raiseExtended is set).

    :param s: string or sequence of strings
              string types: unicode, bytes, fixed-length numpy
    :param bool raiseExtended: raise UnicodeDecodeError for bytes
                               with extended ASCII encoding
    :returns np.ndarray(nxcharUnicode or nxcharBytes):
    :raises UnicodeDecodeError: extended ASCII encoding
    """
    try:
        # dtype=nxcharUnicode will not attempt decoding bytes
        # so readers will get UnicodeDecodeError when bytes
        # are extended ASCII encoded. So do this instead:
        numpy.array(s, dtype=unicode)
    except UnicodeDecodeError:
        # Reason: byte-string with extended ASCII encoding (e.g. Latin-1)
        # Solution: save as byte-string or raise exception
        # Remark: Clients will read back the data exactly as it is written.
        #         However the HDF5 character set is h5py.h5t.CSET_ASCII
        #         which is strictly speaking not correct.
        if raiseExtended:
            raise
        return numpy.array(s, dtype=nxcharBytes)
    else:
        return numpy.array(s, dtype=nxcharUnicode)


PROGRAM_NAME = asNxChar('pymca')
PROGRAM_VERSION = asNxChar(version())
DEFAULT_PLOT_NAME = 'plotselect'


class LocalTZinfo(datetime.tzinfo):
    """
    Local timezone
    """
    _offset = datetime.timedelta(seconds=-time.altzone)
    _dst = datetime.timedelta(0)
    _name = time.tzname[time.daylight]

    def utcoffset(self, dt):
        return self.__class__._offset

    def dst(self, dt):
        return self.__class__._dst

    def tzname(self, dt):
        return self.__class__._name


localtz = LocalTZinfo()


def timestamp():
    return asNxChar(datetime.datetime.now(tz=localtz).isoformat())


def mkdir(path):
    """
    Create directory recursively when it does not exist

    :param str path:
    :raises OSError:
    """
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise e


def splitUri(uri):
    """
    Split Uniform Resource Identifier (URI)

    :param str uri: URI
    :return tuple: filename(str), group(str)
    """
    lst = uri.split('::')
    if len(lst) == 1:
        h5groupname = ''
    else:
        h5groupname = '/'.join(lst[1:])
    return lst[0], '/' + h5groupname


def iterup(h5group, includeself=True):
    """
    Iterator which yields all parent h5py.Group's up till root

    :param h5py.Group h5group:
    :param bool includeself:
    :returns generator:
    """
    if includeself:
        yield h5group
    while h5group.parent != h5group:
        h5group = h5group.parent
        yield h5group


def isLink(parent, name):
    """
    Check whether node is h5py.SoftLink or h5py.ExternalLink

    :param h5py.Group parent:
    :param str name:
    :returns bool:
    """
    try:
        lnk = parent.get(name, default=None, getlink=True)
    except (KeyError, RuntimeError):
        return False
    else:
        return isinstance(lnk, (h5py.SoftLink, h5py.ExternalLink))


def h5Name(h5group):
    """
    HDF5 Dataset of Group name

    :param h5py.Group h5group:
    :returns str:
    """
    return h5group.name.split('/')[-1]


def nxClass(h5group):
    """
    Nexus class of existing h5py.Group (None when no Nexus instance)

    :param h5py.Group h5group:
    :returns str or None:
    """
    return h5group.attrs.get('NX_class', None)


def isNxClass(h5group, *classes):
    """
    Nexus class of existing h5py.Group (None when no Nexus instance)

    :param h5py.Group h5group:
    :param *classes: list(str) of Nexus classes
    :returns bool:
    """
    return nxClass(h5group) in classes


def raiseIsNxClass(h5group, *classes):
    """
    :param h5py.Group h5group:
    :param *classes: list(str) of Nexus classes
    :raises RuntimeError:
    """
    if isNxClass(h5group, *classes):
        raise RuntimeError('Nexus class not in {}'.format(classes))


def raiseIsNotNxClass(h5group, *classes):
    """
    :param h5py.Group h5group:
    :param *classes: list(str) of Nexus classes
    :raises RuntimeError:
    """
    if not isNxClass(h5group, *classes):
        raise RuntimeError('Nexus class not in {}'.format(classes))


def nxClassNeedsInit(parent, name, nxclass):
    """
    Check whether parent[name] needs Nexus initialization

    :param h5py.Group parent:
    :param str or None name:
    :param str nxclass:
    :returns bool: needs initialization
    :raises RuntimeError: wrong Nexus class
    """
    if name is None:
        return nxclass != nxClass(parent)
    if name in parent:
        _nxclass = nxClass(parent[name])
        if _nxclass != nxclass:
            raise RuntimeError('{} is an instance of {} instead of {}'
                               .format(parent[name].name, _nxclass, nxclass))
        return False
    else:
        parent.create_group(name)
        return True


def updated(h5group):
    """
    h5py.Group has changed

    :param h5py.Group h5group:
    """
    tm = timestamp()
    for group in iterup(h5group):
        nxclass = nxClass(group)
        if nxclass is None:
            continue
        elif nxclass in [u'NXentry', u'NXsubentry']:
            updateDataset(group, 'end_time', tm)
        elif nxclass in [u'NXprocess', u'NXnote']:
            updateDataset(group, 'date', tm)
        elif nxclass == u'NXroot':
            group.attrs['file_update_time'] = tm


def updateDataset(parent, name, data):
    """
    :param h5py.Group parent:
    :param str name:
    :param data:
    """
    if name in parent:
        parent[name][()] = data
    else:
        parent[name] = data


def nxClassInit(parent, name, nxclass, parentclasses=None):
    """
    Initialize Nexus class instance without default attributes and datasets

    :param h5py.Group parent:
    :param str name:
    :param str nxclass:
    :param tuple parentclasses:
    :raises RuntimeError: wrong Nexus class or parent not an Nexus class instance
    """
    if parentclasses:
        raiseIsNotNxClass(parent, *parentclasses)
    else:
        raiseIsNxClass(parent, None)
    if nxClassNeedsInit(parent, name, nxclass):
        h5group = parent[name]
        h5group.attrs['NX_class'] = nxclass
        updated(h5group)


def nxRootInit(h5group):
    """
    Initialize NXroot instance

    :param h5py.Group h5group:
    :raises ValueError: not root
    :raises RuntimeError: wrong Nexus class
    """
    if h5group.name != '/':
        raise ValueError('Group should be the root')
    if nxClassNeedsInit(h5group, None, u'NXroot'):
        h5group.attrs['file_time'] = timestamp()
        h5group.attrs['file_name'] = asNxChar(h5group.file.filename)
        h5group.attrs['HDF5_Version'] = asNxChar(h5py.version.hdf5_version)
        h5group.attrs['h5py_version'] = asNxChar(h5py.version.version)
        h5group.attrs['creator'] = PROGRAM_NAME
        h5group.attrs['NX_class'] = u'NXroot'
        updated(h5group)


def nxEntryInit(parent, name):
    """
    Initialize NXentry instance

    :param h5py.Group parent:
    :raises RuntimeError: wrong Nexus class or parent not NXroot
    """
    raiseIsNotNxClass(parent, u'NXroot')
    if nxClassNeedsInit(parent, name, u'NXentry'):
        h5group = parent[name]
        updateDataset(h5group, 'start_time', timestamp())
        h5group.attrs['NX_class'] = u'NXentry'
        updated(h5group)


def nxNoteInit(parent, name, data=None, type=None):
    """
    Initialize NXnote instance

    :param h5py.Group parent:
    :param str name:
    :param str data:
    :param str type:
    :raises RuntimeError: wrong Nexus class or parent not an Nexus class instance
    """
    raiseIsNxClass(parent, None)
    if nxClassNeedsInit(parent, name, u'NXnote'):
        h5group = parent[name]
        h5group.attrs['NX_class'] = u'NXnote'
        update = True
    else:
        h5group = parent[name]
        update = False
    if data is not None:
        updateDataset(h5group, 'data', asNxChar(data))
        update = True
    if type is not None:
        updateDataset(h5group, 'type', asNxChar(type))
        update = True
    if update:
        updated(h5group)


def nxProcessConfigurationInit(parent, configdict=None):
    """
    Initialize NXnote instance

    :param h5py.Group parent:
    :param ConfigDict configdict:
    :raises RuntimeError: parent not NXprocess
    """
    raiseIsNotNxClass(parent, u'NXprocess')
    if configdict is not None:
        data = configdict.tostring()
        type = 'ini'
    else:
        data = None
        type = None
    name = 'configuration'
    nxNoteInit(parent, name, data=data, type=type)
    updated(parent[name])


def nxProcessInit(parent, name, configdict=None):
    """
    Initialize NXprocess instance

    :param h5py.Group parent:
    :param str name:
    :param ConfigDict configdict:
    :raises RuntimeError: wrong Nexus class or parent not NXentry
    """
    raiseIsNotNxClass(parent, u'NXentry')
    if nxClassNeedsInit(parent, name, u'NXprocess'):
        h5group = parent[name]
        updateDataset(h5group, 'program', PROGRAM_NAME)
        updateDataset(h5group, 'version', PROGRAM_VERSION)
        h5group.attrs['NX_class'] = u'NXprocess'
        updated(h5group)
    else:
        h5group = parent[name]
    nxProcessConfigurationInit(h5group, configdict=configdict)
    nxClassInit(h5group, 'results', u'NXcollection')


@contextmanager
def nxRoot(path, mode='r', **kwargs):
    """
    h5py.File context with NXroot initialization

    :param str path:
    :param str mode: h5py.File modes
    :param **kwargs: see h5py.File
    :returns contextmanager:
    """
    if mode != 'r':
        mkdir(os.path.dirname(path))
    with h5py.File(path, mode=mode, **kwargs) as h5file:
        nxRootInit(h5file)
        yield h5file


def nxEntry(root, name):
    """
    Get NXentry instance (initialize when missing)

    :param h5py.Group root:
    :param str name:
    :returns h5py.Group:
    """
    nxEntryInit(root, name)
    return root[name]


def nxProcess(entry, name, **kwargs):
    """
    Get NXprocess instance (initialize when missing)

    :param h5py.Group entry:
    :param str name:
    :param **kwargs: see nxProcessInit
    :returns h5py.Group:
    """
    nxProcessInit(entry, name, **kwargs)
    return entry[name]


def nxCollection(parent, name):
    """
    Get NXcollection instance (initialize when missing)

    :param h5py.Group parent:
    :param str name:
    :returns h5py.Group:
    """
    nxClassInit(parent, name, u'NXcollection')
    return parent[name]


def nxInstrument(parent, name='instrument'):
    """
    Get NXinstrument instance (initialize when missing)

    :param h5py.Group parent:
    :param str name:
    :returns h5py.Group:
    """
    nxClassInit(parent, name, u'NXinstrument', parentclasses=(u'NXentry',))
    return parent[name]


def nxSubEntry(parent, name):
    """
    Get NXsubentry instance (initialize when missing)

    :param h5py.Group parent:
    :param str name:
    :returns h5py.Group:
    """
    nxClassInit(parent, name, u'NXsubentry', parentclasses=(u'NXentry',))
    return parent[name]


def nxDetector(parent, name):
    """
    Get NXdetector instance (initialize when missing)

    :param h5py.Group parent:
    :param str name:
    :returns h5py.Group:
    """
    nxClassInit(parent, name, u'NXdetector', parentclasses=(u'NXinstrument',))
    return parent[name]


def nxData(parent, name):
    """
    Get NXdata instance (initialize when missing)

    :param h5py.Group parent:
    :param str or None name:
    :returns h5py.Group:
    """
    if name is None:
        name = DEFAULT_PLOT_NAME
    nxClassInit(parent, name, u'NXdata')
    return parent[name]


def nxDataAddAxes(data, axes, append=True):
    """
    Add axes to NXdata instance

    :param h5py.Group data:
    :param list(3-tuple) axes: name(str), value(None,h5py.Dataset,numpy.ndarray), attrs(dict)
    :param bool append:
    """
    raiseIsNotNxClass(data, u'NXdata')
    if append:
        newaxes = data.attrs.get('axes', [])
    else:
        newaxes = []
    for name, value, attrs in axes:
        if value is None:
            pass  # is or will be created elsewhere
        elif isinstance(value, h5py.Dataset):
            if value.parent != data:
                data[name] = h5py.SoftLink(value.name)
        elif isinstance(value, dict):
            data.create_dataset(name, **value)
        else:
            data[name] = value
        if attrs:
            data[name].attrs.update(attrs)
        newaxes.append(name)
    if newaxes:
        data.attrs['axes'] = asNxChar(newaxes)
        updated(data)


def nxDataGetSignals(data):
    """
    Get NXdata signals (default signal first)

    :param h5py.Group data:
    :returns list(str): signal names (default first)
    """
    signal = data.attrs.get('signal', None)
    auxsignals = data.attrs.get('auxiliary_signals', None)
    if signal is None:
        lst = []
    else:
        lst = [signal]
    if auxsignals is not None:
        lst += auxsignals.tolist()
    return lst


def nxDataSetSignals(data, signals):
    """
    Set NXdata signals (default signal first)

    :param h5py.Group data:
    :param list(str) signals:
    """
    if signals:
        data.attrs['signal'] = asNxChar(signals[0])
        if len(signals) > 1:
            data.attrs['auxiliary_signals'] = asNxChar(signals[1:])
        else:
            data.attrs.pop('auxiliary_signals', None)
    else:
        data.attrs.pop('signal', None)
        data.attrs.pop('auxiliary_signals', None)
    updated(data)


def nxDataAddSignals(data, signals, append=True):
    """
    Add signals to NXdata instance

    :param h5py.Group data:
    :param list(3-tuple) signals: name(str),
                                  value(None, h5py.Dataset, numpy.ndarray, dict),
                                  attrs(dict)
    :param bool append:
    """
    raiseIsNotNxClass(data, u'NXdata')
    if append:
        newsignals = nxDataGetSignals(data)
    else:
        newsignals = []
    for name, value, attrs in signals:
        if isinstance(value, dict):
            dset = value.get('data', None)
            if isinstance(dset, h5py.Dataset):
                value = dset
        if value is None:
            pass  # is or will be created elsewhere
        elif isinstance(value, h5py.Dataset):
            if value.file.filename != data.file.filename:
                data[name] = h5py.ExternalLink(value.file.filename, value.name)
            elif value.parent != data:
                data[name] = h5py.SoftLink(value.name)
        elif isinstance(value, dict):
            data.create_dataset(name, **value)
        else:
            data[name] = value
        if attrs:
            data[name].attrs.update(attrs)
        newsignals.append(name)
    if newsignals:
        nxDataSetSignals(data, newsignals)


def nxDataAddErrors(data, errors):
    """
    For each dataset in "data", link to the corresponding dataset in "errors".

    :param h5py.Group data:
    :param h5py.Group errors:
    """
    for name in data:
        dest = errors.get(name, None)
        if dest:
            data[name+'_errors'] = h5py.SoftLink(dest.name)


def selectDatasets(root, match=None):
    """
    Select datasets with given restrictions. In case of `root`
    is an NXdata instance, an additional restriction is imposed:
    the dataset must be specified as a signal (including auxilary signals).

    :param h5py.Group or h5py.Dataset root:
    :param match: restrict selection (callable, 'max_ndim', 'mostcommon_ndim')
    :returns list(h5py.Dataset):
    """
    # accept the list to hande multiple selection for h5 file
    if isinstance(root, (list, tuple)):
        datasets = []
        for single_root in root:
            datasets.extend(selectDatasets(single_root, match=match))
        return datasets

    if match == 'max_ndim':
        match, post = None, match
    elif match == 'mostcommon_ndim':
        match, post = None, match
    else:
        post = None
    if not match:
        def match(dset):
            return True
    datasets = []
    if isinstance(root, h5py.Dataset):
        if match(root):
            datasets = [root]
    else:
        labels = nxDataGetSignals(root)
        if not labels:
            labels = root.keys()
        for label in labels:
            dset = root.get(label, None)
            if not isinstance(dset, h5py.Dataset):
                continue
            if match(dset):
                datasets.append(dset)
        if post == 'max_ndim':
            ndimref = max(dset.ndim for dset in datasets)
        elif post == 'mostcommon_ndim':
            occurences = Counter(dset.ndim for dset in datasets)
            ndimref = occurences.most_common(1)[0][0]
        else:
            ndimref = None
        if ndimref is not None:
            datasets = [dset.ndim == ndimref for dset in datasets]
    return datasets


def markDefault(h5node, nxentrylink=True):
    """
    Mark HDF5 Dataset or Group as default (parents get notified as well)

    :param h5py.Group or h5py.Dataset h5node:
    :param bool nxentrylink: Use a direct link for the default of an NXentry instance
    """
    path = h5node
    nxclass = nxClass(path)
    nxdata = None
    for parent in iterup(path.parent):
        parentnxclass = nxClass(parent)
        if parentnxclass == u'NXdata':
            # path becomes default signal of parent
            signals = nxDataGetSignals(parent)
            signal = h5Name(path)
            if signal in signals:
                signals.pop(signals.index(signal))
            nxDataSetSignals(parent, [signal]+signals)
            updated(parent)
        elif nxclass == u'NXentry':
            # Set this entry as default of root
            parent.attrs['default'] = h5Name(path)
            updated(parent)
        elif parentnxclass is not None:
            if nxclass == u'NXdata':
                # Select the NXdata for plotting
                nxdata = path
            if nxdata:
                if parentnxclass == u'NXentry' and nxentrylink:
                    # Instead of setting the default of parent to the selected NXdata,
                    # create a direct link to the select NXData and set that link as
                    # default of the parent
                    plotname = DEFAULT_PLOT_NAME
                    if isLink(parent, plotname):
                        # parent already has plotname: delete because its merely a link
                        del parent[plotname]
                    if plotname in parent:
                        # parent already has plotname: find non-existent plotname
                        # unless plotname is the selected NXdata, in which case
                        # nothing has to be done
                        if parent[plotname].name != nxdata.name:
                            fmt = plotname + '{}'
                            i = 0
                            while fmt.format(i) in parent:
                                i += 1
                            plotname = fmt.format(i)
                            parent[plotname] = h5py.SoftLink(nxdata.name)
                    else:
                        parent[plotname] = h5py.SoftLink(nxdata.name)
                    parent.attrs['default'] = plotname
                else:
                    # Set default of parent to the selected NXdata
                    parent.attrs['default'] = nxdata.name[len(parent.name)+1:]
                updated(parent)
            if parentnxclass == u'NXroot':
                break
        path = parent
        nxclass = parentnxclass
