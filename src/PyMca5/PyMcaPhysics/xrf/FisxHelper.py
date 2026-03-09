#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2025 European Synchrotron Radiation Facility
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
__author__ = "V.A. Sole"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import os
import logging
from fisx import DataDir
from fisx import Elements as FisxElements
from fisx import Material
from fisx import Detector
try:
    from fisx import Beam
except ImportError:
    # old fisx version
    Beam = None
from fisx import XRF
import time
import sys
import numpy
xcom = None

_logger = logging.getLogger(__name__)

try:
    from concurrent.futures import ThreadPoolExecutor
except Exception:
    _logger.info("Cannot import ThreadPoolExecutor")
    ThreadPoolExecutor = None

def getElementsInstance(dataDir=None, bindingEnergies=None, xcomFile=None):
    if dataDir is None:
        dataDir = DataDir.FISX_DATA_DIR
    try:
        from PyMca5.PyMcaDataDir import PYMCA_DATA_DIR as pymcaDataDir
        from PyMca5 import getDataFile
    except Exception:
        _logger.info("Using fisx shell constants and ratios")
        pymcaDataDir = None
    if bindingEnergies is None:
        if pymcaDataDir is None:
            bindingEnergies = os.path.join(dataDir, "BindingEnergies.dat")
        else:
            bindingEnergies = getDataFile("BindingEnergies.dat")
    if xcomFile is None:
        if pymcaDataDir is None:
            xcomFile = os.path.join(dataDir, "XCOM_CrossSections.dat")
        else:
            xcomFile = getDataFile("XCOM_CrossSections.dat")
    t0 = time.time()
    instance = FisxElements(dataDir, bindingEnergies, xcomFile)
    _logger.debug("Shell constants")

    # the files should be taken from PyMca to make sure the same data are used
    for key in ["K", "L", "M"]:
        fname = instance.getShellConstantsFile(key)
        if sys.version > '3.0':
            # we have to make sure we have got a string
            if hasattr(fname, "decode"):
                fname = fname.decode("latin-1")
        _logger.debug("Before %s", fname)
        if pymcaDataDir is not None:
            fname = getDataFile(key + "ShellConstants.dat")
        else:
            fname = os.path.join(os.path.dirname(fname),
                                 key + "ShellConstants.dat")
        instance.setShellConstantsFile(key, fname)
        _logger.debug("After %s", instance.getShellConstantsFile(key))
    _logger.debug("Radiative transitions")

    for key in ["K", "L", "M"]:
        fname = instance.getShellRadiativeTransitionsFile(key)
        if sys.version > '3.0':
            # we have to make sure we have got a string ...
            if hasattr(fname, "decode"):
                fname = fname.decode("latin-1")
        _logger.debug("Before %s", fname)
        if pymcaDataDir is not None:
            fname = getDataFile(key + "ShellRates.dat")
        else:
            fname = os.path.join(os.path.dirname(fname), key + "ShellRates.dat")
        instance.setShellRadiativeTransitionsFile(key, fname)
        _logger.debug("After %s ", instance.getShellRadiativeTransitionsFile(key))

    _logger.debug("Reading Elapsed = %s", time.time() - t0)
    return instance

