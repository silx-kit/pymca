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
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import sys
import os
import logging
__doc__ =\
"""
The 1997 release of the Evaluated Photon Data Library (EPDL97)

This module parses the EPDL97.DAT that can be downloaded from:

http://www-nds.iaea.org/epdl97/libsall.htm

EPDL contains complete information for particle transport for
atomic number Z = 1-100. The incident photon energy range goes
down to 1 eV.

The original units are in barns and MeV.

The specific data are:

- Coherent scattering

    a) integrated cross section
    b) form factor
    c) real and imaginary anomalous scattering factors
    d) average energy of the scattered photon (MeV)

- Incoherent scattering

    a) integrated cross section
    b) scattering function
    c) average energy of the scattered photon and recoil electron (MeV)

- Total photoelectric reaction

    a) integrated cross section
    b) average energy of the residual atom, i.e. local deposition (MeV)
    c) average energy of the secondary photons and electrons (MeV)

- Photoelectric reaction, by subshell

    a) integrated cross section
    b) average energy of the residual atom, i.e. local deposition (MeV)
    c) average energy of the secondary photons and electrons (MeV)

- Pair production cross section

    a) integrated cross section
    b) average energy of the secondary electron and positron (MeV)

- Triplet production reaction

    a) integrated cross section
    b) average energy of the secondary electron and positron (MeV)


Photoelectric data are only for photo-ionization. Photo-excitation data
is distributed in the separated library EXDL (the Evaluation eXcitation
Data Library). Edges are consistant between EADL, EEDL and EPDL.

The data are organized in blocks with headers.

The first line of the header:

Columns    Format   Definition
1-3         I3      Z  - atomic number
4-6         I3      A  - mass number (in all cases=0 for elemental data)
8-9         I2      Yi - incident particle designator (7 is photon)
11-12       I2      Yo - outgoing particle designator (0, no particle
                                                       7, photon
                                                       8, positron
                                                       9, electron)
14-24       E11.4   AW - atomic mass (amu)

26-31       I6      Date of evaluation (YYMMDD)
32          I1      Iflag - Interpolation flag:
                                  = 0 or 2, linear in x and y
                                  = 3, logarithmic in x, linear in y
                                  = 4, linear in x, logarithmic in y
                                  = 5, logarithmic in x and y

The second line of the header:

Columns    Format   Definition
1-2         I2      C  - reaction descriptor
                                  = 71, coherent scattering
                                  = 72, incoherent scattering
                                  = 73, photoelectric effect
                                  = 74, pair production
                                  = 75, triplet production
                                  = 93, whole atom parameters

3-5         I2      I  - reaction property:
                                  =   0, integrated cross section
                                  =  10, avg. energy of Yo
                                  =  11, avg. energy to the residual atom
                                  = 941, form factor
                                  = 942, scattering function
                                  = 943, imaginary anomalous scatt. factor
                                  = 944, real anomalous scatt. factor

6-8         I3      S  - reaction modifier:
                                  =  0 no X1 field data required
                                  = 91 X1 field data required

22-32       #11.4   X1 - subshell designator
                                      0 if S is 0
                                      if S is 91, subshell designator


                 Summary of the EPDL Data Base
--------------------------------------------------------------------------
Yi    C    S    X1    Yo   I          Data Types
--------------------------------------------------------------------------
                     Coherent scattering
--------------------------------------------------------------------------
7    71    0    0.    0    0          integrated coherent cross section
7    93    0    0.    0    941        form factor
7    93    0    0.    0    943        imaginary anomalous scatt. factor
7    93    0    0.    0    943        real anomalous scatt. factor
7    71    0    0.    7    10         avg. energy of the scattered photon
--------------------------------------------------------------------------
                     Incoherent scattering
--------------------------------------------------------------------------
7    72    0    0.    0    0          integrated incoherent cross section
7    72    0    0.    0    942        scattering function
7    72    0    0.    7    10         avg. energy of the scattered photon
7    72    0    0.    9    10         avg. energy of the recoil electron
--------------------------------------------------------------------------
                          Photoelectric
--------------------------------------------------------------------------
7    73    0    0.    0    0          integrated photoelectric cross section
7    73    0    0.    0    11         avg. energy to the residual atom
7    73    0    0.    7    10         avg. energy of the secondary photons
7    73    0    0.    9    10         avg. energy of the secondary electrons
--------------------------------------------------------------------------
                    Photoelectric (by subshell)
--------------------------------------------------------------------------
7    73    91   *    0     0          integrated photoelectric cross section
7    73    91   *    0     11         avg. energy to the residual atom
7    73    91   *    7     10         avg. energy of the secondary photons
7    73    91   *    9     10         avg. energy of the secondary electrons
--------------------------------------------------------------------------
                         Pair production
--------------------------------------------------------------------------
7    74    0    0.    0    0          integrated pair production cross section
7    74    0    0.    8    10         avg. energy of the secondary positron
7    74    0    0.    9    10         avg. energy of the secondary electron
--------------------------------------------------------------------------
                         Triplet production
--------------------------------------------------------------------------
7    75    0    0.    0    0          integrated triplet production cross section
7    75    0    0.    8    10         avg. energy of the secondary positron
7    75    0    0.    9    10         avg. energy of the secondary electron
---------------------------------------------------------------------------
Yi    C    S    X1    Yo   I          Data Types
--------------------------------------------------------------------------

* -> Subshell designator

Data sorted in ascending order Z -> C -> S -> X1 -> Yo -> I
"""
import numpy
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

