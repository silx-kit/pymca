#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import os
import numpy
import time
import logging
_logger = logging.getLogger(__name__)
import sys

try:
    from PyMca5.PyMcaIO import EdfFile
    from PyMca5.PyMcaIO import TiffIO
except ImportError:
    _logger.info("ArraySave.py is importing EdfFile and TiffIO from local directory")
    import EdfFile
    import TiffIO

HDF5 = True
try:
    import h5py
    text_dtype = h5py.special_dtype(vlen=str)
except ImportError:
    HDF5 = False


def to_unicode(s):
    """Return string as unicode.

    :param s: A string (bytestring or unicode string).
        If s is a bytestring, it is assumed that it is utf-8 encoded text"""
    if hasattr(s, "decode"):
        return s.decode("utf-8")
    return s


def to_h5py_utf8(str_list):
    """Convert a string or a list of strings to a variable length utf-8 string
    compatible with h5py.
    """
    return numpy.array(str_list, dtype=text_dtype)


def getDate():
    localtime = time.localtime()
    gtime = time.gmtime()
    # year, month, day, hour, minute, second,\
    #      week_day, year_day, delta = time.localtime()
    year = localtime[0]
    month = localtime[1]
    day = localtime[2]
    hour = localtime[3]
    minute = localtime[4]
    second = localtime[5]
    # get the difference against Greenwich
    delta = hour - gtime[3]
    return u"%4d-%02d-%02dT%02d:%02d:%02d%+02d:00" % (year, month, day, hour,
                                                      minute, second, delta)

def saveXY(x, y, filename, xlabel=None, ylabel=None,
                     csv=False, csvseparator=None, fmt=None):
    """
    Convenience function to save two 1D arrays to file as pure ASCII (no header)
    or as CSV.

    - To save in EXCEL compatible format, csv=True and csvseparator=","

    - To save in OMNIC compatible format, csv=False and csvseparator=","
    """
    if xlabel is None:
        xlabel = "x"
    if ylabel is None:
        ylabel = "y"
    root, ext = os.path.splitext(os.path.basename(filename))
    if ext == '':
        if csv:
            filename += ".csv"
        else:
            filename += ".txt"
    if csvseparator is None:
        if csv:
            # CSV default separator set to colon
            csvseparator = ","
        else:
            # ASCII default separator set to double space
            csvseparator = "  "
    if fmt is None:
        fmt = "%.7E%s%.7E\n"
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except OSError:
            _logger.critical("Cannot delete output file <%s>" % filename)
            raise
    with open(filename, mode="wb") as ffile:
        if csv:
            # we write the header line
            ffile.write(('"%s"%s"%s"\n' % \
                         (xlabel, csvseparator, ylabel)).encode("utf-8"))
        for i in range(len(y)):
            ffile.write((fmt % (x[i], csvseparator, y[i])).encode("utf-8"))

def save2DArrayListAsMultipleASCII(datalist, fileroot,
                           labels=None, csv=False, csvseparator=";"):
    if type(datalist) != type([]):
        datalist = [datalist]
    if labels is not None:
        if len(labels) != len(datalist):
            raise ValueError("Incorrect number of labels")
    dirname = os.path.dirname(fileroot)
    root, ext = os.path.splitext(os.path.basename(fileroot))
    if ext == '':
        if csv:
            ext = "csv"
        else:
            ext = "txt"

    n = int(numpy.log10(len(datalist))) + 1
    fmt = "_%" + "0%dd" % n + ".%s"
    for i in range(len(datalist)):
        filename = os.path.join(dirname, root +  fmt % (i, ext))
        save2DArrayListAsASCII(datalist[i], filename,
                           labels=labels, csv=csv, csvseparator=csvseparator)

