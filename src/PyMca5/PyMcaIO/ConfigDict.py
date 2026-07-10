#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2022 European Synchrotron Radiation Facility
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
__author__ = "E. Papillon & V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import os
import sys
import configparser as ConfigParser
from io import StringIO
try:
    import numpy
    USE_NUMPY = True
except ImportError:
    # do not use numpy, use lists
    USE_NUMPY = False


class ConfigDict(dict):
    def __init__(self, defaultdict=None, initdict=None, filelist=None):
        if defaultdict is None:
            defaultdict = {}
        dict.__init__(self, defaultdict)
        self.default = defaultdict
        self.filelist = []

        if initdict is not None:
            self.update(initdict)
        if filelist is not None:
            self.read(filelist)

    def reset(self):
        """ Revert to default values
        """
        self.clear()
        self.update(self.default)

    def clear(self):
        """ Clear dictionary
        """
        dict.clear(self)
        self.filelist = []

    def _check(self):
        pass

    def __tolist(self, mylist):
        if mylist is None:
            return None
        if not isinstance(mylist, list):
            return [mylist]
        else:
            return mylist

    def getfiles(self):
        return self.filelist

    def getlastfile(self):
        return self.filelist[len(self.filelist) - 1]

    def __convert(self, option):
        return option

    def read(self, filelist, sections=None):
        """
        read the input file list into the internal dictionary
        """
        filelist = self.__tolist(filelist)
        sections = self.__tolist(sections)

        if not len(filelist):
            return

        hdf5files = []
        for ffile in filelist:
            if not os.path.exists(ffile):
                if "::" in ffile:
                    # check if we have received a URI
                    fname, path = ffile.split("::")
                    if os.path.exists(fname):
                        try:
                            import h5py
                        except ImportError:
                            raise IOError("File <%s> does not exist" % ffile)
                        if h5py.is_hdf5(fname):
                            with h5py.File(fname, "r") as h5:
                                stringOrBytes = h5[path][()]
                                if hasattr(stringOrBytes, "decode"):
                                    stringOrBytes = \
                                                  stringOrBytes.decode("utf-8")
                                config = StringIO(stringOrBytes)
                                self.readfp(config, sections=sections)
                            hdf5files.append(ffile)
                else:
                    raise IOError("File <%s> does not exist" % ffile)

        cleanlist = [fname for fname in filelist if fname not in hdf5files]
        
        cfg = ConfigParser.ConfigParser()
        cfg.optionxform = self.__convert
        read_ok = cfg.read(cleanlist)
        read_nok = [filename for filename in cleanlist if filename not in read_ok]
        if read_nok:
            raise IOError(f"The following files could not be read: {read_nok}")
        self.__read(cfg, sections)

        for ffile in filelist:
            self.filelist.append([ffile, sections])
        self._check()

    def readfp(self, filelike, sections=None):
        """
        read the input file-like object into the internal dictionary
        """
        cfg = ConfigParser.ConfigParser()
        cfg.optionxform = self.__convert
        #readfp was deprecated in Python 3.2 
        if hasattr(cfg, "read_file"):
            cfg.read_file(filelike)
        else:
            cfg.readfp(filelike)
        self.__read(cfg, sections)
        self._check()

    def read_file(self, *var, **kw):
        return self.readfp(*var, **kw)

    def __read(self, cfg, sections=None):
        cfgsect = cfg.sections()

        if sections is None:
            readsect = cfgsect
        else:
            readsect = [sect for sect in cfgsect if sect in sections]

        for sect in readsect:
            ddict = self
            for subsectw in sect.split('.'):
                subsect = subsectw.replace("_|_", ".")
                if not (subsect in ddict):
                    ddict[subsect] = {}
                ddict = ddict[subsect]
            for opt in cfg.options(sect):
                ddict[opt] = self.__parse_data(cfg.get(sect, opt))

    def __parse_data(self, data):
        if len(data):
            if data.find(',') == -1:
                # it is not a list
                if USE_NUMPY and (data[0] == '[') and (data[-1] == ']'):
                    # this looks as an array
                    try:
                        return numpy.array([float(x) for x in data[1:-1].split()])
                    except ValueError:
                        try:
                            if (data[2] == '[') and (data[-3] == ']'):
                                nrows = len(data[3:-3].split('] ['))
                                indata = data[3:-3].replace('] [', ' ')
                                indata = numpy.array([float(x) for x in
                                                      indata.split()])
                                indata = indata.reshape(nrows, -1)
                                return indata
                        except ValueError:
                            pass
        dataline = [line for line in data.splitlines()]
        if len(dataline) == 1:
            return self.__parse_line(dataline[0])
        elif len(dataline) == 0:
            # do not return an empty list but an empty string
            return ""
        else:
            return [self.__parse_line(line) for line in dataline]

    def __parse_line(self, line):
        if line.find(',') != -1:
            if line.endswith(','):
                if ',' in line[:-1]:
                    return [self.__parse_string(sstr.strip())
                            for sstr in line[:-1].split(',')]
                else:
                    return [self.__parse_string(line[:-1].strip())]
            else:
                return [self.__parse_string(sstr.strip())
                        for sstr in line.split(',')]
        else:
            return self.__parse_string(line.strip())

    def __parse_string(self, sstr):
        try:
            return int(sstr)
        except ValueError:
            try:
                return float(sstr)
            except ValueError:
                return sstr

    def tostring(self, sections=None):
        tmp = StringIO()
        sections = self.__tolist(sections)
        self.__write(tmp, self, sections)
        return tmp.getvalue()

    def write(self, filename, sections=None):
        """
        Write the current dictionary to the given filename
        """
        sections = self.__tolist(sections)

        with open(filename, "w") as fp:
            self.__write(fp, self, sections)

    def __write(self, fp, ddict, sections=None, secthead=None):
        dictkey = []
        listkey = []
        valkey = []
        for key in ddict.keys():
            if isinstance(ddict[key], list):
                listkey.append(key)
            elif isinstance(ddict[key], tuple):
                listkey.append(key)
            elif hasattr(ddict[key], 'keys'):
                dictkey.append(key)
            else:
                valkey.append(key)

        for key in valkey:
            if USE_NUMPY:
                if isinstance(ddict[key], numpy.ndarray):
                    fp.write('%s =' % key + ' [ ' +
                             ' '.join([str(val) for val in ddict[key]]) +
                             ' ]\n')
                    continue
            txt = '%s = %s\n' % (key, ddict[key])
            if "%" in txt:
                # when reading configparser needs to see % characters in pairs
                fp.write(txt.replace("%", "%%"))
            else:
                fp.write(txt)

        for key in listkey:
            fp.write('%s = ' % key)
            llist = []
            sep = ', '
            for item in ddict[key]:
                if isinstance(item, list):
                    if len(item) == 1:
                        llist.append('%s,' % item[0])
                    else:
                        llist.append(', '.join([str(val) for val in item]))
                    sep = '\n\t'
                else:
                    llist.append(str(item))
            fp.write('%s\n' % (sep.join(llist)))
        for key in dictkey:
            if secthead is None:
                newsecthead = key.replace(".", "_|_")
            else:
                newsecthead = '%s.%s' % (secthead, key.replace(".", "_|_"))
            #print "newsecthead = ", newsecthead
            fp.write('\n[%s]\n' % newsecthead)
            self.__write(fp, ddict[key], key, newsecthead)


def prtdict(ddict, lvl=0):
    for key in ddict.keys():
        if hasattr(ddict[key], 'keys'):
            print('\t' * lvl),
            print('+', key)
            prtdict(ddict[key], lvl + 1)
        else:
            print('\t' * lvl),
            print('-', key, '=', ddict[key])

def getDictFromPathOrUri(path):
    """
    Takes as input an ini-like file or an HDF5 URI
    """
    cfg = ConfigDict()
    cfg.read(path)
    return cfg

def main():
    if len(sys.argv) > 1:
        config = ConfigDict(filelist=sys.argv[1:])
        prtdict(config)
    else:
        print("USAGE: %s <filelist>" % sys.argv[0])


if __name__ == '__main__':
    main()