def getMultilayerFluorescence(multilayerSample,
                              energyList,
                              layerList = None,
                              weightList=None,
                              flagList  = None,
                              fulloutput = None,
                              beamFilters = None,
                              elementsList = None,
                              attenuatorList  = None,
                              userattenuatorList = None,
                              alphaIn      = None,
                              alphaOut     = None,
                              cascade = None,
                              detector= None,
                              elementsFromMatrix=False,
                              secondary=None,
                              materials=None,
                              secondaryCalculationLimit=None,
                              cache=1):
    if secondary is None:
        secondary=0
    if secondaryCalculationLimit is None:
        secondaryCalculationLimit=0.0
    if cache:
        cache = 1
    else:
        cache = 0

    _logger.info("Library requested to use secondary = %s", secondary)
    _logger.info("Library requested to use secondary limit = %s", secondaryCalculationLimit)
    _logger.info("Library requested to use cache = %d", cache)

    global xcom
    if xcom is None:
        _logger.debug("Getting fisx elements instance")
        xcom = getElementsInstance()

    if materials is not None:
        _logger.debug("Deleting materials")
        xcom.removeMaterials()
        for material in materials:
            _logger.debug("Adding material making sure no duplicates")
            xcom.addMaterial(material, errorOnReplace=1)

    # the instance
    _logger.debug("creating XRF instance")
    xrf = XRF()

    # the beam energies
    if not len(energyList):
        raise ValueError("Empty list of beam energies!!!")
    _logger.debug("setting beam")
    xrf.setBeam(energyList, weights=weightList,
                            characteristic=flagList)
    # the beam filters (if any)
    if beamFilters is None:
        beamFilters = []
    """
    Due to wrapping constraints, the filter list must have the form:
    [[Material name or formula0, density0, thickness0, funny factor0],
     [Material name or formula1, density1, thickness1, funny factor1],
     ...
     [Material name or formulan, densityn, thicknessn, funny factorn]]

    Unless you know what you are doing, the funny factors must be 1.0
    """
    _logger.debug("setting beamFilters")
    xrf.setBeamFilters(beamFilters)

    # the sample description
    """
    Due to wrapping constraints, the list must have the form:
    [[Material name or formula0, density0, thickness0, funny factor0],
     [Material name or formula1, density1, thickness1, funny factor1],
     ...
     [Material name or formulan, densityn, thicknessn, funny factorn]]

    Unless you know what you are doing, the funny factors must be 1.0
    """
    _logger.debug("setting sample")
    xrf.setSample(multilayerSample)

    # the attenuators
    if attenuatorList is not None:
        if len(attenuatorList) > 0:
            _logger.debug("setting attenuators")
            xrf.setAttenuators(attenuatorList)

    # the user attenuators
    if userattenuatorList is not None:
        i = 0
        for userAttenuator in userattenuatorList:
            if isinstance(userAttenuator, tuple) or \
               isinstance(userAttenuator, list):
                energy = userAttenuator[0]
                transmission = userAttenuator[1]
                if len(userAttenuator) == 4:
                    name = userAttenuator[2]
                    comment = userAttenuator[3]
            else:
                if userattenuatorList[userAttenuator]["use"]:
                    energy = userattenuatorList[userAttenuator]["energy"]
                    transmission = userattenuatorList[userAttenuator]["transmission"]
                    name = userattenuatorList[userAttenuator].get("name",
                                                        "UserFilter%d" % i)
                    name = userattenuatorList[userAttenuator].get("comment","")
                else:
                    continue
            from fisx import TransmissionTable
            ttable = TransmissionTable()
            ttable.setTransmissionTableFromLists(energy,
                                                 transmission,
                                                 name,
                                                 comment)
            xrf.setTransmissionTable(ttable)

    # the geometry
    _logger.debug("setting Geometry")
    if alphaIn is None:
        alphaIn = 45
    if alphaOut is None:
        alphaOut = 45
    xrf.setGeometry(alphaIn, alphaOut)

    # the detector
    _logger.debug("setting Detector")
    if detector is not None:
        # Detector can be a list as [material, density, thickness]
        # or a Detector instance
        if isinstance(detector, Detector):
            detectorInstance = detector
        elif len(detector) == 3:
            detectorInstance = Detector(detector[0],
                                            density=detector[1],
                                            thickness=detector[2])
        else:
            detectorInstance = Detector(detector[0],
                                            density=detector[1],
                                            thickness=detector[2],
                                            funny=detector[3])
    else:
        detectorInstance = Detector("")

    xrf.setDetector(detectorInstance)
    if detectorInstance.getActiveArea() > 0.0:
        useGeometricEfficiency = 1
    else:
        useGeometricEfficiency = 0

    if elementsList in [None, []]:
        raise ValueError("Element list not specified")

    if len(elementsList):
        if len(elementsList[0]) == 3:
            # PyMca can send [atomic number, element, peak]
            actualElementsList = [x[1] + " " + x[2] for x in elementsList]
        elif len(elementsList[0]) == 2:
            actualElementsList = [x[0] + " " + x[1] for x in elementsList]
        else:
            actualElementsList = elementsList

    matrixElementsList = []
    for peak in actualElementsList:
        ele = peak.split()[0]
        considerIt = False
        for layer in multilayerSample:
            composition = xcom.getComposition(layer[0])
            if ele in composition:
                considerIt = True
        if considerIt:
            if peak not in matrixElementsList:
                matrixElementsList.append(peak)

    if elementsFromMatrix:
        elementsList = matrixElementsList

    t0 = time.time()
    if cache:
        # enabling the cascade cache gets a (miserable) 15 % speed up
        _logger.debug("FisxHelper Using cache")
    else:
        _logger.debug("FisxHelper Not using cache")

    treatedElements = []
    emittedLines = []
    for actualElement in actualElementsList:
        element = actualElement.split()[0]
        if element not in treatedElements:
            if cache:
                lines = xcom.getEmittedXRayLines(element)
                sampleEnergies = [lines[key] for key in lines]
                for e in sampleEnergies:
                    if e not in emittedLines:
                        emittedLines.append(e)
            treatedElements.append(element)

    for layer in multilayerSample:
        composition = xcom.getComposition(layer[0])
        for element in composition.keys():
            if element not in treatedElements:
                if cache:
                    lines = xcom.getEmittedXRayLines(element)
                    sampleEnergies = [lines[key] for key in lines]
                    for e in sampleEnergies:
                        if e not in emittedLines:
                            emittedLines.append(e)
                treatedElements.append(element)

    if attenuatorList is not None:
        for layer in attenuatorList:
            composition = xcom.getComposition(layer[0])
            for element in composition.keys():
                if element not in treatedElements:
                    if cache:
                        lines = xcom.getEmittedXRayLines(element)
                        sampleEnergies = [lines[key] for key in lines]
                        for e in sampleEnergies:
                            if e not in emittedLines:
                                emittedLines.append(e)
                    treatedElements.append(element)

    if hasattr(xcom, "updateCache"):
        composition = detectorInstance.getComposition(xcom)
        for element in composition.keys():
            if element not in treatedElements:
                if cache:
                    lines = xcom.getEmittedXRayLines(element)
                    sampleEnergies = [lines[key] for key in lines]
                    for e in sampleEnergies:
                        if e not in emittedLines:
                            emittedLines.append(e)
                treatedElements.append(element)

        for element in actualElementsList:
            if element.split()[0] not in treatedElements:
                treatedElements.append(element.split()[0])

        for element in treatedElements:
            # this limit seems overestimated but still reasonable
            if xcom.getCacheSize(element) > 5000:
                _logger.info("Clearing cache for %s" % element)
                xcom.clearCache(element)
            if cache:
                _logger.info("Updating cache for %s" % element)
                xcom.updateCache(element, energyList)
                xcom.updateCache(element, emittedLines)
            else:
                # should I clear the cache to be sure?
                # for the time being, yes.
                _logger.info("No cache. Clearing cache for %s" % element)
                xcom.clearCache(element)
            xcom.setCacheEnabled(element, cache)
            _logger.info("Element %s cache size = %d",
                          element, xcom.getCacheSize(element))
        for element in actualElementsList:
            xcom.setElementCascadeCacheEnabled(element.split()[0], cache)

    if hasattr(xcom, "updateEscapeCache") and \
       hasattr(xcom, "setEscapeCacheEnabled"):
        if detector is not None:
            for element in actualElementsList:
                if cache:
                    lines = xcom.getEmittedXRayLines(element.split()[0])
                    lines_energy = [lines[key] for key in lines]
                    for e in lines_energy:
                        if e not in emittedLines:
                            emittedLines.append(e)
            if not cache:
                if hasattr(xcom, "clearEscapeCache"):
                    # the method is there but nor wrapped yet
                    xcom.clearEscapeCache()
            xcom.setEscapeCacheEnabled(cache)
            if cache:
                xcom.updateEscapeCache(detectorInstance.getComposition(xcom),
                            emittedLines,
                            energyThreshold=detectorInstance.getEscapePeakEnergyThreshold(), \
                            intensityThreshold=detectorInstance.getEscapePeakIntensityThreshold(), \
                            nThreshold=detectorInstance.getEscapePeakNThreshold(), \
                            alphaIn=detectorInstance.getEscapePeakAlphaIn(),
                            thickness=0)  # No escape by the back considered yet
    else:
        _logger.debug("NOT CALLING UPDATE CACHE")
    _logger.info("C++ elapsed filling cache = %s",
                  time.time() - t0)
        
    _logger.debug("Calling getMultilayerFluorescence")

    nSampleLayers = len(multilayerSample)
    nEnergies = len(energyList)
    #secondary = 2
    #print(" SECONDARY = ", secondary)
    if Beam and ThreadPoolExecutor and secondary and (nEnergies > 4 or nSampleLayers > 1):
        if (secondary <= 1) and (nSampleLayers > nEnergies):
            # one thread per layer
            # Sample layer parallelization
            _logger.info("Threading by layers")
            t0 = time.time()
            pool = ThreadPoolExecutor(max_workers=min(os.cpu_count(), nSampleLayers))
            ele = [x.split()[0] for x in actualElementsList]
            family = [x.split()[1] for x in actualElementsList]
            future = [None] * nSampleLayers
            for i in range(nSampleLayers):
                future[i] = pool.submit(xrf.getFluorescence,
                                        ele, xcom, i, family,
                                        secondary=secondary,
                                        useGeometricEfficiency=useGeometricEfficiency,
                                        useMassFractions=elementsFromMatrix,
                                        secondaryCalculationLimit=secondaryCalculationLimit)
            fluorescence = {}
            for i in range(len(future)):
                partialFluorescence = future[i].result()
                for peakFamily in partialFluorescence:
                    if peakFamily not in fluorescence:
                        fluorescence[peakFamily] = partialFluorescence[peakFamily]
                        continue
                    for layer in partialFluorescence[peakFamily]:
                        if layer not in fluorescence[peakFamily]:
                            fluorescence[peakFamily][layer] = partialFluorescence[peakFamily][layer]
                            continue
                        for transition in partialFluorescence[peakFamily][layer]:
                                msg = "This point should not be reached with layer parallerisation"
                                _logger.critical(msg)
                                if transition not in fluorescence[peakFamily][layer]:
                                    fluorescence[peakFamily][layer][transition] = \
                                                    partialFluorescence[peakFamily][layer][transition]
                                    continue
                                for key in partialFluorescence[peakFamily][layer][transition]:
                                    if key not in fluorescence[peakFamily][layer][transition]:
                                        fluorescence[peakFamily][layer][transition][key] = \
                                                    partialFluorescence[peakFamily][layer][transition][key]
                                    continue
        elif (secondary <= 1) and (len(energyList) < 2) and len(actualElementsList) > 4:
            # elements parallelization cannot work with tertiary excitation
            # the speed up does not seem to be huge
            _logger.info("Threading by elements")
            t0 = time.time()
            max_workers = min(os.cpu_count(), int(len(actualElementsList)/2))
            pool = ThreadPoolExecutor(max_workers=max_workers)
            ele = [x.split()[0] for x in actualElementsList]
            family = [x.split()[1] for x in actualElementsList]
            partialActualElementsList = [None] * max_workers
            future = [None] * max_workers
            for i in range(max_workers):
                partialActualElementsList = actualElementsList[i::max_workers]
                future[i] = pool.submit(xrf.getMultilayerFluorescence,
                                        partialActualElementsList,
                                        xcom,
                                        secondary=secondary,
                                        useGeometricEfficiency=useGeometricEfficiency,
                                        useMassFractions=elementsFromMatrix,
                                        secondaryCalculationLimit=secondaryCalculationLimit)
            fluorescence = {}
            for i in range(len(future)):
                partialFluorescence = future[i].result()
                for peakFamily in partialFluorescence:
                    if peakFamily not in fluorescence:
                        fluorescence[peakFamily] = partialFluorescence[peakFamily]
                        continue
                    msg = "This point should not be reached with element parallerisation"
                    _logger.critical(msg)
        else:
            # multiple energies parallelization
            _logger.info("Threading by energies")
            t0 = time.time()
            max_workers = min(os.cpu_count(), int(len(energyList)/2))
            _logger.info("Number of workers = %d" % max_workers)
            pool = ThreadPoolExecutor(max_workers=max_workers)
            ele = [x.split()[0] for x in actualElementsList]
            family = [x.split()[1] for x in actualElementsList]
            beamList = [None] * max_workers
            future = [None] * max_workers
            # the beam is automatically normalized
            totalBeamWeight = numpy.sum(weightList, dtype=numpy.float64)
            beamWeight = [None] * max_workers
            for i in range(max_workers):
                beamList[i] = Beam()            
                beamList[i].setBeam(energyList[i::max_workers],
                                weightList[i::max_workers])
                beamWeight[i] = numpy.sum(weightList[i::max_workers], dtype=numpy.float64)
                future[i] = pool.submit(xrf.getMultilayerFluorescence,
                                        actualElementsList,
                                        xcom,
                                        secondary=secondary,
                                        useGeometricEfficiency=useGeometricEfficiency,
                                        useMassFractions=elementsFromMatrix,
                                        secondaryCalculationLimit=secondaryCalculationLimit,
                                        overwritingBeam=beamList[i])
            fluorescence = {}
            for i in range(len(future)):
                partialFluorescence = future[i].result()
                for peakFamily in partialFluorescence:
                    if peakFamily not in fluorescence:
                        fluorescence[peakFamily] = {}
                    for layer in partialFluorescence[peakFamily]:
                        if layer not in fluorescence[peakFamily]:
                            fluorescence[peakFamily][layer] = {}
                        for transition in partialFluorescence[peakFamily][layer]:
                                if transition not in fluorescence[peakFamily][layer]:
                                    fluorescence[peakFamily][layer][transition] = {}
                                for key in partialFluorescence[peakFamily][layer][transition]:
                                    if key not in fluorescence[peakFamily][layer][transition]:
                                        fluorescence[peakFamily][layer][transition][key] = 0.0
                                    fluorescence[peakFamily][layer][transition][key] += \
                                            partialFluorescence[peakFamily][layer][transition][key]* \
                                            beamWeight[i] / totalBeamWeight
        expectedFluorescence = fluorescence
        print("THREADING ELAPSED = %s", time.time() - t0)
    else:
        # No possibility to use threads or no need
        _logger.info("No Threading")
        t0 = time.time()
        expectedFluorescence = xrf.getMultilayerFluorescence(actualElementsList,
                            xcom,
                            secondary=secondary,
                            useGeometricEfficiency=useGeometricEfficiency,
                            useMassFractions=elementsFromMatrix,
                            secondaryCalculationLimit=secondaryCalculationLimit)
        if 0:
            # This whould be equivalent
            overwritingBeam = Beam()
            overwritingBeam.setBeam(energyList, weights=weightList)
            expectedFluorescence = xrf.getMultilayerFluorescence(actualElementsList,
                                    xcom,
                                    secondary=secondary,
                                    useGeometricEfficiency=useGeometricEfficiency,
                                    useMassFractions=elementsFromMatrix,
                                    secondaryCalculationLimit=secondaryCalculationLimit,
                                    overwritingBeam=overwritingBeam)
        print("C++ elapsed TWO = %s", time.time() - t0)
    # check if the two dictionnaries are idential
    # print("Are they equal ? = ", _compareResults(fluorescence, expectedFluorescence))
    # expectedFluorescence = fluorescence

    if not elementsFromMatrix:
        # If one element was present in one layer and not on others, PyMca only
        # calculated contributions from the layers in which the element was
        # present
        for peakFamily in matrixElementsList:
            element, family = peakFamily.split()[0:2]
            key = element + " " + family
            if key in expectedFluorescence:
                # those layers where the amount of the material was 0 have
                # to present no contribution
                for iLayer in range(len(expectedFluorescence[key])):
                    layerMaterial = multilayerSample[iLayer][0]
                    if element not in xcom.getComposition(layerMaterial):
                        expectedFluorescence[key][iLayer] = {}
    return expectedFluorescence