def save2DArrayListAsASCII(datalist, filename,
                           labels=None, csv=False, csvseparator=";"):
    if type(datalist) != type([]):
        datalist = [datalist]
    r, c = datalist[0].shape
    ndata = len(datalist)
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except OSError:
            _logger.critical("Cannot delete file <%s>" % filename)
    if labels is None:
        labels = []
        for i in range(len(datalist)):
            labels.append("Array_%d" % i)
    if len(labels) != len(datalist):
        raise ValueError("Incorrect number of labels")
    if csv:
        header = '"row"%s"column"' % csvseparator
        for label in labels:
            header += '%s"%s"' % (csvseparator, label)
    else:
        header = "row  column"
        for label in labels:
            header += "  %s" % label
    filehandle = open(filename, 'w+')
    filehandle.write('%s\n' % header)
    fileline = ""
    if csv:
        for row in range(r):
            for col in range(c):
                fileline += "%d" % row
                fileline += "%s%d" % (csvseparator, col)
                for i in range(ndata):
                    fileline += "%s%g" % (csvseparator, datalist[i][row, col])
                fileline += "\n"
                filehandle.write("%s" % fileline)
                fileline = ""
    else:
        for row in range(r):
            for col in range(c):
                fileline += "%d" % row
                fileline += "  %d" % col
                for i in range(ndata):
                    fileline += "  %g" % datalist[i][row, col]
                fileline += "\n"
                filehandle.write("%s" % fileline)
                fileline = ""
    filehandle.write("\n")
    filehandle.close()

def save2DArrayListAsEDF(datalist, filename, labels=None, dtype=None):
    if type(datalist) != type([]):
        datalist = [datalist]
    ndata = len(datalist)
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except OSError:
            pass
    if labels is None:
        labels = []
        for i in range(ndata):
            labels.append("Array_%d" % i)
    if len(labels) != ndata:
        raise ValueError("Incorrect number of labels")
    edfout = EdfFile.EdfFile(filename, access="ab")
    for i in range(ndata):
        if dtype is None:
            edfout.WriteImage({'Title': labels[i]},
                              datalist[i], Append=1)
        else:
            edfout.WriteImage({'Title': labels[i]},
                              datalist[i].astype(dtype),
                              Append=1)
    del edfout  # force file close


def save2DArrayListAsMonochromaticTiff(datalist, filename,
                                       labels=None, dtype=None):
    if type(datalist) != type([]):
        datalist = [datalist]
    ndata = len(datalist)
    if dtype is None:
        dtype = datalist[0].dtype
        for i in range(len(datalist)):
            dtypeI = datalist[i].dtype
            if dtypeI in [numpy.float32, numpy.float64] or\
               dtypeI.str[-2] == 'f':
                dtype = numpy.float32
                break
            elif dtypeI != dtype:
                dtype = numpy.float32
                break
    if labels is None:
        labels = []
        for i in range(ndata):
            labels.append("Array_%d" % i)
    if len(labels) != ndata:
        raise ValueError("Incorrect number of labels")
    multifile = False
    if type(filename) in [type([]), type((1,))]:
        if len(filename) == 1:
            fileList = filename
        elif len(filename) != len(labels):
            raise ValueError("Incorrect number of files")
        else:
            fileList = filename
            multifile = True
    else:
        fileList = [filename]

    savedData = 0
    while savedData < ndata:
        if multifile:
            fname = fileList[savedData]
        else:
            fname = fileList[0]
        if os.path.exists(fname):
            try:
                os.remove(fname)
            except OSError:
                _logger.warning("Cannot remove file %s", fname)
                pass
        if (savedData == 0) or multifile:
            outfileInstance = TiffIO.TiffIO(fname, mode="wb+")
        if multifile:
            # multiple files
            if dtype is None:
                data = datalist[savedData]
            else:
                data = datalist[savedData].astype(dtype)
            outfileInstance.writeImage(data, info={'Title': labels[savedData]})
            savedData += 1
        else:
            # a single file
            for i in range(ndata):
                if i == 1:
                    outfileInstance = TiffIO.TiffIO(fname, mode="rb+")
                if dtype is None:
                    data = datalist[i]
                else:
                    data = datalist[i].astype(dtype)
                outfileInstance.writeImage(data, info={'Title': labels[i]})
                savedData += 1
        outfileInstance.close()  # force file close


