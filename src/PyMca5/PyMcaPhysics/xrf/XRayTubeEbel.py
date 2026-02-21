#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2023 European Synchrotron Radiation Facility
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

import sys
import math
import numpy

import sys
from PyMca5.PyMcaMisc import CliUtils
from . import Elements


def continuumEbel(target, e0, e=None, window=None,
                  alphae=None, alphax=None,
                  transmission=None, targetthickness=None,
                  filterlist=None):
    """
    Calculation of X-ray Tube continuum emission spectrum

    Parameters:
    -----------
     target : list [Symbol, density (g/cm2), thickness(cm)] or atomic ymbol
        If set to atomic symbol, the program sets density and thickness of 0.1 cm
     e0 : float
        Tube Voltage in kV
     e : float or array of floats
        Energy of interest. If not given, the program will generate an array of energies
        from 1 to the given tube voltage minus 1 kV in keV.
     window : list
        Tube window [Formula, density, thickness]
     alphae : float
        Angle, in degrees, between electron beam and tube target. Normal incidence is 90.
     alphax : float
        Angle, in degrees, of X-ray exit beam. Normal exit is 90.
     transmission : Boolean, default is False
        If True the X-ray come out of the tube target by the side opposite to the one
        receiving the exciting electron beam.
     targetthickness : Target thickness in cm
        Only considered in transmission case. If not given, the program uses as target
        thickness the maximal penetration depth of the incident electron beam.
     filterlist : [list]
        Additional filters [[Formula, density, thickness], ...]

     Return:
     -------
     result : Array
        Spectral flux density.
        Flux of photons at the given energies in photons/sr/mA/keV/s

    Reference:
        H. Ebel, X-Ray Spectrometry 28 (1999) 255-266
        Tube voltage from 5 to 50 kV
        Electron incident angle from 50 to 90 deg.
        X-Ray take off angle from 90 to 5 deg.
    """
    if type(target) in [type([]), type(list())]:
        element = target[0]
        density = target[1]
        thickness = target[2]
    else:
        element   = target
        density   = Elements.Element[element]['density']
        thickness = 0.1
    if e is None:
        energy = numpy.arange(e0 * 1.0)[1:]
    elif type(e) == type([]):
        energy = numpy.array(e, dtype=numpy.float64)
    elif type(e) == numpy.ndarray:
        energy = numpy.array(e, dtype=numpy.float64)
    else:
        energy = numpy.array([e], dtype=numpy.float64)

    if alphae is None:
        alphae = 75.0
    if alphax is None:
        alphax = 15.0
    if transmission is None:
        transmission = False

    sinalphae = math.sin(math.radians(alphae))
    sinalphax = math.sin(math.radians(alphax))
    sinfactor = sinalphae / sinalphax

    z = Elements.getz(element)
    const = 1.35e+09
    x = 1.109 - 0.00435 * z + 0.00175 * e0


    # calculate intermediate constants from formulae (4) in Ebel's paper
    # eta in Ebel's paper
    m   = 0.1382 - 0.9211 / math.sqrt(z)
    logz = math.log(z)
    eta = 0.1904 - 0.2236 * logz + 0.1292 * pow(logz, 2) - \
          0.0149 * pow(logz, 3)
    eta = eta * pow(e0, m)

    # dephmax? in Ebel's paper
    p3 = 0.787e-05 * math.sqrt(0.0135 * z) * pow(e0, 1.5) + \
         0.735e-06 * pow(e0, 2)
    rhozmax = (Elements.Element[element]['mass'] / z) * p3
    # print "max depth = ",2 * rhozmax

    # and finally we get rhoz
    u0 = e0 / energy
    logu0 = numpy.log(u0)
    p1 = logu0 * (0.49269 - 1.09870 * eta + 0.78557 * pow(eta, 2))
    p2 = 0.70256 - 1.09865 * eta + 1.00460 * pow(eta, 2) + logu0
    rhoz = rhozmax * (p1 / p2)


    # the term dealing with the photoelectric absorption of the Bremsstrahlung
    tau = numpy.array(
        Elements.getMaterialMassAttenuationCoefficients(element,
                                                        1.0,
                                                        energy)['photo'])

    if not transmission:
        rhelp = tau * 2.0 * rhoz * sinfactor
        if len(numpy.nonzero(rhelp <= 0.0)[0]):
            result = numpy.zeros(rhelp.shape, numpy.float64)
            for i in range(len(rhelp)):
                if rhelp[i] > 0.0:
                    result[i] = const * z * pow(u0[i] - 1.0, x) * \
                         (1.0 - numpy.exp(-rhelp[i])) / rhelp[i]
        else:
            result = const * z * pow(u0 - 1.0, x) * \
                 (1.0 - numpy.exp(-rhelp)) / rhelp

        # the term dealing with absorption in tube's window
        if window is not None:
            if window[2] != 0:
                w = Elements.getMaterialTransmission(window[0], 1.0, energy,
                                                     density=window[1],
                                                     thickness=window[2],
                                                     listoutput=False)['transmission']
                result *= w
        if filterlist is not None:
            w = 1
            for fwindow in filterlist:
                if fwindow[2] == 0:
                    continue
                w *= Elements.getMaterialTransmission(fwindow[0], 1.0, energy,
                                                      density = fwindow[1],
                                                      thickness = fwindow[2],
                                                      listoutput=False)['transmission']
            result *= w
        return result
    # transmission case
    if targetthickness is None:
        #d = Elements.Element[target]['density']
        d = density
        ttarget = 2 * rhozmax
        print("WARNING target thickness assumed equal to maximum depth of %f cm" % (ttarget/d))
    else:
        #ttarget = targetthickness * Elements.Element[target]['density']
        ttarget = targetthickness * density
    # generationdepth = min(ttarget, 2 * rhozmax)
    rhelp = tau * 2.0 * rhoz * sinfactor
    if len(numpy.nonzero(rhelp <= 0.0)[0]):
        result = numpy.zeros(rhelp.shape, numpy.float64)
        for i in range(len(rhelp)):
            if rhelp[i] > 0.0:
                result[i] = const * z * pow(u0[i] - 1.0, x) * \
                     (numpy.exp(-tau[i] *(ttarget - 2.0 * rhoz[i]) / sinalphax) - \
                      numpy.exp(-tau[i] * ttarget / sinalphax)) / rhelp[i]
    else:
        result = const * z * pow(u0 - 1.0, x) * \
             (numpy.exp(-tau *(ttarget - 2.0 * rhoz) / sinalphax) - \
              numpy.exp(-tau * ttarget / sinalphax)) / rhelp
    # the term dealing with absorption in tube's window
    if window is not None:
        if window[2] != 0.0 :
            w = Elements.getMaterialTransmission(window[0], 1.0, energy,
                                                 density=window[1],
                                                 thickness=window[2] / sinalphax,
                                                 listoutput=False)['transmission']
            result *= w
    if filterlist is not None:
        for fwindow in filterlist:
            if fwindow[2] == 0:
                continue
            w = Elements.getMaterialTransmission(fwindow[0], 1.0, energy,
                                                 density=fwindow[1],
                                                 thickness=fwindow[2],
                                                 listoutput=False)['transmission']
            result *= w
    return result