def _compareResults(fluorescence, expectedFluorescence, atol=1.0e-6, rtol=1.0e-4):
    """
    Returns 0 if not equal, 1 if equal within tolerance, 2 if identical 
    """
    if fluorescence == expectedFluorescence:
        return 2
    for peakFamily in expectedFluorescence:
        for layer in expectedFluorescence[peakFamily]:
            for transition in expectedFluorescence[peakFamily][layer]:
                for key in expectedFluorescence[peakFamily][layer][transition]:
                    if expectedFluorescence[peakFamily][layer][transition][key] != \
                           fluorescence[peakFamily][layer][transition][key]:
                        tmpDouble = expectedFluorescence[peakFamily][layer][transition][key] \
                                    - fluorescence[peakFamily][layer][transition][key]
                        relative = tmpDouble/max(fluorescence[peakFamily][layer][transition][key],
                                                  expectedFluorescence[peakFamily][layer][transition][key])
                        if abs(tmpDouble) > atol or (relative > rtol):
                            print("Offending key = %s" % key)
                            print("delta = %f" % tmpDouble)
                            print("relative = %f" % relative)
                            print(expectedFluorescence[peakFamily][layer][transition][key])
                            print(fluorescence[peakFamily][layer][transition][key])
                            return 0
    return 1