def openHDF5File(name, mode='a', **kwargs):
    """
    Open an HDF5 file.

    Valid modes (like Python's file() modes) are:
    - r   Readonly, file must exist
    - r+  Read/write, file must exist
    - w   Create file, truncate if exists
    - w-  Create file, fail if exists
    - a   Read/write if exists, create otherwise (default)

    sorted_with is a callable function like python's builtin sorted, or
    None.
    """

    h5file = h5py.File(name, mode, **kwargs)
    if h5file.mode != 'r' and len(h5file) == 0:
        if 'file_name' not in h5file.attrs:
            h5file.attrs.create('file_name', to_h5py_utf8(name))
        if 'file_time' not in h5file.attrs:
            h5file.attrs.create('file_time', to_h5py_utf8(getDate()))
        if 'HDF5_version' not in h5file.attrs:
            txt = "%s" % h5py.version.hdf5_version
            h5file.attrs.create('HDF5_version', to_h5py_utf8(txt))
        if 'HDF5_API_version' not in h5file.attrs:
            txt = "%s" % h5py.version.api_version
            h5file.attrs.create('HDF5_API_version', to_h5py_utf8(txt))
        if 'h5py_version' not in h5file.attrs:
            txt = "%s" % h5py.version.version
            h5file.attrs.create('h5py_version', to_h5py_utf8(txt))
        if 'creator' not in h5file.attrs:
            h5file.attrs.create('creator', to_h5py_utf8('PyMca'))
        # if 'format_version' not in self.attrs and len(h5file) == 0:
        #     h5file.attrs['format_version'] = __format_version__

    return h5file


def getHDF5FileInstanceAndBuffer(filename, shape,
                                 buffername="data",
                                 dtype=numpy.float32,
                                 interpretation=None,
                                 compression=None):
    if not HDF5:
        raise IOError('h5py does not seem to be installed in your system')

    if os.path.exists(filename):
        try:
            os.remove(filename)
        except Exception:
            raise IOError("Cannot overwrite existing file!")
    hdf = openHDF5File(filename, 'a')
    entryName = "data"

    # entry
    nxEntry = hdf.require_group(entryName)
    if 'NX_class' not in nxEntry.attrs:
        nxEntry.attrs['NX_class'] = u'NXentry'
    elif nxEntry.attrs['NX_class'] not in [b'NXentry', u"NXentry"]:
        # should I raise an error?
        pass
    nxEntry['title'] = u"PyMca saved 3D Array"
    nxEntry['start_time'] = getDate()
    nxData = nxEntry.require_group('NXdata')
    if 'NX_class' not in nxData.attrs:
        nxData.attrs['NX_class'] = u'NXdata'
    elif nxData.attrs['NX_class'] in [b'NXdata', u'NXdata']:
        # should I raise an error?
        pass
    if compression:
        _logger.debug("Saving compressed and chunked dataset")
        chunk1 = int(shape[1] / 10)
        if chunk1 == 0:
            chunk1 = shape[1]
        for i in [11, 10, 8, 7, 5, 4]:
            if (shape[1] % i) == 0:
                chunk1 = int(shape[1] / i)
                break
        chunk2 = int(shape[2] / 10)
        if chunk2 == 0:
            chunk2 = shape[2]
        for i in [11, 10, 8, 7, 5, 4]:
            if (shape[2] % i) == 0:
                chunk2 = int(shape[2] / i)
                break
        data = nxData.require_dataset(buffername,
                                      shape=shape,
                                      dtype=dtype,
                                      chunks=(1, chunk1, chunk2),
                                      compression=compression)
    else:
        #no chunking
        _logger.debug("Saving not compressed and not chunked dataset")
        data = nxData.require_dataset(buffername,
                                      shape=shape,
                                      dtype=dtype,
                                      compression=None)
    nxData.attrs['signal'] = to_unicode(buffername)
    if interpretation is not None:
        data.attrs['interpretation'] = to_unicode(interpretation)

    for i in range(len(shape)):
        dim = numpy.arange(shape[i]).astype(numpy.float32)
        dset = nxData.require_dataset('dim_%d' % i,
                                      dim.shape,
                                      dim.dtype,
                                      dim,
                                      chunks=dim.shape)

    nxData.attrs["axes"] = to_h5py_utf8(['dim_%d' % i
                                         for i in range(len(shape))])

    nxEntry['end_time'] = getDate()
    return hdf, data


