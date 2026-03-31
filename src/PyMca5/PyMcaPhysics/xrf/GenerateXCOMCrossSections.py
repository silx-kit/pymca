#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2014 European Synchrotron Radiation Facility
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
__doc__= "Generate specfile from XCOM generated files"

import sys
import os
from PyMca5.PyMcaPhysics import Elements


def getHeader(filename):
    text  = '#F %s\n' % filename
    text += '#U00 This file is a direct conversion to specfile format of \n'
    text += '#U01 the XCOM selected-arrays output.\n'
    text += '#U02 \n'
    text += '#U03 XCOM itself can be found at:\n'
    text += '#U04   http://www.nist.gov/pml/data/xcom/index.cfm\n'
    text += '\n'
    return text

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("python GenerateXCOMTotalCrossSections SPEC_output_filename Barns_flag")
        sys.exit(0)

    fname = sys.argv[1]
    if os.path.exists(fname):
        os.remove(fname)

    if int(sys.argv[2]):
        BARNS = True
    else:
        BARNS = False
    print("BARNS = %s" % BARNS)
    outfile = open(fname, 'wb')
    outfile.write(getHeader(fname))

    for i in range(1, 101):
        ele = Elements.getsymbol(i)
        print("i = %d element = %s" % (i, ele))
        # force data readout
        dataDict = Elements.getelementmassattcoef(ele)

        # pure XCOM data
        dataDict = Elements.Element[ele]['xcom']

        # energy (keV)
        energy = dataDict['energy']

        # coherent (cm2/g)
        cohe = dataDict['coherent']

        # incoherent
        incohe = dataDict['compton']

        # photoelectric
        photo = dataDict['photo']

        # photoelectric
        pair = dataDict['pair']

        # total
        total = dataDict['total']

        # convert to keV and cut at 500 keV not done for XCOM
        # indices = numpy.nonzero(energy<=500.)
        # energy = energy[indices]
        # photo  = photo[indices]
        # cohe   = cohe[indices]
        # incohe = incohe[indices]

        # I do not cut at 500 keV. I need to take the pair production
        total = photo + cohe + incohe + pair

        #now I am ready to write a Specfile
        text  = '#S %d %s\n' % (i, ele)
        text += '#N 5\n'
        labels = '#L PhotonEnergy[keV]'
        labels += '  Rayleigh(coherent)[barn/atom]'
        labels += '  Compton(incoherent)[barn/atom]'
        labels += '  CoherentPlusIncoherent[barn/atom]'
        labels += '  Photoelectric[barn/atom]'
        labels += '  PairProduction[barn/atom]'
        labels += '  TotalCrossSection[barn/atom]\n'
        if not BARNS:
            labels = labels.replace("barn/atom", "cm2/g")
            factor = 1.0
        else:
            factor = Elements.Element[ele]['mass'] /(1.0E-24*Elements.AVOGADRO_NUMBER)
        text += labels
        if 0:
            fformat = "%g %g %g %g %g %g %g\n"
        else:
            fformat = "%.6E %.6E %.6E %.6E %.6E %.6E %.6E\n"
        outfile.write(text)
        for n in range(len(energy)):
            line = fformat % (energy[n],
                              cohe[n] * factor,
                              incohe[n] * factor,
                              (cohe[n] + incohe[n]) * factor,
                              photo[n] * factor,
                              pair[n] * factor,
                              total[n] * factor)
            outfile.write(line)
        outfile.write('\n')
    outfile.close()
