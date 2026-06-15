#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2018-2023 European Synchrotron Radiation Facility
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
__author__ = "V. Armando Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import unittest
import os
import sys
import numpy
from io import StringIO

cfg = """[attenuators]
kapton = 0, -, 0.0, 0.0, 1.0
atmosphere = 1, Air, 0.00120479, 0.14, 1.0
Matrix = 1, Sample, 1.0, 0.01, 0.1, 90.0, 0, 90.1
deadlayer = 0, Si1, 2.33, 4.5e-06, 1.0
BeamFilter1 = 0, -, 0.0, 0.0, 1.0
BeamFilter0 = 0, -, 0.0, 0.0, 1.0
absorber = 0, -, 0.0, 0.0, 1.0
window = 1, Be1, 1.85, 0.0008, 1.0
contact = 0, Al1, 2.72, 3e-06, 1.0
Filter 6 = 0, -, 0.0, 0.0, 1.0
Filter 7 = 0, -, 0.0, 0.0, 1.0
Detector = 1, Si1, 2.33, 0.045, 1.0

[peaks]
Ni = K
Zn = K, L
Co = K
Sr = K, L
Ca = K
Mn = K
As = K, L
Cd = L
Pb = L, M
Tl = L, M
Ar = K
Ti = K
Fe = K
V = K
Sb = L
Cu = K, L
Se = K, L
Cr = K

[fit]
stripwidth = 10
linearfitflag = 1
xmin = 290
scatterflag = 0
snipwidth = 20
stripfilterwidth = 4
escapeflag = 1
exppolorder = 6
fitweight = 1
stripflag = 1
stripanchorsflag = 0
use_limit = 1
maxiter = 10
stripiterations = 6000
sumflag = 0
linpolorder = 5
stripalgorithm = 0
deltaonepeak = 0.01
deltachi = 0.001
continuum = 0
hypermetflag = 1
stripconstant = 1.0
xmax = 3400
fitfunction = 0
energy = 17.5, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None
stripanchorslist = 3400, 290, 0, 0
energyscatter = 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
energyweight = 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
energyflag = 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

[multilayer]
Layer3 = 0, -, 0.0, 0.0
Layer2 = 0, -, 0.0, 0.0
Layer1 = 0, -, 0.0, 0.0
Layer0 = 1, Water, 1.0, 0.01
Layer7 = 0, -, 0.0, 0.0
Layer6 = 0, -, 0.0, 0.0
Layer5 = 0, -, 0.0, 0.0
Layer4 = 0, -, 0.0, 0.0
Layer9 = 0, -, 0.0, 0.0
Layer8 = 0, -, 0.0, 0.0

[tube]
windowdensity = 1.848
anodedensity = 10.5
windowthickness = 0.0125
anodethickness = 0.0002
transmission = 0
alphax = 90.0
deltaplotting = 0.1
window = Be
filter1thickness = 0.0
anode = Ag
voltage = 30.0
filter1density = 0.000118
alphae = 90.0
filter1 = He

[materials]

[materials.Kapton]
Comment = Kapton 100 HN 25 micron density=1.42 g/cm3
Thickness = 0.0025
Density = 1.42
CompoundFraction = 0.628772, 0.066659, 0.304569
CompoundList = C1, N1, O1

[materials.Teflon]
Comment = Teflon density=2.2 g/cm3
Density = 2.2
CompoundFraction = 0.240183, 0.759817
CompoundList = C1, F1

[materials.Gold]
Comment = Gold
CompoundFraction = 1.0
Thickness = 1e-06
Density = 19.37
CompoundList = Au

[materials.Water]
Comment = Water density=1.0 g/cm3
CompoundFraction = 1.0
Density = 1.0
CompoundList = H2O1

[materials.Sample]
Comment = Water with 500 ppm Co
Thickness = 0.01
Density = 0.1
CompoundFraction = 0.9995, 0.0005
CompoundList = H2O1, Co

[materials.Air]
Comment = Dry Air (Near sea level) density=0.001204790 g/cm3
Thickness = 1.0
Density = 0.0012048
CompoundFraction = 0.000124, 0.75527, 0.23178, 0.012827, 3.2e-06
CompoundList = C1, N1, O1, Ar1, Kr1

[materials.Mylar]
Comment = Mylar (Polyethylene Terephthalate) density=1.40 g/cm3
Density = 1.4
CompoundFraction = 0.041959, 0.625017, 0.333025
CompoundList = H1, C1, O1

[materials.Viton]
Comment = Viton Fluoroelastomer density=1.8 g/cm3
Density = 1.8
CompoundFraction = 0.009417, 0.280555, 0.710028
CompoundList = H1, C1, F1

[concentrations]
usemultilayersecondary = 0
reference = Co
area = 0.10
flux = 190000.0
time = 600.0
useattenuators = 1
usematrix = 1
mmolarflag = 0
distance = 0.3

[detector]
noise = 0.0781703
fixednoise = 0
fixedgain = 0
deltafano = 0.114
fixedfano = 0
sum = 0.0
deltasum = 1e-08
fano = 0.120159
fixedsum = 0
fixedzero = 0
zero = -0.492773
deltazero = 0.1
deltanoise = 0.05
deltagain = 0.001
detele = Si
nthreshold = 4
gain = 0.00502883

[peakshape]
lt_arearatio = 0.2
fixedlt_arearatio = 0
fixedeta_factor = 0
st_arearatio = 0.04
deltalt_arearatio = 0.015
deltaeta_factor = 0.2
deltalt_sloperatio = 7.0
deltastep_heightratio = 5e-05
st_sloperatio = 0.6
lt_sloperatio = 10.0
fixedlt_sloperatio = 0
deltast_arearatio = 0.03
eta_factor = 0.2
fixedst_sloperatio = 0
fixedst_arearatio = 0
deltast_sloperatio = 0.49
step_heightratio = 0.0005
fixedstep_heightratio = 0"""