def save3DArrayAsMonochromaticTiff(data, filename,
                                   labels=None, dtype=None, mcaindex=-1):
    ndata = data.shape[mcaindex]
    if dtype is None:
        dtype = numpy.float32
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except OSError:
            pass
    if labels is None:
        labels = []
        for i in range(ndata):
            labels.append("Array_%d" % i)
    if len(labels) != ndata:
        raise ValueError("Incorrect number of labels")
    outfileInstance = TiffIO.TiffIO(filename, mode="wb+")
    if mcaindex in [2, -1]:
        for i in range(ndata):
            if i == 1:
                outfileInstance = TiffIO.TiffIO(filename, mode="rb+")
            if dtype is None:
                tmpData = data[:, :, i]
            else:
                tmpData = data[:, :, i].astype(dtype)
            outfileInstance.writeImage(tmpData, info={'Title': labels[i]})
            if (ndata > 10):
                print("Saved image %d of %d" % (i + 1, ndata))
                _logger.info("Saved image %d of %d", i + 1, ndata)
    elif mcaindex == 1:
        for i in range(ndata):
            if i == 1:
                outfileInstance = TiffIO.TiffIO(filename, mode="rb+")
            if dtype is None:
                tmpData = data[:, i, :]
            else:
                tmpData = data[:, i, :].astype(dtype)
            outfileInstance.writeImage(tmpData, info={'Title': labels[i]})
            if (ndata > 10):
                _logger.info("Saved image %d of %d", i + 1, ndata)
                print("Saved image %d of %d" % (i + 1, ndata))
    else:
        for i in range(ndata):
            if i == 1:
                outfileInstance = TiffIO.TiffIO(filename, mode="rb+")
            if dtype is None:
                tmpData = data[i]
            else:
                tmpData = data[i].astype(dtype)
            outfileInstance.writeImage(tmpData, info={'Title': labels[i]})
            if (ndata > 10):
                _logger.info("Saved image %d of %d",
                             i + 1, ndata)
                print("Saved image %d of %d" % (i + 1, ndata))
    outfileInstance.close()  # force file close