def _getFisxMaterials(fitConfiguration):
    """
    Given a PyMca fir configuration, return the list of fisx materials to be
    used by the library for calculation purposes.
    """
    global xcom
    if xcom is None:
        xcom = getElementsInstance()

    # define all the needed materials
    inputMaterialDict = fitConfiguration.get("materials", {})
    inputMaterialList = list(inputMaterialDict.keys())
    nMaterials = len(inputMaterialList)
    fisxMaterials = []
    processedMaterialList = []
    nIter = 10000
    while (len(processedMaterialList) != nMaterials) and (nIter > 0):
        nIter -= 1
        for i in range(nMaterials):
            materialName = inputMaterialList[i]
            if materialName in processedMaterialList:
                # already defined
                pass
            else:
                thickness = inputMaterialDict[materialName].get("Thickness", 1.0)
                if thickness <= 0:
                    raise ValueError("Invalid thickness %f" % thickness)
                density = inputMaterialDict[materialName].get("Density", 1.0)
                if density == 0.0:
                    raise ValueError("Invalid density %f" % density)
                comment = inputMaterialDict[materialName].get("Comment", "")
                if type(comment) in [type([])]:
                    # the user may have put a comma in the comment leading to
                    # misinterpretation of the string as a list
                    if len(comment) == 0:
                        comment = ""
                    elif len(comment) == 1:
                        comment = comment[0]
                    else:
                        actualComment = comment[0]
                        for commentPiece in comment[1:]:
                            actualComment = actualComment + "," + commentPiece
                        comment = actualComment
                if not len(comment):
                    comment = ""
                compoundList = inputMaterialDict[materialName]["CompoundList"]
                fractionList = inputMaterialDict[materialName]["CompoundFraction"]
                if not hasattr(fractionList, "__getitem__"):
                    compoundList = [compoundList]
                    fractionList = [fractionList]
                composition = {}
                for n in range(len(compoundList)):
                    if fractionList[n] > 0.0:
                        composition[compoundList[n]] = fractionList[n]
                    else:
                        _logger.info("ignoring %s, fraction = %s",
                                     compoundList[n], fractionList[n])
                # check the composition is expressed in terms of elements
                # and not in terms of other undefined materials
                totallyDefined = True
                for element in composition:
                    #check if it can be understood
                    if element in processedMaterialList:
                        # already defined
                        continue
                    elif not len(xcom.getComposition(element)):
                        # compound not understood
                        # probably we have a material defined in terms of other material
                        totallyDefined = False
                if totallyDefined:
                    try:
                        fisxMaterial = Material(materialName,
                                              density=density,
                                              thickness=thickness,
                                              comment=comment)
                        fisxMaterial.setComposition(composition)
                        fisxMaterials.append(fisxMaterial)
                    except Exception:
                        if len(materialName):
                            raise TypeError("Error defining material <%s>" % \
                                            materialName)
                    processedMaterialList.append(materialName)
    if len(processedMaterialList) < nMaterials:
        txt = "Undefined materials. "
        for material in inputMaterialList:
            if material not in processedMaterialList:
                txt += "\nCannot define material <%s>\nComposition " % material
                compoundList = inputMaterialDict[material]["CompoundList"]
                fractionList = inputMaterialDict[material]["CompoundFraction"]
                for compound in compoundList:
                    if not len(xcom.getComposition(compound)):
                        if compound not in processedMaterialList:
                            if compound + " " in processedMaterialList:
                                txt += "contains <%s> (defined as <%s>), " % (compound, compound + " ")
                            else:
                                txt += "contains <%s> (undefined)," % compound
        _logger.info(txt)
        raise KeyError(txt)
    return fisxMaterials