#Translation from EADL index to actual shell (Table VI)
import EADLSubshells
SHELL_LIST = EADLSubshells
getSubshellFromValue = EADLSubshells.getSubshellFromValue
getValueFromSubshell = EADLSubshells.getValueFromSubshell

_logger = logging.getLogger(__name__)

AVOGADRO_NUMBER = 6.02214179E23

#Read the EPDL library
# Try to find it in the local directory
EPDL = os.path.join(os.path.dirname(__file__), 'EPDL97.DAT')

if not os.path.exists(EPDL):
    from PyMca5 import PyMcaDataDir
    EPDL = os.path.join(PyMcaDataDir.PYMCA_DATA_DIR, 'EPDL97', 'EPDL97.DAT')


infile = open(EPDL, 'rb')
EPDL97_DATA = infile.read()
infile.close()

#speed up sequential access
LAST_INDEX = -1

#properly write exponential notation
EPDL97_DATA = EPDL97_DATA.replace('-', 'E-')
EPDL97_DATA = EPDL97_DATA.replace('+', 'E+')

#get rid of tabs if any
EPDL97_DATA = EPDL97_DATA.replace('\t', ' ')

#get rid of carriage returns if any
EPDL97_DATA = EPDL97_DATA.replace('\r\n', '\n')
EPDL97_DATA = EPDL97_DATA.split('\n')
#Now I have a huge list with all the lines
EPDL97_ATOMIC_WEIGHTS = None

def getParticle(value):
    """
    Returns one of ['none', 'photon', 'positron', 'electron'] following
    the convention:
            0 = no particle
            7 = photon
            8 = positron
            9 = electron)
    """
    if value == 7:
        return 'photon'
    if value == 0:
        return 'none'
    if value == 9:
        return 'electron'
    if value == 8:
        return 'positron'
    raise ValueError('Invalid particle code')

def getInterpolationType(value):
    """
    Returns one of ['lin-lin', 'log-lin', 'lin-log', 'log-log'] following
    the convention:
                  0 or 2, linear in x and y         -> returns lin-lin
                  3, logarithmic in x, linear in y  -> returns log-lin
                  4, linear in x, logarithmic in y  -> returns lin-log
                  5, logarithmic in x and y         -> returns log-log
    """
    if value in [0, 2]:
        return 'lin-lin'
    if value == 3:
        return 'log-lin'
    if value == 4:
        return 'lin-log'
    if value == 5:
        return 'log-log'
    raise ValueError('Invalid interpolation flag')