# it should be used to name the data that for the time being is named 'data'.
def save3DArrayAsHDF5(data, filename, axes=None, labels=None, dtype=None, mode='nexus',
                      mcaindex=-1, interpretation=None, compression=None):
    if not HDF5:
        raise IOError('h5py does not seem to be installed in your system')
    if (mcaindex == 0) and (interpretation in ["spectrum", None]):
        # stack of images to be saved as stack of spectra
        modify = True
        shape = [data.shape[1], data.shape[2], data.shape[0]]
    elif (mcaindex != 0) and (interpretation in ["image"]):
        # stack of spectra to be saved as stack of images
        modify = True
        shape = [data.shape[2], data.shape[0], data.shape[1]]
    else:
        modify = False
        shape = data.shape
    if dtype is None:
        dtype = data.dtype
    if mode.lower() in ['nexus', 'nexus+']:
        # raise IOError, 'NeXus data saving not implemented yet'
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                raise IOError("Cannot overwrite existing file!")
        hdf = openHDF5File(filename, 'a')
        entryName = "data"
        # entry
        nxEntry = hdf.require_group(entryName)
        if 'NX_class' not in nxEntry.attrs:
            nxEntry.attrs['NX_class'] = u'NXentry'
        elif nxEntry.attrs['NX_class'] not in [b'NXentry', u'NXentry']:
            # should I raise an error?
            pass

        nxEntry['title'] = u"PyMca saved 3D Array"
        nxEntry['start_time'] = getDate()
        nxData = nxEntry.require_group('NXdata')
        if 'NX_class' not in nxData.attrs:
            nxData.attrs['NX_class'] = u'NXdata'
        elif nxData.attrs['NX_class'] not in [u'NXdata', b'NXdata']:
            # should I raise an error?
            pass
        if modify:
            if interpretation in [b"image", u"image"]:
                if compression:
                    _logger.debug("Saving compressed and chunked dataset")
                    #risk of taking a 10 % more space in disk
                    chunk1 = int(shape[1] / 10)
                    if chunk1 == 0:
                        chunk1 = shape[1]
                    for i in [11, 10, 8, 7, 5, 4]:
                        if (shape[1] % i) == 0:
                            chunk1 = int(shape[1] / i)
                            break
                    chunk2 = int(shape[2] / 10)
                    for i in [11, 10, 8, 7, 5, 4]:
                        if (shape[2] % i) == 0:
                            chunk2 = int(shape[2] / i)
                            break
                    dset = nxData.require_dataset('data',
                                                  shape=shape,
                                                  dtype=dtype,
                                                  chunks=(1, chunk1, chunk2),
                                                  compression=compression)
                else:
                    _logger.debug("Saving not compressed and not chunked dataset")
                    #print not compressed -> Not chunked
                    dset = nxData.require_dataset('data',
                                                  shape=shape,
                                                  dtype=dtype,
                                                  compression=None)
                for i in range(data.shape[-1]):
                    tmp = data[:, :, i:i + 1]
                    tmp = tmp.reshape(1, shape[1], shape[2])
                    dset[i, 0:shape[1], :] = tmp
                    _logger.info("Saved item %d of %d",
                                 i + 1, data.shape[-1])
            elif 0:
                # if I do not match the input and output shapes it takes ages
                # to save the images as spectra. However, it is much faster
                # when performing spectra operations.
                dset = nxData.require_dataset('data',
                                              shape=shape,
                                              dtype=dtype,
                                              chunks=(1, shape[1], shape[2]))
                for i in range(data.shape[1]):  # shape[0]
                    chunk = numpy.zeros((1, data.shape[2], data.shape[0]),
                                        dtype)
                    for k in range(data.shape[0]):  # shape[2]
                        if 0:
                            tmpData = data[k:k + 1]
                            for j in range(data.shape[2]):  # shape[1]
                                tmpData = tmpData.reshape(data.shape[1], data.shape[2])
                                chunk[0, j, k] = tmpData[i, j]
                        else:
                            tmpData = data[k:k + 1, i, :]
                            tmpData = numpy.ravel(tmpData)
                            chunk[0, :, k] = tmpData
                    _logger.info("Saving item %d of %d",
                                 i, data.shape[1])
                    dset[i, :, :] = chunk
            else:
                # if I do not match the input and output shapes it takes ages
                # to save the images as spectra. This is a very fast saving, but
                # the performance is awful when reading.
                if compression:
                    _logger.debug("Saving compressed and chunked dataset")
                    dset = nxData.require_dataset('data',
                               shape=shape,
                               dtype=dtype,
                               chunks=(shape[0], shape[1], 1),
                               compression=compression)
                else:
                    _logger.debug("Saving not compressed and not chunked dataset")
                    dset = nxData.require_dataset('data',
                                                  shape=shape,
                                                  dtype=dtype,
                                                  compression=None)
                for i in range(data.shape[0]):
                    tmp = data[i:i + 1, :, :]
                    tmp = tmp.reshape(shape[0], shape[1], 1)
                    dset[:, :, i:i + 1] = tmp
        else:
            if compression:
                _logger.debug("Saving compressed and chunked dataset")
                chunk1 = int(shape[1] / 10)
                if chunk1 == 0:
                    chunk1 = shape[1]
                for i in [11, 10, 8, 7, 5, 4]:
                    if (shape[1] % i) == 0:
                        chunk1 = int(shape[1] / i)
                        break
                chunk2 = int(shape[2] / 10)
                if chunk2 == 0:
                    chunk2 = shape[2]
                for i in [11, 10, 8, 7, 5, 4]:
                    if (shape[2] % i) == 0:
                        chunk2 = int(shape[2] / i)
                        break
                _logger.debug("Used chunk size = (1, %d, %d)",
                              chunk1, chunk2)
                dset = nxData.require_dataset('data',
                                              shape=shape,
                                              dtype=dtype,
                                              chunks=(1, chunk1, chunk2),
                                              compression=compression)
            else:
                _logger.debug("Saving not compressed and notchunked dataset")
                dset = nxData.require_dataset('data',
                                              shape=shape,
                                              dtype=dtype,
                                              compression=None)
            tmpData = numpy.zeros((1, data.shape[1], data.shape[2]),
                                  data.dtype)
            for i in range(data.shape[0]):
                tmpData[0:1] = data[i:i + 1]
                dset[i:i + 1] = tmpData[0:1]
                _logger.info("Saved item %d of %d", i + 1, data.shape[0])

        nxData.attrs["signal"] = u'data'

        if interpretation is not None:
            dset.attrs['interpretation'] = to_unicode(interpretation)

        axesAttribute = []
        for i in range(len(shape)):
            if axes is None:
                dim = numpy.arange(shape[i]).astype(numpy.float32)
                dimlabel = 'dim_%d' % i
            elif axes[i] is not None:
                dim = axes[i]
                try:
                    if labels[i] in [None, 'None']:
                        dimlabel = 'dim_%d' % i
                    else:
                        dimlabel = "%s" % labels[i]
                except Exception:
                    dimlabel = 'dim_%d' % i
            else:
                dim = numpy.arange(shape[i]).astype(numpy.float32)
                dimlabel = 'dim_%d' % i
            axesAttribute.append(dimlabel)
            adset = nxData.require_dataset(dimlabel,
                                           dim.shape,
                                           dim.dtype,
                                           compression=None)
            adset[:] = dim[:]
            adset.attrs['axis'] = i + 1

        nxData.attrs["axes"] = to_h5py_utf8([axAttr for axAttr in axesAttribute])

        nxEntry['end_time'] = getDate()
        if mode.lower() == 'nexus+':
            # create link
            # Deprecated: g = h5py.h5g.open(hdf.fid, '/')
            g = h5py.h5g.open(hdf.id, '/')
            g.link('/data/NXdata/data',
                   '/data/data',
                   h5py.h5g.LINK_HARD)

    elif mode.lower() == 'simplest':
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                raise IOError("Cannot overwrite existing file!")
        hdf = h5py.File(filename, 'a')
        if compression:
            hdf.require_dataset('data',
                                shape=shape,
                                dtype=dtype,
                                data=data,
                                chunks=(1, shape[1], shape[2]),
                                compression=compression)
        else:
            hdf.require_dataset('data',
                                shape=shape,
                                data=data,
                                dtype=dtype,
                                compression=None)
    else:
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                raise IOError("Cannot overwrite existing file!")
        shape = data.shape
        dtype = data.dtype
        hdf = h5py.File(filename, 'a')
        dataGroup = hdf.require_group('data')
        dataGroup.require_dataset('data',
                                  shape=shape,
                                  dtype=dtype,
                                  data=data,
                                  chunks=(1, shape[1], shape[2]))
    hdf.flush()
    hdf.close()


def main():
    a = numpy.arange(1000000.)
    a = a.reshape(20, 50, 1000)
    save3DArrayAsHDF5(a, '/test.h5', mode='nexus+', interpretation='image')
    getHDF5FileInstanceAndBuffer('/test2.h5', (100, 100, 100))
    print("Date String = ", getDate())


if __name__ == "__main__":
    main()