def characteristicEbel(target, e0, window=None,
                       alphae=None, alphax=None,
                       transmission=None, targetthickness=None,
                       filterlist=None):
    """
    Calculation of target characteritic lines and intensities

    Parameters:
    -----------
     target : list [Symbol, density (g/cm2), thickness(cm)] or atomic ymbol
        If set to atomic symbol, the program sets density and thickness of 0.1 cm
     e0 : float
        Tube Voltage in kV
     e : float
        Energy of interest
     window : list
        Tube window [Formula, density, thickness]
     alphae : float
        Angle, in degrees, between electron beam and tube target. Normal incidence is 90.
     alphax : float
        Angle, in degrees, of X-ray exit beam. Normal exit is 90.
     transmission : Boolean, default is False
        If True the X-ray come out of the tube target by the side opposite to the one
        receiving the exciting electron beam.
     targetthickness : Target thickness in cm
        Only considered in transmission case. If not given, the program uses as target
        thickness the maximal penetration depth of the incident electron beam.
     filterlist : [list]
        Additional filters [[Formula, density, thickness], ...]

    Result: list
        Characteristic lines and intensities in the form
        [[energy0, intensity0, name0], [energy1, intensity1, name1], ...]
        Energies in keV
        Intensities in photons/sr/mA/keV/s
    """
    if type(target) == type([]):
        element = target[0]
        density = target[1]
        thickness = target[2]
        if targetthickness is None:
            targetthickness = target[2]
    else:
        element   = target
        density   = Elements.Element[element]['density']
        thickness = 0.1

    if alphae is None:
        alphae = 75.0
    if alphax is None:
        alphax = 15.0
    if transmission is None:
        transmission = False

    sinalphae = math.sin(math.radians(alphae))
    sinalphax = math.sin(math.radians(alphax))
    sinfactor = sinalphae/sinalphax

    z = Elements.getz(element)
    const = 6.0e+13
    # K Shell
    energy = Elements.Element[element]['binding']['K']
    # get the energy of the characteristic lines
    lines = Elements._getUnfilteredElementDict(element, None, photoweights = True)

    if 0:
        # L shell lines will have to be entered directly by the user
        # L shell
        lpeaks = []
        for label in lines['L xrays']:
            lpeaks.append([lines[label]['energy'],
                              lines[label]['rate'],
                              element+' '+label])
        lfluo = Elements._filterPeaks(lpeaks, ethreshold=0.020,
                                      ithreshold=0.001,
                                      nthreshold=6,
                                      absoluteithreshold=False,
                                      keeptotalrate=True)
        lfluo.sort()
    peaklist = []
    rays = 'K xrays'
    if rays in lines.keys():
        #K shell
        for label in lines[rays]:
            peaklist.append([lines[label]['energy'],
                             lines[label]['rate'],
                             element + ' ' + label])
        fl = Elements._filterPeaks(peaklist, ethreshold=0.020,
                                   ithreshold=0.001,
                                   nthreshold=4,
                                   absoluteithreshold=False,
                                   keeptotalrate=True)

        fl.sort()
        if (energy > 0) and (e0 > energy):
            zk = 2.0
            bk = 0.35
        else:
            for i in range(len(fl)):
                fl[i][1] = 0.00
            return fl

    u0 = e0 / energy
    logu0 = numpy.log(u0)

    # stopping factor
    oneovers = (numpy.sqrt(u0) * logu0 + 2 * (1.0 - numpy.sqrt(u0)))
    oneovers /= u0 * logu0 + 1.0 - u0
    oneovers = 1.0 + 16.05 * numpy.sqrt(0.0135 * z / energy) * oneovers
    oneovers *= (zk * bk / z) * (u0 * logu0 + 1.0 - u0)

    # backscattering factor
    r = 1.0 - 0.0081517 * z + 3.613e-05 * z * z +\
        0.009583 * z * numpy.exp(-u0) + 0.001141 * e0

    # Absorption correction
    # calculate intermediate constants from formulae (4) in Ebel's paper
    # eta in Ebel's paper
    m = 0.1382 - 0.9211 / numpy.sqrt(z)
    logz = numpy.log(z)
    eta = 0.1904 - 0.2236 * logz + 0.1292 * pow(logz, 2) - 0.0149 * pow(logz, 3)
    eta = eta * pow(e0, m)

    # depmax? in Ebel's paper
    p3 = 0.787e-05 * numpy.sqrt(0.0135 * z) * pow(e0, 1.5) + \
        0.735e-06 * pow(e0, 2)
    rhozmax = (Elements.Element[element]['mass'] / z) * p3

    # and finally we get rhoz
    p1 = logu0 * (0.49269 - 1.09870 * eta + 0.78557 * pow(eta, 2))
    p2 = 0.70256 - 1.09865 * eta + 1.00460 * pow(eta, 2) + logu0
    rhoz = rhozmax * (p1 / p2)

    # the term dealing with the photoelectric absorption
    energylist = []
    for i in range(len(fl)):
        energylist.append(fl[i][0])
    tau = numpy.array(
        Elements.getMaterialMassAttenuationCoefficients(element, 1.0,
                                                        energylist)['photo'])
    if not transmission:
        rhelp = tau * 2.0 * rhoz * sinfactor
        w = None
        if window is not None:
            if window[2] != 0.0:
                w = Elements.getMaterialTransmission(window[0], 1.0,
                                                     energylist,
                                                     density=window[1],
                                                     thickness=window[2],
                                                     listoutput=False)['transmission']
        if filterlist is not None:
            for fwindow in filterlist:
                if fwindow[2] == 0:
                    continue
                if w is None:
                    w = Elements.getMaterialTransmission(fwindow[0], 1.0,
                                                         energylist,
                                                         density=fwindow[1],
                                                         thickness=fwindow[2],
                                                         listoutput=False)['transmission']
                else:
                    w *= Elements.getMaterialTransmission(fwindow[0], 1.0,
                                                          energylist,
                                                          density=fwindow[1],
                                                          thickness=fwindow[2],
                                                          listoutput=False)['transmission']
        for i in range(len(fl)):
            if rhelp[i] > 0.0 :
                rhelp[i] = (1.0 - numpy.exp(-rhelp[i])) / rhelp[i]
            else:
                rhelp[i] = 0.0
            intensity = const * oneovers * r * Elements.getomegak(element) * rhelp[i]
            #the term dealing with absorption in tube's window
            if w is not None:
                intensity = intensity * w[i]
            fl[i][1] = intensity * fl[i][1]
        return fl

    #transmission case
    if targetthickness is None:
        d = density
        ttarget = 2 * rhozmax
        print("WARNING target thickness assumed equal to maximum depth of %f cm" % (ttarget/d))
    else:
        ttarget = targetthickness * density
    #generationdepth = min(ttarget, 2 * rhozmax)
    rhelp = tau * 2.0 * rhoz * sinfactor
    w = None
    if (window is not None) or (filterlist is not None):
        if window is not None:
            if window[2] != 0.0:
                w = Elements.getMaterialTransmission(window[0], 1.0,
                                                     energylist,
                                                     density=window[1],
                                                     thickness=window[2] / sinalphax,
                                                     listoutput=False)['transmission']
        if filterlist is not None:
            for fwindow in filterlist:
                if w is None:
                    w = Elements.getMaterialTransmission(fwindow[0], 1.0,
                                                         energylist,
                                                         density=fwindow[1],
                                                         thickness=fwindow[2],
                                                         listoutput=False)['transmission']
                else:
                    w *= Elements.getMaterialTransmission(fwindow[0], 1.0,
                                                          energylist,
                                                          density=fwindow[1],
                                                          thickness=fwindow[2],
                                                          listoutput=False)['transmission']
        for i in range(len(fl)):
            if rhelp[i] > 0.0:
                rhelp[i] = (numpy.exp(-tau[i] *( ttarget - 2.0 * rhoz) / sinalphax) - numpy.exp(-tau[i] * ttarget / sinalphax)) / rhelp[i]
            else:
                rhelp[i] = 0.0
            intensity = const * oneovers * r * Elements.getomegak(element) * rhelp[i]
            if w is not None:
                intensity = intensity * w[i]
            fl[i][1] = intensity * fl[i][1]
    return fl