def _getBeam(fitConfiguration):
    inputEnergy = fitConfiguration['fit'].get('energy', None)
    if inputEnergy in [None, ""]:
        raise ValueError("Beam energy has to be specified")
    if not hasattr(inputEnergy, "__len__"):
        energyList = [inputEnergy]
        weightList = [1.0]
        characteristicList = [1]
    else:
        energyList    = []
        weightList  = []
        characteristicList = []
        for i in range(len(inputEnergy)):
            if fitConfiguration['fit']['energyflag'][i]:
                energy = fitConfiguration['fit']['energy'][i]
                if energy is not None:
                    if fitConfiguration['fit']['energyflag'][i]:
                        weight = fitConfiguration['fit']['energyweight'][i]
                        if weight > 0.0:
                            energyList.append(energy)
                            weightList.append(weight)
                    if 'energyscatter' in fitConfiguration['fit']:
                        characteristicList.append(fitConfiguration['fit'] \
                                              ['energyscatter'][i])
                    elif i == 0:
                        characteristicList.append(1)
                    else:
                        characteristicList.append(0)
    return energyList, weightList, characteristicList

def _getUserAttenuators(fitConfiguration):
    return _getUserattenuators(fitConfiguration)

def _getUserattenuators(fitConfiguration):
    userattenuatorList =[]
    userattenuators = fitConfiguration.get('userattenuators', {})
    for userattenuator in userattenuators.keys():
        ddict = userattenuators[userattenuator]
        if ddict["use"]:
            userattenuatorList.append([ddict["energy"],
                                       ddict["transmission"],
                                       ddict["name"],
                                       ddict["comment"]])
    return userattenuatorList