def getReactionFromCode(value):
    """
    The input value must be one of: 71, 72, 73, 74, 75
    Returns one of coherent, incoherent, photoelectric, pair, triplet
    according to the integer EPDL97 code of the reaction:
                    71 <-> coherent scattering
                    72 <-> incoherent scattering
                    73 <-> photoelectric effect
                    74 <-> pair production
                    75 <-> triplet production
                    93 <-> whole atom parameters
    """
    if value == 71:
        return 'coherent'
    if value == 72:
        return 'incoherent'
    if value in [73, 93]:
        return 'photoelectric'
    if value == 74:
        return 'pair'
    if value == 75:
        return 'triplet'
    raise ValueError('Invalid reaction descriptor code')

def getReactionPropertyFromCode(value):
    """
    The input value must be one of: 0, 10, 11, 941, 942, 943, 944
    according to the integer EPDL97 code of the reaction property:
                     0 <-> integrated cross section
                    10 <-> avg. energy of secondary particle Yo
                    11 <-> avg. energy to the residual atom
                   941 <-> form factor
                   942 <-> scattering function
                   943 <-> imaginary anomalous scatt. factor
                   944 <-> real anomalous scatt. factor
    """
    if value == 0:
        return 'cross_section'
    if value == 10:
        return 'secondary_particle_energy'
    if value == 11:
        return 'atom_energy_transfer'
    if value == 941:
        return 'form_factor'
    if value == 942:
        return 'scattering_function'
    if value == 943:
        return 'imaginary_anomalous_scattering_factor'
    if value == 944:
        return 'real_anomalous_scattering_factor'
    raise ValueError('Invalid reaction property descriptor code')

def getCodeFromReaction(text):
    """
    The input text must be one of:
    coherent, incoherent, photoelectric, subshell_photoelectric, pair, triplet
    Returns the integer EPDL97 code of the reaction:
                    71 <-> coherent scattering
                    72 <-> incoherent scattering
                    73 <-> photoelectric effect
                    74 <-> pair production
                    75 <-> triplet production
                    93 <-> whole atom parameters
    """
    tmp = text.lower()
    if 'coherent' in tmp:
        return 71
    if 'incoherent' in tmp:
        return 72
    if 'photo' in tmp:
        return 73
    if 'pair' in tmp:
        return 74
    if 'triplet' in tmp:
        return 75
    raise ValueError('Invalid reaction')


def parseHeader0(line):
    """
    Columns    Format   Definition
    1-3         I3      Z  - atomic number
    4-6         I3      A  - mass number (in all cases=0 for elemental data)
    8-9         I2      Yi - incident particle designator (7 is photon)
    11-12       I2      Yo - outgoing particle designator (0, no particle
                                                           7, photon
                                                           8, positron
                                                           9, electron)
    14-24       E11.4   AW - atomic mass (amu)

    26-31       I6      Date of evaluation (YYMMDD)
    32          I1      Iflag - Interpolation flag:
                                      = 0 or 2, linear in x and y
                                      = 3, logarithmic in x, linear in y
                                      = 4, linear in x, logarithmic in y
                                      = 5, logarithmic in x and y
    """
    item0 = line[0:6]
    items = line[6:].split()
    Z  = int(item0[0:3])
    A  = int(item0[3:6])
    Yi = int(items[0])
    Yo = int(items[1])
    AW = float(items[2])
    Date = items[3]
    Iflag = int(items[4])
    ddict={}
    ddict['atomic_number'] = Z
    ddict['mass_number'] = A
    ddict['atomic_mass'] = AW
    ddict['incident_particle'] = getParticle(Yi)
    ddict['incident_particle_value'] = Yi
    ddict['outgoing_particle'] = getParticle(Yo)
    ddict['outgoing_particle_value'] = Yo
    ddict['date'] = Date
    ddict['interpolation_type'] = getInterpolationType(Iflag)
    ddict['interpolation_flag'] = Iflag
    ddict['Z']  = Z
    ddict['A']  = A
    ddict['Yi'] = Yi
    ddict['Yo'] = Yo
    ddict['AW'] = AW
    return ddict

