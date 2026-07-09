#/*##########################################################################
#
# Copyright (c) 2018 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__ = """
Script writing a stack of XRF data with calibration and live_time information
"""

import os
import numpy
import h5py

# use a dummy 3D array generated using data supplied with PyMca
from PyMca5 import PyMcaDataDir
from PyMca5.PyMcaIO import specfilewrapper as specfile
from PyMca5.PyMcaIO import ConfigDict

dataDir = PyMcaDataDir.PYMCA_DATA_DIR
spe = os.path.join(dataDir, "Steel.spe")
cfg = os.path.join(dataDir, "Steel.cfg")
sf = specfile.Specfile(spe)
y = counts = sf[0].mca(1)
x = channels = numpy.arange(y.size).astype(numpy.float64)
configuration = ConfigDict.ConfigDict()
configuration.read(cfg)
calibration = configuration["detector"]["zero"], \
              configuration["detector"]["gain"], 0.0
initialTime = configuration["concentrations"]["time"]

# create the data
nRows = 5
nColumns = 10
nTimes = 3
data = numpy.zeros((nRows, nColumns, counts.size), dtype = numpy.float64)
live_time = numpy.zeros((nRows * nColumns), dtype=numpy.float64)

mcaIndex = 0
for i in range(nRows):
    for j in range(nColumns):
        factor = (1 + mcaIndex % nTimes)
        data[i, j] = counts * factor
        live_time[i * nColumns + j] = initialTime * factor
        mcaIndex += 1

# now we have a 3D array containing the spectra in data (mandatory)
# we have the channels (not mandatory)
# we have the associated calibration (not mandatory)
# we have the live_time (not mandatory)
# and we are going to create an HDF5 with that information
#
# Just writing those data as a dataset in an HDF5 file would be enough for
# using it in PyMca, but we can create a container group in order to associate
# additional information (channels, live_time, calibration)
# "instrument" can be replaced by, for instance, the beamline name
# "detector" can be replaced by, for instance, "mca_0"
#
h5File = "Steel.h5"
if os.path.exists(h5File):
    os.remove(h5File)
h5 = h5py.File(h5File, "w")
h5["/entry/instrument/detector/calibration"] = calibration
h5["/entry/instrument/detector/channels"] = channels
h5["/entry/instrument/detector/data"] = data
h5["/entry/instrument/detector/live_time"] = live_time

# add nexus conventions (not needed)
h5["/entry/title"] = u"Dummy generated map"
h5["/entry"].attrs["NX_class"] = u"NXentry"
h5["/entry/instrument"].attrs["NX_class"] = u"NXinstrument"
h5["/entry/instrument/detector/"].attrs["NX_class"] = u"NXdetector"
h5["/entry/instrument/detector/data"].attrs["interpretation"] = \
                                                      u"spectrum"
# implement a default plot named measurement (not needed)
h5["/entry/measurement/data"] = \
                    h5py.SoftLink("/entry/instrument/detector/data")
h5["/entry/measurement"].attrs["NX_class"] = u"NXdata"
h5["/entry/measurement"].attrs["signal"] = u"data"
h5["/entry"].attrs["default"] = u"measurement"

h5.flush()
h5.close()
h5 = None