def _getFiltersMatrixAttenuatorsDetectorGeometry(fitConfiguration):
    useMatrix = False
    attenuatorList =[]
    filterList = []
    detector = None
    for attenuator in list(fitConfiguration['attenuators'].keys()):
        if not fitConfiguration['attenuators'][attenuator][0]:
            # set to be ignored
            continue
        #if len(fitConfiguration['attenuators'][attenuator]) == 4:
        #    fitConfiguration['attenuators'][attenuator].append(1.0)
        if attenuator.upper() == "MATRIX":
            if fitConfiguration['attenuators'][attenuator][0]:
                useMatrix = True
                matrix = fitConfiguration['attenuators'][attenuator][1:4]
                alphaIn= fitConfiguration['attenuators'][attenuator][4]
                alphaOut= fitConfiguration['attenuators'][attenuator][5]
            else:
                useMatrix = False
        elif attenuator.upper() == "DETECTOR":
            detector = fitConfiguration['attenuators'][attenuator][1:5]
        elif attenuator.upper().startswith("BEAMFILTER"):
            filterList.append(fitConfiguration['attenuators'][attenuator][1:5])
        else:
            attenuatorList.append(fitConfiguration['attenuators'][attenuator][1:5])
    if not useMatrix:
        raise ValueError("Sample matrix has to be specified!")

    if matrix[0].upper() == "MULTILAYER":
        multilayerSample = []
        layerKeys = list(fitConfiguration['multilayer'].keys())
        if len(layerKeys):
            layerKeys.sort()
        for layer in layerKeys:
            if fitConfiguration['multilayer'][layer][0]:
                multilayerSample.append(fitConfiguration['multilayer'][layer][1:])
    else:
        multilayerSample = [matrix]
    return filterList, multilayerSample, attenuatorList, detector, \
           alphaIn, alphaOut

def _getPeakList(fitConfiguration):
    elementsList = []
    for element in fitConfiguration['peaks'].keys():
        if len(element) > 1:
            ele = element[0:1].upper() + element[1:2].lower()
        else:
            ele = element.upper()
        if type(fitConfiguration['peaks'][element]) == type([]):
            for peak in fitConfiguration['peaks'][element]:
                elementsList.append(ele + " " + peak)
        else:
            for peak in [fitConfiguration['peaks'][element]]:
                elementsList.append(ele + " " + peak)
    elementsList.sort()
    return elementsList