def parseHeader1(line):
    """
    The second line of the header:

    Columns    Format   Definition
    1-2         I2      C  - reaction descriptor
                                      = 71, coherent scattering
                                      = 72, incoherent scattering
                                      = 73, photoelectric effect
                                      = 74, pair production
                                      = 75, triplet production
                                      = 93, whole atom parameters

    3-5         I2      I  - reaction property:
                                      =   0, integrated cross section
                                      =  10, avg. energy of Yo
                                      =  11, avg. energy to the residual atom
                                      = 941, form factor
                                      = 942, scattering function
                                      = 943, imaginary anomalous scatt. factor
                                      = 944, real anomalous scatt. factor

    6-8         I3      S  - reaction modifier:
                                      =  0 no X1 field data required
                                      = 91 X1 field data required

    22-32       #11.4   X1 - subshell designator
                                          0 if S is 0
                                          if S is 91, subshell designator
    """
    item0 = line[0:6]
    items = line[6:].split()
    C  = int(item0[0:2])
    I  = int(item0[2:6])
    S  = int(items[0])
    #there seems to be some dummy number in between
    X1 = float(items[2])
    ddict={}
    ddict['reaction_code'] = C
    ddict['reaction'] = getReactionFromCode(C)
    ddict['reaction_property'] = getReactionPropertyFromCode(I)
    ddict['reaction_property_code'] = I
    ddict['C'] = C
    ddict['I'] = I
    ddict['S'] = S
    ddict['X1'] = X1
    if S == 91:
        ddict['subshell_code'] = X1
        if X1 != 0.0:
            ddict['subshell'] = getSubshellFromValue(X1)
        else:
            ddict['subshell'] = 'none'
    elif (S == 0) and (X1 == 0.0):
        ddict['subshell_code'] = 0
        ddict['subshell'] = 'none'
    else:
        _logger.error("Inconsistent data")
        _logger.error("X1 = %s; S = %s", X1, S)
        sys.exit(1)
    return ddict

def parseHeader(line0, line1):
    #print("line0 = ", line0)
    #print("line1 = ", line1)
    ddict = parseHeader0(line0)
    ddict.update(parseHeader1(line1))
    return ddict

def getDataLineIndex(lines, z, Yi, C, S, X1, Yo, I, getmode=True):
    global LAST_INDEX
    if (z < 1) or (z>100):
        raise ValueError("Invalid atomic number")
    nlines = len(lines)
    i = LAST_INDEX
    while i < (nlines-1):
        i += 1
        line = lines[i]
        if len(line.split()) < 4:
            continue
        try:
            ddict = parseHeader(lines[i], lines[i+1])
        except Exception:
            _logger.error("Error with lines")
            _logger.error(lines[i])
            _logger.error(lines[i+1])
            _logger.error(sys.exc_info())
            raise
        if ddict['Z'] == z:
            _logger.debug("Z found")
            if ddict['Yi'] == Yi:
                _logger.debug("Yi found")
                if ddict['C'] == C:
                    _logger.debug("C found")
                    if ddict['S'] == S:
                        _logger.debug("S found with X1 = %s", ddict['X1'])
                        _logger.debug("Requested    X1 = %s", X1)
                        _logger.debug(lines[i])
                        _logger.debug(lines[i+1])
                        if ddict['X1'] == X1:
                            if ddict['Yo'] == Yo:
                                if ddict['I'] == I:
                                    _logger.debug("FOUND!")
                                    _logger.debug(lines[i])
                                    _logger.debug(lines[i+1])
                                    LAST_INDEX = i - 1
                                    if getmode:
                                        return i, ddict['interpolation_type']
                                    else:
                                        return i

        i += 1
    if LAST_INDEX > 0:
        _logger.debug("REPEATING")
        LAST_INDEX = -1
        return getDataLineIndex(lines, z, Yi, C, S, X1, Yo, I, getmode=getmode)
    if getmode:
        return -1, 'lin-lin'
    else:
        return -1