def generateLists(target, e0, window=None,
                  alphae=None, alphax=None,
                  transmission=None, targetthickness=None,
                  filterlist=None):
    """
    Generate a theoretical X-Ray Tube emission profile

    Parameters:
    -----------
     target : list [Symbol, density (g/cm2), thickness(cm)] or atomic ymbol
        If set to atomic symbol, the program sets density and thickness of 0.1 cm
     e0 : float
        Tube Voltage in kV
     window : list
        Tube window [Formula, density, thickness]
     alphae : float
        Angle, in degrees, between electron beam and tube target. Normal incidence is 90.
     alphax : float
        Angle, in degrees, of X-ray exit beam. Normal exit is 90.
     transmission : Boolean, default is False
        If True the X-ray come out of the tube target by the side opposite to the one
        receiving the exciting electron beam.
     targetthickness : Target thickness in cm
        Only considered in transmission case. If not given, the program uses as target
        thickness the maximal penetration depth of the incident electron beam.
     filterlist : [list]
        Additional filters [[Formula, density, thickness], ...]

     Return:
     -------
     result : Tuple
        [Array of Energies, Array of relative intensities, Array of flags]
        Flag set to 1 means it is a target characteristic energy
        Flag set to 0 means it corresponds to a continuum energy
    """
    e0w = 1.0 * e0
    x1min = 1.4
    step1 = 0.2
    x2min = min(e0 - 2 * step1, 20.0)
    if x2min < 20:
        step2 = step1
    else:
        step2 = 0.5
    x3min = e0w
    x1 = numpy.arange(x1min, x2min+step1, step1)
    x2 = numpy.arange(x2min+step1, x3min, step2)

    # get K shell characteristic lines and intensities
    fllines = characteristicEbel(target, e0, window,
                                 alphae=alphae, alphax=alphax,
                                 transmission=transmission,
                                 targetthickness=targetthickness,
                                 filterlist=filterlist)

    energy = numpy.ones(len(x1) + len(x2), dtype=float)
    energy[0:len(x1)] *= x1
    energy[len(x1):(len(x1)+len(x2))] *= x2
    energyweight = continuumEbel(target, e0, energy, window,
                                 alphae=alphae, alphax=alphax,
                                 transmission=transmission,
                                 targetthickness=targetthickness,
                                 filterlist=filterlist)
    energyweight[0:len(x1)] *= step1
    energyweight[len(x1):(len(x1) + len(x2))] *= step2
    energyweight[len(x1)] *= (energy[len(x1)] - energy[len(x1) - 1]) / step2
    finalenergy = numpy.zeros(len(fllines) + len(energyweight), numpy.float64)
    finalweight = numpy.zeros(len(fllines) + len(energyweight), numpy.float64)
    scatterflag = numpy.zeros(len(fllines) + len(energyweight))
    finalenergy[len(fllines):] = energy[0:]
    finalweight[len(fllines):] = energyweight[0:] / 1.0e7
    for i in range(len(fllines)):
        finalenergy[i] = fllines[i][0]
        finalweight[i] = fllines[i][1] / 1.0e7
        scatterflag[i] = 1
    return finalenergy, finalweight, scatterflag