def _getFisxDetector(fitConfiguration, attenuatorsDetector=None):
    distance = fitConfiguration["concentrations"]["distance"]
    area = fitConfiguration["concentrations"]["area"]
    detectorMaterial = fitConfiguration["detector"]["detele"]

    if attenuatorsDetector is None:
        # user is not interested on accounting for detection efficiency
        if fitConfiguration["fit"]["escapeflag"]:
            # but wants to account for escape peaks
            # we can forget about efficiency but not about detector composition
            # assign "infinite" efficiency
            density = 0.0
            thickness = 0.0
            fisxDetector = Detector(detectorMaterial,
                                    density=density,
                                    thickness=thickness)
        else:
            # user is not interested on considering the escape peaks
            fisxDetector = None
    else:
        # make sure information is consistent
        if attenuatorsDetector[0] not in [detectorMaterial, detectorMaterial+"1"]:
            _logger.warning("%s not equal to %s",
                            attenuatorsDetector[0], detectorMaterial)
            msg = "Inconsistent detector material between DETECTOR and ATTENUATORS tab"
            msg += "\n%s not equal to %s" % (attenuatorsDetector[0], detectorMaterial)
            raise ValueError(msg)
        if len(attenuatorsDetector) == 3:
            fisxDetector = Detector(detectorMaterial,
                                density=attenuatorsDetector[1],
                                thickness=attenuatorsDetector[2])
        else:
            fisxDetector = Detector(detectorMaterial,
                                density=attenuatorsDetector[1],
                                thickness=attenuatorsDetector[2],
                                funny=attenuatorsDetector[3])
        fisxDetector.setActiveArea(area)
        fisxDetector.setDistance(distance)
    if fisxDetector is not None:
        nThreshold = fitConfiguration["detector"]["nthreshold"]
        fisxDetector.setMaximumNumberOfEscapePeaks(nThreshold)
    return fisxDetector

def  _getSecondaryCalculationLimitFromFitConfiguration(fitConfiguration):
    try:
        limit = float(\
            fitConfiguration["concentrations"]["secondarycalculationlimit"])
    except Exception:
        _logger.debug("Exception. Forcing no limit")
        limit = 0.0
    return limit

def getMultilayerFluorescenceFromFitConfiguration(fitConfiguration,
                                                  elementsFromMatrix=False,
                                                  secondaryCalculationLimit=None):
    return _fisxFromFitConfigurationAction(fitConfiguration,
                                        action="fluorescence",
                                        elementsFromMatrix=elementsFromMatrix,
                                        secondaryCalculationLimit= \
                                           secondaryCalculationLimit)

def getFisxCorrectionFactorsFromFitConfiguration(fitConfiguration,
                                                 elementsFromMatrix=False,
                                                 secondaryCalculationLimit=None):
    return _fisxFromFitConfigurationAction(fitConfiguration,
                                        action="correction",
                                        elementsFromMatrix=elementsFromMatrix,
                                        secondaryCalculationLimit= \
                                           secondaryCalculationLimit)

def _fisxFromFitConfigurationAction(fitConfiguration,
                                    action=None,
                                    elementsFromMatrix=False, \
                                    secondaryCalculationLimit=None):
    if action is None:
        raise ValueError("Please specify action")
    if secondaryCalculationLimit is None:
        secondaryCalculationLimit = \
            _getSecondaryCalculationLimitFromFitConfiguration(fitConfiguration)
    # This is highly inefficient because one has to perform all the parsing
    # that has been already made when configuring the fit. However, this is
    # currently the simplest implementation that can work as standalone given
    # the fit configuration

    # the fisx materials list
    fisxMaterials = _getFisxMaterials(fitConfiguration)

    # extract beam parameters
    energyList, weightList, characteristicList = _getBeam(fitConfiguration)

    # extract beamFilters, matrix, geometry, attenuators and detector
    filterList, multilayerSample, attenuatorList, detector, alphaIn, alphaOut \
                = _getFiltersMatrixAttenuatorsDetectorGeometry(fitConfiguration)

    # extract transmission tables used as atenuators
    userattenuatorList = _getUserattenuators(fitConfiguration)

    # The elements and families to be considered
    elementsList = _getPeakList(fitConfiguration)

    # The detection setup
    detectorInstance = _getFisxDetector(fitConfiguration, detector)

    try:
        secondary = fitConfiguration["concentrations"]["usemultilayersecondary"]
    except Exception:
        _logger.warning("Exception. Forcing tertiary")
        secondary = 2

    if action.upper() == "FLUORESCENCE":
        return getMultilayerFluorescence(multilayerSample,
                                      energyList,
                                      weightList = weightList,
                                      flagList = characteristicList,
                                      fulloutput = None,
                                      beamFilters = filterList,
                                      elementsList = elementsList,
                                      attenuatorList = attenuatorList,
                                      userattenuatorList = userattenuatorList,
                                      alphaIn = alphaIn,
                                      alphaOut = alphaOut,
                                      cascade = None,
                                      detector = detectorInstance,
                                      elementsFromMatrix=elementsFromMatrix,
                                      secondary=secondary,
                                      materials=fisxMaterials,
                                      secondaryCalculationLimit= \
                                          secondaryCalculationLimit)
    else:
        if secondary == 0:
            # otherways it is meaning less to call the function
            secondary = 2            
        return getFisxCorrectionFactors(multilayerSample,
                                      energyList,
                                      weightList = weightList,
                                      flagList = characteristicList,
                                      fulloutput = None,
                                      beamFilters = filterList,
                                      elementsList = elementsList,
                                      attenuatorList = attenuatorList,
                                      userattenuatorList = userattenuatorList,
                                      alphaIn = alphaIn,
                                      alphaOut = alphaOut,
                                      cascade = None,
                                      detector = detectorInstance,
                                      elementsFromMatrix=elementsFromMatrix,
                                      secondary=secondary,
                                      materials=fisxMaterials,
                                      secondaryCalculationLimit= \
                                          secondaryCalculationLimit)

