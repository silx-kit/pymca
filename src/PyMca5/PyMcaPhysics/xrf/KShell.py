#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2016 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"

import os
import numpy
from PyMca5 import getDataFile
from PyMca5.PyMcaIO import specfile

sf=specfile.Specfile(getDataFile("KShellRates.dat"))
ElementKShellTransitions = sf[0].alllabels()
ElementKShellRates = numpy.transpose(sf[0].data()).tolist()

ElementKAlphaTransitions = []
ElementKBetaTransitions = []
for transition in ElementKShellTransitions:
    if transition[0] == 'K':
        if transition[1] == 'L':
            ElementKAlphaTransitions.append(transition)
        else:
            ElementKBetaTransitions.append(transition)
    elif transition[0] == 'Z':
        ElementKAlphaTransitions.append(transition)
        ElementKBetaTransitions.append(transition)
    else:
        #TOTAL column meaningless
        pass

filedata = sf[0].data()
ndata    = sf[0].lines()
ElementKAlphaRates = filedata[0] * 1
ElementKAlphaRates = ElementKAlphaRates.reshape(ndata, 1)
ElementKBetaRates = filedata[0] * 1
ElementKBetaRates = ElementKBetaRates.reshape(ndata, 1)
for transition in ElementKAlphaTransitions:
    if transition[0] != 'Z':
        data = filedata[ElementKShellTransitions.index(transition)] * 1
        data = data.reshape(ndata, 1)
        ElementKAlphaRates = numpy.concatenate((ElementKAlphaRates, data),
                                                 axis = 1)

for transition in ElementKBetaTransitions:
    if transition[0] != 'Z':
        data = filedata[ElementKShellTransitions.index(transition)] * 1
        data = data.reshape(ndata, 1)
        ElementKBetaRates = numpy.concatenate((ElementKBetaRates, data),
                                                axis = 1)
for i in range(len(ElementKAlphaTransitions)):
    if ElementKAlphaTransitions[i] != 'Z':
        ElementKAlphaTransitions[i] = ElementKAlphaTransitions[i] + "a"

for i in range(len(ElementKBetaTransitions)):
    if ElementKBetaTransitions[i] != 'Z':
        ElementKBetaTransitions[i] = ElementKBetaTransitions[i] + "b"

ElementKAlphaRates = ElementKAlphaRates.tolist()
ElementKBetaRates  = ElementKBetaRates.tolist()

sf=specfile.Specfile(getDataFile("KShellConstants.dat"))
ElementKShellConstants = sf[0].alllabels()
ElementKShellValues = numpy.transpose(sf[0].data()).tolist()
sf=None

Elements = ['H', 'He',
            'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
            'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
            'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe',
            'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se',
            'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo',
            'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In', 'Sn',
            'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce',
            'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy',
            'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W',
            'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb',
            'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th',
            'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf',
            'Es', 'Fm', 'Md', 'No', 'Lr', 'Rf', 'Db', 'Sg',
            'Bh', 'Hs', 'Mt']


def getsymbol(z):
    return Elements[z-1]

def getz(ele):
    return Elements.index(ele)+1

#fluorescence yields
def getomegak(ele):
    index = ElementKShellConstants.index('omegaK')
    return ElementKShellValues[getz(ele)-1][index]

#Jump ratios following Veigele: Atomic Data Tables 5 (1973) 51-111. p 54 and 55
def getjk(z):
    return (125.0/z) + 3.5

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        ele = sys.argv[1]
        if ele in Elements:
            z = getz(ele)
            print("Atomic  Number = ",z)
            print("K-shell yield = ",getomegak(ele))
            print("K-shell  jump = ",getjk(z))