class testXrf(unittest.TestCase):
    def setUp(self):
        """
        Get the data directory
        """
        self._importSuccess = False
        try:
            from PyMca5 import PyMcaDataDir
            self._importSuccess = True
            self.dataDir = PyMcaDataDir.PYMCA_DATA_DIR
        except Exception:
            self.dataDir = None

    def testTrainingDataDirectoryPresence(self):
        self.assertTrue(self._importSuccess,
                        'Unsuccessful PyMca5.PyMcaDataDir import')
        self.assertTrue(self.dataDir is not None,
                        'Unassigned PyMca5.PyMcaDataDir.PYMCA_DATA_DIR')
        self.assertTrue(os.path.exists(self.dataDir),
                        'Directory "%s" does not exist' % self.dataDir)
        self.assertTrue(os.path.isdir(self.dataDir),
                        '"%s" expected to be a directory' % self.dataDir)

    def testTrainingDataFilePresence(self):
        trainingDataFile = os.path.join(self.dataDir, "XRFSpectrum.mca")
        self.assertTrue(os.path.exists(trainingDataFile),
                        "File %s does not exists" % trainingDataFile)
        self.assertTrue(os.path.isfile(trainingDataFile),
                        "File %s is not an actual file" % trainingDataFile)

    def testTrainingDataFit(self):
        from PyMca5.PyMcaIO import specfilewrapper as specfile
        from PyMca5.PyMcaPhysics.xrf import ClassMcaTheory
        from PyMca5.PyMcaPhysics.xrf import ConcentrationsTool
        from PyMca5.PyMcaIO import ConfigDict
        trainingDataFile = os.path.join(self.dataDir, "XRFSpectrum.mca")
        self.assertTrue(os.path.isfile(trainingDataFile),
                        "File %s is not an actual file" % trainingDataFile)

        sf = specfile.Specfile(trainingDataFile)
        self.assertTrue(len(sf) == 2,
                        "Training data not interpreted as two scans")
        self.assertTrue(sf[0].nbmca() == 0,
                        "Training data 1st scan should contain no MCAs")
        self.assertTrue(sf[1].nbmca() == 1,
                        "Training data 1st scan should contain no MCAs")
        y = mcaData = sf[1].mca(1)
        sf = None

        # perform the actual XRF analysis
        configuration = ConfigDict.ConfigDict()
        configuration.readfp(StringIO(cfg))
        mcaFit = ClassMcaTheory.ClassMcaTheory()
        configuration=mcaFit.configure(configuration)
        x = numpy.arange(y.size).astype(numpy.float64)
        mcaFit.setData(x, y,
                       xmin=configuration["fit"]["xmin"],
                       xmax=configuration["fit"]["xmax"])
        mcaFit.estimate()
        fitResult, result = mcaFit.startFit(digest=1)

        # fit is already done, calculate the concentrations
        concentrationsConfiguration = configuration["concentrations"]
        cTool = ConcentrationsTool.ConcentrationsTool()
        cToolConfiguration = cTool.configure()
        cToolConfiguration.update(configuration['concentrations'])
        # make sure we are using Co as internal standard
        cToolConfiguration["usematrix"] = 1
        cToolConfiguration["reference"] = "Co"
        concentrationsResult, addInfo = cTool.processFitResult( \
                    config=cToolConfiguration,
                    fitresult={"result":result},
                    elementsfrommatrix=False,
                    fluorates = mcaFit._fluoRates,
                    addinfo=True)
        referenceElement = addInfo['ReferenceElement']
        referenceTransitions = addInfo['ReferenceTransitions']
        self.assertTrue(referenceElement == "Co",
               "referenceElement is <%s> instead of <Co>" % referenceElement)
        cobalt = concentrationsResult["mass fraction"]["Co K"]
        self.assertTrue( abs(cobalt-0.0005) < 1.0E-7,
                        "Wrong Co concentration %f expected 0.0005" % cobalt)

        # we should get the same result with internal parameters
        cTool = ConcentrationsTool.ConcentrationsTool()
        cToolConfiguration = cTool.configure()
        cToolConfiguration.update(configuration['concentrations'])

        # make sure we are not using an internal standard
        cToolConfiguration['usematrix'] = 0
        cToolConfiguration['flux'] = addInfo["Flux"]
        cToolConfiguration['time'] = addInfo["Time"]
        cToolConfiguration['area'] = addInfo["DetectorArea"]
        cToolConfiguration['distance'] = addInfo["DetectorDistance"]
        concentrationsResult2, addInfo = cTool.processFitResult( \
                    config=cToolConfiguration,
                    fitresult={"result":result},
                    elementsfrommatrix=False,
                    fluorates = mcaFit._fluoRates,
                    addinfo=True)
        referenceElement = addInfo['ReferenceElement']
        referenceTransitions = addInfo['ReferenceTransitions']
        self.assertTrue(referenceElement in ["None", "", None],
               "referenceElement is <%s> instead of <None>" % referenceElement)

        for key in concentrationsResult["mass fraction"]:
            internal = concentrationsResult["mass fraction"][key]
            fp = concentrationsResult2["mass fraction"][key]
            delta = 100 * (abs(internal - fp) / internal)
            self.assertTrue( delta < 1.0e-5,
                "Error for <%s> concentration %g != %g" % (key, internal, fp))

    def testStainlessSteelDataFit(self):
        from PyMca5.PyMcaIO import specfilewrapper as specfile
        from PyMca5.PyMcaPhysics.xrf import ClassMcaTheory
        from PyMca5.PyMcaPhysics.xrf import ConcentrationsTool
        from PyMca5.PyMcaIO import ConfigDict

        # read the data
        dataFile = os.path.join(self.dataDir, "Steel.spe")
        self.assertTrue(os.path.isfile(dataFile),
                        "File %s is not an actual file" % dataFile)
        sf = specfile.Specfile(dataFile)
        self.assertTrue(len(sf) == 1, "File %s cannot be read" % dataFile)
        self.assertTrue(sf[0].nbmca() == 1,
                        "Spe file should contain MCA data")
        y = counts = sf[0].mca(1)
        x = channels = numpy.arange(y.size).astype(numpy.float64)
        sf = None

        # read the fit configuration
        configFile = os.path.join(self.dataDir, "Steel.cfg")
        self.assertTrue(os.path.isfile(configFile),
                        "File %s is not an actual file" % configFile)
        configuration = ConfigDict.ConfigDict()
        configuration.read(configFile)
        # configure the fit
        # make sure no secondary excitations are used
        configuration["concentrations"]["usemultilayersecondary"] = 0
        mcaFit = ClassMcaTheory.ClassMcaTheory()
        configuration=mcaFit.configure(configuration)
        mcaFit.setData(x, y,
                       xmin=configuration["fit"]["xmin"],
                       xmax=configuration["fit"]["xmax"])
        mcaFit.estimate()
        fitResult, result = mcaFit.startFit(digest=1)

        # concentrations
        # fit is already done, calculate the concentrations
        concentrationsConfiguration = configuration["concentrations"]
        cTool = ConcentrationsTool.ConcentrationsTool()
        cToolConfiguration = cTool.configure()
        cToolConfiguration.update(configuration['concentrations'])

        # make sure we are using Fe as internal standard
        matrix = configuration["attenuators"]["Matrix"]
        self.assertTrue(matrix[1] == "SRM_1155",
                "Invalid matrix. Expected <SRM_1155> got <%s>" % matrix[1])
        cToolConfiguration["usematrix"] = 1
        cToolConfiguration["reference"] = "Fe"
        concentrationsResult, addInfo = cTool.processFitResult( \
                    config=cToolConfiguration,
                    fitresult={"result":result},
                    elementsfrommatrix=False,
                    fluorates = mcaFit._fluoRates,
                    addinfo=True)
        referenceElement = addInfo['ReferenceElement']
        referenceTransitions = addInfo['ReferenceTransitions']
        self.assertTrue(referenceElement == "Fe",
               "referenceElement is <%s> instead of <Fe>" % referenceElement)

        # check the Fe concentration is 0.65 +/ 5 %
        self.assertTrue( \
            abs(concentrationsResult["mass fraction"]["Fe Ka"] - 0.65) < 0.03,
            "Invalid Fe Concentration")
        # check the Cr concentration is overestimated (more than 30 %) %
        testValue = concentrationsResult["mass fraction"]["Cr K"]
        self.assertTrue( testValue > 0.30,
            "Expected Cr concentration above 0.30 got %.3f" % testValue)

        # chek the sum of concentration of main components is above 1
        # because of neglecting higher order excitations
        elements = ["Cr K", "V K", "Mn K", "Fe Ka", "Ni K"]
        total = 0.0
        for element in elements:
            total += concentrationsResult["mass fraction"][element]
        self.assertTrue(total > 1,
                    "Sum of concentrations should be above 1 got %.3f" % total)

        # correct for tertiary excitation without a new fit
        cToolConfiguration["usemultilayersecondary"] = 2
        concentrationsResult, addInfo = cTool.processFitResult( \
                    config=cToolConfiguration,
                    fitresult={"result":result},
                    elementsfrommatrix=False,
                    fluorates = mcaFit._fluoRates,
                    addinfo=True)

        # check the Fe concentration is 0.65 +/ 5 %
        self.assertTrue( \
            abs(concentrationsResult["mass fraction"]["Fe Ka"] - 0.65) < 0.03,
            "Invalid Fe Concentration Using Tertiary Excitation")

        # chek the sum of concentration of main components is above 1
        elements = ["Cr K", "Mn K", "Fe Ka", "Ni K"]
        total = 0.0
        for element in elements:
            total += concentrationsResult["mass fraction"][element]
        self.assertTrue(total < 1,
                   "Sum of concentrations should be below 1 got %.3f" % total)
        # check the Cr concentration is not overestimated (more than 30 %) %
        testValue = concentrationsResult["mass fraction"]["Cr K"]
        self.assertTrue( (testValue > 0.18) and (testValue < 0.20),
            "Expected Cr between 0.18 and 0.20 got %.3f" % testValue)

        # perform the fit already accounting for tertiary excitation
        # in order to get the good fundamental parameters
        configuration["concentrations"]['usematrix'] = 1
        configuration["concentrations"]["usemultilayersecondary"] = 2
        mcaFit.setConfiguration(configuration)
        mcaFit.setData(x, y,
                       xmin=configuration["fit"]["xmin"],
                       xmax=configuration["fit"]["xmax"])
        mcaFit.estimate()
        fitResult, result = mcaFit.startFit(digest=1)

        # concentrations
        # fit is already done, calculate the concentrations
        concentrationsConfiguration = configuration["concentrations"]
        cTool = ConcentrationsTool.ConcentrationsTool()
        cToolConfiguration = cTool.configure()
        cToolConfiguration.update(configuration['concentrations'])
        matrix = configuration["attenuators"]["Matrix"]
        self.assertTrue(matrix[1] == "SRM_1155",
                "Invalid matrix. Expected <SRM_1155> got <%s>" % matrix[1])
        cToolConfiguration["usematrix"] = 1
        cToolConfiguration["reference"] = "Fe"
        concentrationsResult, addInfo = cTool.processFitResult( \
                    config=cToolConfiguration,
                    fitresult={"result":result},
                    elementsfrommatrix=False,
                    fluorates = mcaFit._fluoRates,
                    addinfo=True)

        # make sure we are not using an internal standard
        # repeat everything using a single layer strategy
        configuration["concentrations"]['usematrix'] = 0
        configuration["concentrations"]['flux'] = addInfo["Flux"]
        configuration["concentrations"]['time'] = addInfo["Time"]
        configuration["concentrations"]['area'] = addInfo["DetectorArea"]
        configuration["concentrations"]['distance'] = \
                                                    addInfo["DetectorDistance"]
        configuration["concentrations"]["usemultilayersecondary"] = 2

        # setup the strategy starting with Fe as matrix
        matrix[1] = "Fe"
        configuration["attenuators"]["Matrix"] = matrix
        configuration["fit"]["strategyflag"] = 1
        configuration["fit"]["strategy"] = "SingleLayerStrategy"
        configuration["SingleLayerStrategy"] = {}
        configuration["SingleLayerStrategy"]["layer"] = "Auto"
        configuration["SingleLayerStrategy"]["iterations"] = 3
        configuration["SingleLayerStrategy"]["completer"] = "-"
        configuration["SingleLayerStrategy"]["flags"] = [1, 1, 1, 1, 0,
                                                         0, 0, 0, 0, 0]
        configuration["SingleLayerStrategy"]["peaks"] = [ "Cr K",
                                                         "Mn K", "Fe Ka",
                                                         "Ni K", "-", "-",
                                                         "-","-","-","-"]
        configuration["SingleLayerStrategy"]["materials"] = ["Cr",
                                                         "Mn", "Fe",
                                                         "Ni", "-", "-",
                                                         "-","-","-"]
        mcaFit = ClassMcaTheory.ClassMcaTheory()
        configuration=mcaFit.configure(configuration)
        mcaFit.setData(x, y,
                       xmin=configuration["fit"]["xmin"],
                       xmax=configuration["fit"]["xmax"])
        mcaFit.estimate()
        fitResult, result = mcaFit.startFit(digest=1)

        # concentrations
        # fit is already done, calculate the concentrations
        concentrationsConfiguration = configuration["concentrations"]
        cTool = ConcentrationsTool.ConcentrationsTool()
        cToolConfiguration = cTool.configure()
        cToolConfiguration.update(configuration['concentrations'])
        concentrationsResult2, addInfo = cTool.processFitResult( \
                    config=cToolConfiguration,
                    fitresult={"result":result},
                    elementsfrommatrix=False,
                    fluorates = mcaFit._fluoRates,
                    addinfo=True)

        # chek the sum of concentration of main components is above 1
        elements = ["Cr K", "Mn K", "Fe Ka", "Ni K"]
        total = 0.0
        for element in elements:
            if element == "Cr K":
                tolerance = 6 # 6 %
            else:
                tolerance = 5 # 5 %
            previous = concentrationsResult["mass fraction"][element]
            current = concentrationsResult2["mass fraction"][element]
            delta = 100 * (abs(previous - current) / previous)
            self.assertTrue(delta < tolerance,
                "Strategy: Element %s discrepancy too large %.1f %%" % \
                  (element.split()[0], delta))

def getSuite(auto=True):
    testSuite = unittest.TestSuite()
    if auto:
        testSuite.addTest(unittest.TestLoader().loadTestsFromTestCase(testXrf))
    else:
        # use a predefined order
        testSuite.addTest(testXrf("testTrainingDataDirectoryPresence"))
        testSuite.addTest(testXrf("testTrainingDataFilePresence"))
        testSuite.addTest(testXrf("testTrainingDataFit"))
        testSuite.addTest(testXrf("testStainlessSteelDataFit"))
    return testSuite

def test(auto=False):
    return unittest.TextTestRunner(verbosity=2).run(getSuite(auto=auto))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        auto = False
    else:
        auto = True
    result = test(auto)
    sys.exit(not result.wasSuccessful())