def getFisxCorrectionFactors(*var, **kw):
    expectedFluorescence = getMultilayerFluorescence(*var, **kw)
    ddict = {}
    transitions = ['K', 'Ka', 'Kb', 'L', 'L1', 'L2', 'L3', 'M', 'M1', 'M2', 'M3', 'M4', 'M5']
    if kw["secondary"] == 2:
        nItems = 3
    else:
        nItems = 2
    for key in expectedFluorescence:
        element, family = key.split()
        if element not in ddict:
            ddict[element] = {}
        if family not in transitions:
            raise KeyError("Invalid transition family: %s" % family)
        if family not in ddict[element]:
            ddict[element][family] = {'total':0.0,
                                      'correction_factor':[1.0] * nItems,
                                      'counts':[0.0] * nItems}
        for iLayer in range(len(expectedFluorescence[key])):
            layerOutput = expectedFluorescence[key][iLayer]
            layerKey = "layer %d" % iLayer
            if layerKey not in ddict[element][family]:
                ddict[element][family][layerKey] = {'total':0.0,
                                    'correction_factor':[1.0] * nItems,
                                    'counts':[0.0] * nItems}
            for line in layerOutput:
                rate = layerOutput[line]["rate"]
                primary = layerOutput[line]["primary"]
                secondary = layerOutput[line]["secondary"]
                tertiary = layerOutput[line].get("tertiary", 0.0)
                if rate <= 0.0:
                    continue
                # primary counts
                tmpDouble = rate * (primary / (primary + secondary + tertiary))
                ddict[element][family]["counts"][0] += tmpDouble
                secondaryCounts = rate * \
                    ((primary  + secondary)/ (primary + secondary + tertiary))
                ddict[element][family]["counts"][1] += secondaryCounts
                if nItems == 3:
                    ddict[element][family]["counts"][2] += rate
                ddict[element][family]["total"] += rate

                #layer by layer information
                ddict[element][family][layerKey]["counts"][0] += tmpDouble
                ddict[element][family][layerKey]["counts"][1] += secondaryCounts
                if nItems == 3:
                    ddict[element][family][layerKey]["counts"][2] += rate
                ddict[element][family][layerKey]["total"] += rate

    for element in ddict:
        for family in ddict[element]:
            # second order includes tertiary!!!
            firstOrder = ddict[element][family]["counts"][0]
            secondOrder = ddict[element][family]["counts"][1]
            ddict[element][family]["correction_factor"][1] = \
                       secondOrder / firstOrder
            if nItems == 3:
                thirdOrder = ddict[element][family]["counts"][2]
                ddict[element][family]["correction_factor"][2] = \
                                   thirdOrder / firstOrder
            i = 0
            layerKey = "layer %d" % i
            while layerKey in ddict[element][family]:
                firstOrder = ddict[element][family][layerKey]["counts"][0]
                secondOrder = ddict[element][family][layerKey]["counts"][1]
                if firstOrder <= 0:
                    if secondOrder > 0.0:
                        _logger.warning("Inconsistency? secondary with no primary?")
                    ddict[element][family][layerKey]["correction_factor"][1] = 1
                    if nItems == 3:
                        ddict[element][family][layerKey]["correction_factor"][2] = 1
                else:
                    ddict[element][family][layerKey]["correction_factor"][1] =\
                       secondOrder / firstOrder
                    if nItems == 3:
                        ddict[element][family][layerKey]["correction_factor"][2] =\
                           thirdOrder / firstOrder
                i += 1
                layerKey = "layer %d" % i
    return ddict

def getFisxCorrectionFactorsFromFitConfigurationFile(fileName,
                                                     elementsFromMatrix=False,
                                                secondaryCalculationLimit=None):
    from PyMca5.PyMca import ConfigDict
    d = ConfigDict.ConfigDict()
    d.read(fileName)
    return getFisxCorrectionFactorsFromFitConfiguration(d,
                                        elementsFromMatrix=elementsFromMatrix,
                                        secondaryCalculationLimit= \
                                            secondaryCalculationLimit)

if __name__ == "__main__":
    _logger.setLevel(logging.DEBUG)
    if len(sys.argv) < 2:
        print("Usage: python FisxHelper FitConfigurationFile [element] [matrix_flag]")
        sys.exit(0)
    fileName = sys.argv[1]
    if len(sys.argv) > 2:
        element = sys.argv[2]
        if len(sys.argv) > 3:
            matrix = int(sys.argv[3])    
            print(getFisxCorrectionFactorsFromFitConfigurationFile(\
                fileName, elementsFromMatrix=matrix))[element]
        else:
            print(getFisxCorrectionFactorsFromFitConfigurationFile(fileName)) \
                                                                    [element]
    else:
        print(getFisxCorrectionFactorsFromFitConfigurationFile(fileName))