def getActualDataFromLinesAndOffset(lines, index):
    data_begin = index + 2
    data_end   = index + 2
    while len(lines[data_end].split()) == 2:
        data_end += 1
    _logger.debug("COMPLETE DATA SET")
    _logger.debug(lines[index:data_end])
    _logger.debug("END DATA SET")
    _logger.debug(lines[data_end])
    _logger.debug("ADDITIONAL LINE")
    ndata = data_end - data_begin
    energy = numpy.zeros((ndata,), numpy.float64)
    value  = numpy.zeros((ndata,), numpy.float64)
    for i in range(ndata):
        t = lines[data_begin+i].split()
        energy[i] = float(t[0])
        value[i]  = float(t[1])
    #print "OBTAINED INDEX = ", index
    #print lines[index:index+10]
    return energy, value

def getAtomicWeights():
    global EPDL97_ATOMIC_WEIGHTS
    if EPDL97_ATOMIC_WEIGHTS is None:
        lines = EPDL97_DATA
        i = 1
        EPDL97_ATOMIC_WEIGHTS = numpy.zeros((len(Elements),), numpy.float64)
        for line in lines:
            if line.startswith('%3d000 ' % i):
                ddict0 = parseHeader0(line)
                EPDL97_ATOMIC_WEIGHTS[i-1] = ddict0['atomic_mass']
                i += 1
    return EPDL97_ATOMIC_WEIGHTS * 1

def getTotalCoherentCrossSection(z, lines=None, getmode=False):
    #Yi    C    S    X1    Yo   I
    #7    71    0    0.    0    0
    if lines is None:
        lines = EPDL97_DATA
    index, mode = getDataLineIndex(lines, z, 7, 71, 0, 0., 0, 0, getmode=True)
    if index < 0:
        raise IOError("Requested data not found")
    energy, value = getActualDataFromLinesAndOffset(lines, index)
    if getmode:
        return energy, value, mode
    else:
        return energy, value

def getTotalIncoherentCrossSection(z, lines=None, getmode=False):
    #Yi    C    S    X1    Yo   I
    #7    72    0    0.    0    0
    if lines is None:
        lines = EPDL97_DATA
    index, mode = getDataLineIndex(lines, z, 7, 72, 0, 0., 0, 0, getmode=True)
    if index < 0:
        raise IOError("Requested data not found")
    energy, value = getActualDataFromLinesAndOffset(lines, index)
    if getmode:
        return energy, value, mode
    else:
        return energy, value

def getTotalPhotoelectricCrossSection(z, lines=None, getmode=False):
    #Yi    C    S    X1    Yo   I
    #7    73    0    0.    0    0
    if lines is None:
        lines = EPDL97_DATA
    index, mode = getDataLineIndex(lines, z, 7, 73, 0, 0., 0, 0, getmode=True)
    if index < 0:
        raise IOError("Requested data not found")
    energy, value = getActualDataFromLinesAndOffset(lines, index)
    if getmode:
        return energy, value, mode
    else:
        return energy, value

def getPartialPhotoelectricCrossSection(z, shell, lines=None, getmode=False):
    #Yi    C    S    X1    Yo   I
    #7    73    91   1.    0    0    K   Shell
    #7    73    91   2.    0    0    L   Shell
    #7    73    91   3.    0    0    L1  Shell
    #7    73    91   4.    0    0    L23 Shell
    #7    73    91   5.    0    0    L2  Shell
    #7    73    91   6.    0    0    L3  Shell
    #7    73    91   7.    0    0    M   Shell
    #7    73    91   8.    0    0    M1  Shell
    #7    73    91   9.    0    0    M23 Shell
    #7    73    91  10.    0    0    M2  Shell
    #7    73    91  11.    0    0    M3  Shell
    #7    73    91  12.    0    0    M45 Shell
    #7    73    91  13.    0    0    M4  Shell
    #7    73    91  14.    0    0    M5  Shell
    #7    73    91  15.    0    0    N   Shell
    #7    73    91  16.    0    0    N1  Shell
    #7    73    91  17.    0    0    N23 Shell
    #7    73    91  18.    0    0    N2  Shell
    #7    73    91  19.    0    0    N3  Shell
    #7    73    91  20.    0    0    N45 Shell
    #7    73    91  21.    0    0    N4  Shell
    #7    73    91  22.    0    0    N5  Shell
    #7    73    91  23.    0    0    N67 Shell
    #7    73    91  24.    0    0    N6  Shell
    #7    73    91  25.    0    0    N7  Shell

    #cleanup shell name
    X1 = getValueFromSubshell(shell)
    if lines is None:
        lines = EPDL97_DATA
    index, mode = getDataLineIndex(lines, z, 7, 73, 91, X1, 0, 0, getmode=True)
    if index < 0:
        raise IOError("Requested data not found")
    energy, value = getActualDataFromLinesAndOffset(lines, index)
    if getmode:
        return energy, value, mode
    else:
        return energy, value

