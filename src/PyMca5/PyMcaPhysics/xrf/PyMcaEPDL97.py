#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2024 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
__doc__= "Interface to the PyMca EPDL97 description"
import os
import sys
from PyMca5.PyMcaIO import specfile
from PyMca5 import getDataFile
import numpy
log = numpy.log
exp = numpy.exp
ElementList = ['H', 'He',
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

EPDL97_FILE = getDataFile("EPDL97_CrossSections.dat")
EADL97_FILE = getDataFile("EADL97_BindingEnergies.dat")

EPDL97_DICT = {}
for element in ElementList:
    EPDL97_DICT[element] = {}

#initialize the dictionary, for the time being compatible with PyMca 4.3.0
EPDL97_DICT = {}
for element in ElementList:
    EPDL97_DICT[element] = {}
    EPDL97_DICT[element]['binding'] = {}
    EPDL97_DICT[element]['EPDL97']  = {}
    EPDL97_DICT[element]['original'] = True

#fill the dictionary with the binding energies
def _initializeBindingEnergies():
    #read the specfile data
    sf = specfile.Specfile(EADL97_FILE)
    scan = sf[0]
    labels = scan.alllabels()
    data = scan.data()
    scan = None
    sf = None
    i = -1
    for element in ElementList:
        if element == 'Md':
            break
        i += 1
        EPDL97_DICT[element]['binding'] = {}
        for j in range(len(labels)):
            if j == 0:
                #this is the atomic number
                continue
            label = labels[j].replace(" ","").split("(")[0]
            EPDL97_DICT[element]['binding'][label] = data[j, i]

_initializeBindingEnergies()

def setElementBindingEnergies(element, ddict):
    """
    Allows replacement of the element internal binding energies by a different
    set of energies. This is made to force this implementaticon of EPDL97 to
    respect other programs absorption edges. Data will be extrapolated when
    needed. WARNING: Coherent resonances are not replaced.
    """
    if len(EPDL97_DICT[element]['EPDL97'].keys()) < 2:
        _initializeElement(element)
    EPDL97_DICT[element]['original'] = False
    EPDL97_DICT[element]['binding']={}
    if 'binding' in ddict:
        EPDL97_DICT[element]['binding'].update(ddict['binding'])
    else:
        EPDL97_DICT[element]['binding'].update(ddict)

def _initializeElement(element):
    """
    _initializeElement(element)
    Supposed to be of internal use.
    Reads the file and loads all the relevant element information contained
    int the EPDL97 file into the internal dictionary.
    """
    #read the specfile data
    sf = specfile.Specfile(EPDL97_FILE)
    scan_index = ElementList.index(element)
    if scan_index > 99:
        #just to avoid a crash
        #I do not expect any fluorescent analysis of these elements ...
        scan_index = 99
    scan = sf[scan_index]
    labels = scan.alllabels()
    data = scan.data()
    scan = None

    #fill the information into the dictionary
    i = -1
    for label0 in labels:
        i += 1
        label = label0.lower()
        #translate the label to the PyMca keys
        if ('coherent' in label) and ('incoherent' not in label):
            EPDL97_DICT[element]['EPDL97']['coherent'] = data[i, :]
            EPDL97_DICT[element]['EPDL97']['coherent'] = numpy.ravel(EPDL97_DICT[element]['EPDL97']['coherent'])
            continue
        if ('incoherent' in label) and ('plus' not in label):
            EPDL97_DICT[element]['EPDL97']['compton'] = data[i, :]
            EPDL97_DICT[element]['EPDL97']['compton'] = numpy.ravel(EPDL97_DICT[element]['EPDL97']['compton'])
            continue
        if 'allother' in label:
            EPDL97_DICT[element]['EPDL97']['all other'] = data[i, :]
            EPDL97_DICT[element]['EPDL97']['all other'] = numpy.ravel(EPDL97_DICT[element]['EPDL97']['all other'])
            continue
        label = label.replace(" ","").split("(")[0]
        if 'energy' in label:
            EPDL97_DICT[element]['EPDL97']['energy'] = data[i, :]
            EPDL97_DICT[element]['EPDL97']['energy'] = numpy.ravel(EPDL97_DICT[element]['EPDL97']['energy'])
            continue
        if 'photoelectric' in label:
            EPDL97_DICT[element]['EPDL97']['photo'] = data[i, :]
            EPDL97_DICT[element]['EPDL97']['photo'] = numpy.ravel(EPDL97_DICT[element]['EPDL97']['photo'])
            #a reference should not be expensive ...
            EPDL97_DICT[element]['EPDL97']['photoelectric'] =\
                                EPDL97_DICT[element]['EPDL97']['photo']
            continue
        if 'total' in label:
            EPDL97_DICT[element]['EPDL97']['total'] = data[i, :]
            EPDL97_DICT[element]['EPDL97']['total'] = numpy.ravel(EPDL97_DICT[element]['EPDL97']['total'])
            continue
        if label[0].upper() in ['K', 'L', 'M']:
            #for the time being I do not use the other shells in PyMca
            EPDL97_DICT[element]['EPDL97'][label.upper()] = data[i, :]
            EPDL97_DICT[element]['EPDL97'][label.upper()] = numpy.ravel(EPDL97_DICT[element]['EPDL97'][label.upper()])
            continue
    EPDL97_DICT[element]['EPDL97']['pair'] = 0.0 *\
                                             EPDL97_DICT[element]['EPDL97']['energy']
    EPDL97_DICT[element]['EPDL97']['photo'] = \
            EPDL97_DICT[element]['EPDL97']['total'] -\
            EPDL97_DICT[element]['EPDL97']['compton']-\
            EPDL97_DICT[element]['EPDL97']['coherent']-\
            EPDL97_DICT[element]['EPDL97']['pair']

    atomic_shells = ['M5', 'M4', 'M3', 'M2', 'M1', 'L3', 'L2', 'L1', 'K']

    # with the new (short) version of the cross-sections file, "all other" contains all
    # shells above the M5. Nevertheless, we calculate it
    if scan_index > 17:
        idx = EPDL97_DICT[element]['EPDL97']['all other'] > 0.0
        delta = 0.0
        for key in atomic_shells:
            delta += EPDL97_DICT[element]['EPDL97'][key]
        EPDL97_DICT[element]['EPDL97']['all other'] =\
                        (EPDL97_DICT[element]['EPDL97']['photo'] - delta) * idx
    else:
        EPDL97_DICT[element]['EPDL97']['all other'] = 0.0 * \
                        EPDL97_DICT[element]['EPDL97']['photo']

    #take care of rounding problems
    idx = EPDL97_DICT[element]['EPDL97']['all other'] < 0.0
    EPDL97_DICT[element]['EPDL97']['all other'][idx] = 0.0


def getElementCrossSections(element, energy=None, forced_shells=None):
    """
    getElementCrossSections(element, energy, forced_shells=None)
    Returns total and partial cross sections of element at the specified
    energies. If forced_shells are not specified, it uses the internal
    binding energies of EPDL97 for all shells. If forced_shells is specified,
    it enforces excitation of the relevant shells via log-log extrapolation
    if needed.
    """
    if forced_shells is None:
        forced_shells = []
    if element not in ElementList:
        raise ValueError("Invalid chemical symbol %s" % element)
    if len(EPDL97_DICT[element]['EPDL97'].keys()) < 2:
        _initializeElement(element)

    if energy is None and EPDL97_DICT[element]['original']:
        return EPDL97_DICT[element]['EPDL97']
    elif energy is None:
        energy = EPDL97_DICT[element]['EPDL97']['energy']

    if hasattr(energy, "__len__"):
        energy = numpy.array(energy, copy=True)
    else:
        energy = numpy.array([energy], copy=True)

    binding = EPDL97_DICT[element]['binding']
    wdata = EPDL97_DICT[element]['EPDL97']
    ddict = {}
    ddict['energy']     = energy
    ddict['coherent']   = numpy.zeros(energy.shape, dtype=numpy.float64)
    ddict['compton']    = numpy.zeros(energy.shape, dtype=numpy.float64)
    ddict['photo']      = numpy.zeros(energy.shape, dtype=numpy.float64)
    ddict['pair']       = numpy.zeros(energy.shape, dtype=numpy.float64)
    ddict['all other']  = numpy.zeros(energy.shape, dtype=numpy.float64)
    ddict['total']      = numpy.zeros(energy.shape, dtype=numpy.float64)
    atomic_shells = ['M5', 'M4', 'M3', 'M2', 'M1', 'L3', 'L2', 'L1', 'K']
    for key in atomic_shells:
        ddict[key] = 0.0 * energy

    #find interpolation point
    len_energy = len(energy)
    for i in range(len_energy):
        x = energy[i]
        if x > wdata['energy'][-2]:
            #take last value or extrapolate?
            print("Warning: Extrapolating data at the end")
            j1 = len(wdata['energy']) - 1
            j0 = j1 - 1
        elif x <= wdata['energy'][0]:
            #take first value or extrapolate?
            print("Warning: Extrapolating data at the beginning")
            j1 = 1
            j0 = 0
        else:
            j0 = numpy.max(numpy.nonzero(wdata['energy'] < x), axis=1)
            if hasattr(j0, "__len__"):
                j0 = j0[0]
            j1 = j0 + 1
        x0 = wdata['energy'][j0]
        x1 = wdata['energy'][j1]
        if x == x1:
            if (j1 + 1 ) < len(wdata['energy']):
                if x1 == wdata['energy'][j1 + 1]:
                    j0 = j1
                    j1 += 1
                    x0 = wdata['energy'][j0]
                    x1 = wdata['energy'][j1]

        #coherent and incoherent
        for key in ['coherent', 'compton', 'pair', 'all other']:
            if (j0 == j1) or ((x1 - x0) < 5.E-10) or ((x1 - x) < 5.E-10) :
                ddict[key][i] =  wdata[key][j1]
            else:
                y0 = wdata[key][j0]
                y1 = wdata[key][j1]
                if (y0 > 0) and (y1 > 0):
                    ddict[key][i] = exp((log(y0) * log(x1/x) +\
                                     log(y1) * log(x/x0))/log(x1/x0))
                elif (y1 > 0) and ((x-x0) > 1.E-5):
                    ddict[key][i] = exp((log(y1) * log(x/x0))/log(x1/x0))


        #partial cross sections
        for key in atomic_shells:
            y0 = wdata[key][j0]
            if (y0 > 0.0) and (x >= binding[key]):
                #standard way
                y1 = wdata[key][j1]
                if (((x1 - x0) < 5.E-10) or ((x1 - x) < 5.E-10)):
                    # no interpolation needed
                    ddict[key][i] = y1
                else:
                    ddict[key][i] = exp((log(y0) * log(x1/x) +\
                                 log(y1) * log(x/x0))/log(x1/x0))
            elif (forced_shells == []) and (x < binding[key]):
                continue
            elif (key in forced_shells) or (x >= binding[key]):
                l = numpy.nonzero(wdata[key] > 0.0)
                if not len(l[0]):
                    continue
                j00 = numpy.min(l)
                j01 = j00 + 1
                x00 = wdata['energy'][j00]
                x01 = wdata['energy'][j01]
                y0 = wdata[key][j00]
                y1 = wdata[key][j01]
                ddict[key][i] = exp((log(y0) * log(x01/x) +\
                                 log(y1) * log(x/x00))/log(x01/x00))

        for key in ['all other'] + atomic_shells:
            ddict['photo'][i] += ddict[key][i]

        for key in ['coherent', 'compton', 'photo']:
            ddict['total'][i] += ddict[key][i]
    for key in ddict.keys():
        ddict[key] = ddict[key].tolist()
    return ddict


def getPhotoelectricWeights(element, shelllist, energy, normalize = None, totals = None):
    """
    getPhotoelectricWeights(element,shelllist,energy,normalize=None,totals=None)
    Given a certain list of shells and one excitation energy, gives back the ratio
    mu(shell, energy)/mu(energy) where mu refers to the photoelectric mass attenuation
    coefficient.
    The special shell "all others" refers to all the shells not in the K, L or M groups.
    Therefore, valid values for the items in the shellist are:
        'K', 'L1', 'L2', 'L3', 'M1', 'M2', 'M3', 'M4', 'M5', 'all other'
    For instance, for the K shell, it is the equivalent of (Jk-1)/Jk where Jk is the k jump.
    If normalize is None or True, normalizes the output to the shells given in shelllist.
    If totals is True, gives back the dictionary with all the mass attenuation coefficients
    used in the calculations.
    """
    if normalize is None:
        normalize = True

    if totals is None:
        totals = False

    #it is not necessary to force shells because the proper way to work is to force this
    #module to respect a given set of binding energies.
    ddict = getElementCrossSections(element, energy=energy, forced_shells=None)

    w = []
    d = ddict['photo'][0]
    for key in shelllist:
        if d > 0.0:
            wi = ddict[key][0]/d
        else:
            wi = 0.0
        w += [wi]

    if normalize:
        total = sum(w)
        for i in range(len(w)):
            if total > 0.0:
                w[i] = w[i]/total
            else:
                w[i] = 0.0

    if totals:
        return w, ddict
    else:
        return w