def main(args):
    # Energy array
    e = numpy.arange(args.voltage * 10 + 1)[1:] / 10

    # Compute spectra
    _ = continuumEbel(
        args.target,
        args.voltage,
        e,
        [args.wele, Elements.Element[args.wele]['density'], args.wthickness],
        alphae=args.anglee,
        alphax=args.anglex,
        transmission=args.transmission,
        targetthickness=args.tthickness,
        filterlist=None
    )

    fllines = characteristicEbel(
        args.target,
        args.voltage,
        [args.wele, Elements.Element[args.wele]['density'], args.wthickness],
        alphae=args.anglee,
        alphax=args.anglex,
        transmission=args.transmission,
        targetthickness=args.tthickness,
        filterlist=None
    )

    # Print characteristic lines
    fsum = 0.0
    for l in fllines:
        print("%s %.4f %.3e" % (l[2], l[0], l[1]))
        fsum += l[1]

    energy, weight, scatter = generateLists(
        args.target,
        args.voltage,
        [args.wele, Elements.Element[args.wele]['density'], args.wthickness],
        alphae=args.anglee,
        alphax=args.anglex,
        transmission=args.transmission,
        targetthickness=args.tthickness,
        filterlist=None
    )

    # Write output file
    fname = "Tube_%s_%.1f_%s_%.5f_ae%.1f_ax%.1f.txt" % (
        args.target, args.voltage, args.wele, args.wthickness, args.anglee, args.anglex
    )

    with open(fname, "w") as f:
        f.write("energyweight= " + ", ".join(str(w) for w in weight) + "\n")
        f.write("energy= " + ", ".join(str(e) for e in energy) + "\n")
        f.write("energyflag= " + ", ".join("1" for _ in energy) + "\n")
        f.write("energyscatter= " + ", ".join(str(s) for s in scatter) + "\n")


def build_parser():
    parser = CliUtils.create_parser(description="Generate Tube Spectrum Files")

    parser.add_argument("--target", default="Ag", type=str, help="Target element")
    parser.add_argument("--voltage", default=40, type=float, help="Tube voltage (kV)")
    parser.add_argument("--wele", "--window", default="Be", type=str, help="Window element")
    parser.add_argument("--wthickness", default=0.0125, type=float, help="Window thickness (cm)")
    parser.add_argument("--anglee", "--alphae", default=70, type=float, help="Emission angle (deg)")
    parser.add_argument("--anglex", "--alphax", default=50, type=float, help="X-ray angle (deg)")
    parser.add_argument("--cfg", default=None, type=str, help="Config file")
    parser.add_argument("--deltae", default=None, type=float, help="Delta E (optional)")
    parser.add_argument("--transmission", default=None, type=int, help="Transmission factor")
    parser.add_argument("--tthickness", default=None, type=float, help="Target thickness")

    return parser


if __name__ == "__main__":
    exit_code = CliUtils.cli_main(main, build_parser())
    sys.exit(exit_code)