def getTotalPairCrossSection(z, lines=None, getmode=False):
    #Yi    C    S    X1    Yo   I
    #7    74    0    0.    0    0
    index, mode = getDataLineIndex(lines, z, 7, 74, 0, 0., 0, 0, getmode=True)
    if lines is None:
        lines = EPDL97_DATA
    if index < 0:
        raise IOError("Requested data not found")
    energy, value = getActualDataFromLinesAndOffset(lines, index)
    if getmode:
        return energy, value, mode
    else:
        return energy, value

def getTotalTripletCrossSection(z, lines=None, getmode=False):
    #Yi    C    S    X1    Yo   I
    #7    75    0    0.    0    0
    index, mode = getDataLineIndex(lines, z, 7, 75, 0, 0., 0, 0, getmode=True)
    if lines is None:
        lines = EPDL97_DATA
    if index < 0:
        raise IOError("Requested data not found")
    energy, value = getActualDataFromLinesAndOffset(lines, index)
    if getmode:
        return energy, value, mode
    else:
        return energy, value

if __name__ == "__main__":
    if len(sys.argv) > 1:
        Z = int(sys.argv[1])
    else:
        Z = 82
    energy, value, mode = getTotalCoherentCrossSection(Z, EPDL97_DATA, getmode=True)
    _logger.info("TOTAL COHERENT %s", mode)
    for i in range(len(energy)):
        if energy[i] > 0.010:
            if energy[i] < 0.020:
                _logger.info("%s, %s", energy[i], value[i])

    energy, value, mode = getTotalIncoherentCrossSection(Z, EPDL97_DATA , getmode=True)
    _logger.info("TOTAL INCOHERENT %s", mode)
    for i in range(len(energy)):
        if energy[i] > 0.010:
            if energy[i] < 0.020:
                _logger.info("%s, %s", energy[i], value[i])

    energy, value, mode = getTotalPhotoelectricCrossSection(Z, EPDL97_DATA, getmode=True)
    _logger.info("TOTAL PHOTOELECTRIC %s", mode)
    for i in range(len(energy)):
        if energy[i] > 0.010:
            if energy[i] < 0.020:
                _logger.info("%s, %s", energy[i], value[i])

    energy, value, mode = getTotalPairCrossSection(Z, EPDL97_DATA, getmode=True)
    _logger.info(" TOTAL PAIR %s", mode)
    for i in range(len(energy)):
        if energy[i] > 0.010:
            if energy[i] < 0.020:
                _logger.info("%s, %s", energy[i], value[i])

    energy, value, mode = getPartialPhotoelectricCrossSection(Z, 'L1', EPDL97_DATA, getmode=True)
    _logger.info("L1 SHELL PARTIAL PHOTOELECTRIC IDX")
    for i in range(len(energy)):
        if energy[i] > 0.010:
            if energy[i] < 0.020:
                _logger.info("%s, %s, %s", energy[i], value[i], mode)

    energy, value, mode = getPartialPhotoelectricCrossSection(Z, 'K', EPDL97_DATA, getmode=True)
    _logger.info("K SHELL PARTIAL PHOTOELECTRIC")
    for i in range(len(energy)):
        if energy[i] > 0.088:
            if energy[i] < 0.090:
                _logger.info("%s, %s, %s", energy[i], value[i], mode)

    _logger.info("atomic weight = %s", getAtomicWeights()[Z-1])
