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
__author__ = "V.A. Sole & A. Mirone - ESRF"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import os
import time
import logging
import numpy
import numpy.linalg
try:
    import numpy.core._dotblas as dotblas
except ImportError:
    # _dotblas was removed in numpy 1.10
    #print("WARNING: Not using BLAS, PCA calculation will be slower")
    dotblas = numpy

try:
    import mdp
    MDP = True
except Exception:
    # MDP can raise other errors than just an import error
    MDP = False

from . import Lanczos
from . import PCATools


_logger = logging.getLogger(__name__)


# Make these functions accept arguments not relevant to
# them in order to simplify having a common graphical interface
def lanczosPCA(stack, ncomponents=10, binning=None, legacy=True, **kw):
    _logger.debug("lanczosPCA")
    if binning is None:
        binning = 1

    if hasattr(stack, "info") and hasattr(stack, "data"):
        data = stack.data
    else:
        data = stack

    if not isinstance(data, numpy.ndarray):
        raise TypeError(\
            "lanczosPCA is only supported when using numpy arrays")

    #wrapmatrix = "double"
    wrapmatrix = "single"

    dtype = numpy.float64
    if wrapmatrix == "double":
        data = data.astype(dtype)

    if len(data.shape) == 3:
        r, c, N = data.shape
        data = data.reshape(r * c, N)
    else:
        r, N = data.shape
        c = 1

    npixels = r * c

    if binning > 1:
        # data.shape may fails with non-contiguous arrays
        # use reshape.
        data = numpy.reshape(data,
                             [data.shape[0], data.shape[1] / binning, binning])
        data = numpy.sum(data, axis=-1)
        N /= binning

    if ncomponents > N:
        raise ValueError("Number of components too high.")

    avg = numpy.sum(data, 0) / (1.0 * npixels)
    numpy.subtract(data, avg, data)

    Lanczos.LanczosNumericMatrix.tipo = dtype
    Lanczos.LanczosNumericVector.tipo = dtype

    if wrapmatrix == "single":
        SM = [dotblas.dot(data.T, data).astype(dtype)]
        SM = Lanczos.LanczosNumericMatrix(SM)
    else:
        SM = Lanczos.LanczosNumericMatrix([data.T.astype(dtype),
                                           data.astype(dtype)])

    eigenvalues, eigenvectors = Lanczos.solveEigenSystem(SM,
                                                         ncomponents,
                                                         shift=0.0,
                                                         tol=1.0e-15)
    SM = None
    numpy.add(data, avg, data)

    images = numpy.zeros((ncomponents, npixels), data.dtype)
    vectors = numpy.zeros((ncomponents, N), dtype)
    for i in range(ncomponents):
        vectors[i, :] = eigenvectors[i].vr
        images[i, :] = dotblas.dot(data,
                                   (eigenvectors[i].vr).astype(data.dtype))
    data = None
    images = images.reshape(ncomponents, r, c)
    if legacy:
        return images, eigenvalues, vectors
    else:
        return {"scores": images,
                "eigenvalues": eigenvalues,
                "eigenvectors": vectors,
                "average": avg,
                "pixels": npixels,
                #"variance": ???????,
                }


def lanczosPCA2(stack, ncomponents=10, binning=None, legacy=True, **kw):
    """
    This is a fast method, but it may loose information
    """
    if hasattr(stack, "info") and hasattr(stack, "data"):
        data = stack.data
    else:
        data = stack

    # check we have received a numpy.ndarray and not an HDF5 group
    # or other type of dynamically loaded data
    if not isinstance(data, numpy.ndarray):
        raise TypeError(\
            "lanczosPCA2 is only supported when using numpy arrays")
    r, c, N = data.shape

    npixels = r * c  # number of pixels
    data = data.reshape(r * c, N)

    if npixels < 2000:
        BINNING = 2
    if npixels < 5000:
        BINNING = 4
    elif npixels < 10000:
        BINNING = 8
    elif npixels < 20000:
        BINNING = 10
    elif npixels < 30000:
        BINNING = 15
    elif npixels < 60000:
        BINNING = 20
    else:
        BINNING = 30
    if BINNING is not None:
        dataorig = data
        reminder = npixels % BINNING
        if reminder:
            data = data[0:BINNING * int(npixels / BINNING), :]
        data = data.reshape(int(data.shape[0] / BINNING), BINNING, data.shape[1])
        data = numpy.swapaxes(data, 1, 2)
        data = numpy.sum(data, axis=-1)
        rc = int(r * c / BINNING)

    tipo = numpy.float64
    neig = ncomponents + 5

    # it does not create the covariance matrix but performs two multiplications
    rappmatrix = "doppia"
    # it creates the covariance matrix but performs only one multiplication
    rappmatrix = "singola"

    # calcola la media
    ndata = len(data)
    mediadata = numpy.sum(data, axis=0) / numpy.array([ndata], data.dtype)

    numpy.subtract(data, mediadata, data)

    Lanczos.LanczosNumericMatrix.tipo = tipo
    Lanczos.LanczosNumericVector.tipo = tipo

    if rappmatrix == "singola":
        SM = [dotblas.dot(data.T, data).astype(tipo)]
        SM = Lanczos.LanczosNumericMatrix(SM)
    else:
        SM = Lanczos.LanczosNumericMatrix([data.T.astype(tipo),
                                           data.astype(tipo)])

    # calculate eigenvalues and eigenvectors
    ev, eve = Lanczos.solveEigenSystem(SM, neig, shift=0.0, tol=1.0e-7)
    SM = None
    rc = rc * BINNING

    newmat = numpy.zeros((r * c, neig), numpy.float64)

    data = data.astype(tipo)

    # numpy in-place addition to make sure not intermediate copies are made
    numpy.add(data, mediadata, data)

    for i in range(neig):
        newmat[:, i] = dotblas.dot(dataorig,
                                   (eve[i].vr).astype(dataorig.dtype))

    newcov = dotblas.dot(newmat.T, newmat)
    evals, evects = numpy.linalg.eigh(newcov)

    nuovispettri = dotblas.dot(evects, eve.vr[:neig])
    images = numpy.zeros((ncomponents, npixels), data.dtype)
    vectors = numpy.zeros((ncomponents, N), tipo)
    for i in range(ncomponents):
        vectors[i, :] = nuovispettri[-1 - i, :]
        images[i, :] = dotblas.dot(newmat,
                                   evects[-1 - i].astype(dataorig.dtype))
    images = images.reshape(ncomponents, r, c)
    return images, evals, vectors
    if legacy:
        return images, eigenvalues, vectors
    else:
        return {"scores": images,
                "eigenvalues": eigenvalues,
                "eigenvectors": vectors,
                "average": mediadata,
                "pixels": ndata,
                #"variance": ???????,
                }

def multipleArrayCovariancePCA(stackList0, **kw):
    return multipleArrayPCA(stackList0, scale=False, **kw)

def multipleArrayCorrelationPCA(stackList0, **kw):
    return multipleArrayPCA(stackList0, scale=True, **kw)

def multipleArrayPCA(stackList0, ncomponents=10, binning=None, legacy=True, scale=False, **kw):
    """
    Given a list of arrays, calculate the requested principal components from
    the matrix resulting from their column concatenation. Therefore, all the
    input arrays must have the same number of rows.
    """
    stackList = [None] * len(stackList0)
    i = 0
    for stack in stackList0:
        if hasattr(stack, "info") and hasattr(stack, "data"):
            data = stack.data
        else:
            data = stack
        stackList[i] = data
        i += 1

    stack = stackList[0]
    if hasattr(stack, "info") and hasattr(stack, "data"):
        data = stack.data
    else:
        data = stack

    if not isinstance(data, numpy.ndarray):
        raise TypeError(\
            "multipleArrayPCA is only supported when using numpy arrays")

    if len(data.shape) == 3:
        r, c = data.shape[:2]
        npixels = r * c
    else:
        c = None
        r = data.shape[0]
        npixels = r

    #reshape and subtract mean to all the input data
    shapeList = []
    avgList = []
    eigenvectorLength = 0
    for i in range(len(stackList)):
        shape = stackList[i].shape
        eigenvectorLength += shape[-1]
        shapeList.append(shape)
        stackList[i] = stackList[i].reshape(npixels, -1)
        avg = numpy.sum(stackList[i], 0) / (1.0 * npixels)
        numpy.subtract(stackList[i], avg, stackList[i])
        avgList.append(avg)

    #create the needed storage space for the covariance matrix
    covMatrix = numpy.zeros((eigenvectorLength, eigenvectorLength),
                            numpy.float32)

    rowOffset = 0
    indexDict = {}
    for i in range(len(stackList)):
        iVectorLength = shapeList[i][-1]
        colOffset = 0
        for j in range(len(stackList)):
            jVectorLength = shapeList[j][-1]
            if i <= j:
                covMatrix[rowOffset:(rowOffset + iVectorLength),
                          colOffset:(colOffset + jVectorLength)] =\
                          dotblas.dot(stackList[i].T, stackList[j])/(npixels-1)
                if i < j:
                    key = "%02d%02d" % (i, j)
                    indexDict[key] = (rowOffset, rowOffset + iVectorLength,
                                      colOffset, colOffset + jVectorLength)
            else:
                key = "%02d%02d" % (j, i)
                rowMin, rowMax, colMin, colMax = indexDict[key]
                covMatrix[rowOffset:(rowOffset + iVectorLength),
                          colOffset:(colOffset + jVectorLength)] =\
                          covMatrix[rowMin:rowMax, colMin:colMax].T
            colOffset += jVectorLength
        rowOffset += iVectorLength
    indexDict = None

    #I have the covariance matrix, calculate the eigenvectors and eigenvalues
    totalVariance = numpy.array(numpy.diag(covMatrix), copy=True)
    # use the correlation matrix if required
    normalizeToUnitStandardDeviation = scale
    #option to normalize to unit standard deviation
    if normalizeToUnitStandardDeviation:
        for i in range(covMatrix.shape[0]):
            if totalVariance[i] > 0:
                covMatrix[i, :] /= numpy.sqrt(totalVariance[i])
                covMatrix[:, i] /= numpy.sqrt(totalVariance[i])
    totalVariance = numpy.diag(covMatrix).sum()
    evalues, evectors = numpy.linalg.eigh(covMatrix)
    covMatrix = None
    _logger.info("Total Variance = %s", totalVariance)
    # The total variance should also be the sum of all the eigenvalues
    calculatedTotalVariance = evalues.sum()
    if abs(totalVariance - calculatedTotalVariance) > \
           (0.0001 * calculatedTotalVariance):
        _logger.warning("Discrepancy on total variance")
        _logger.warning("Variance from matrix = %s",
                     totalVariance)
        _logger.warning("Variance from sum of eigenvalues = %s",
                     calculatedTotalVariance)

    images = numpy.zeros((ncomponents, npixels), numpy.float32)
    eigenvectors = numpy.zeros((ncomponents, eigenvectorLength), numpy.float32)
    eigenvalues = numpy.zeros((ncomponents,), numpy.float32)

    a = [(evalues[i], i) for i in range(len(evalues))]
    a.sort()
    a.reverse()
    totalExplainedVariance = 0.0
    for i0 in range(ncomponents):
        i = a[i0][1]
        eigenvalues[i0] = evalues[i]
        partialExplainedVariance = 100. * evalues[i] / \
                                   calculatedTotalVariance
        _logger.info("PC%02d  Explained variance %.5f %% " %\
                                    (i0 + 1, partialExplainedVariance))
        totalExplainedVariance += partialExplainedVariance
        eigenvectors[i0, :] = evectors[:, i]
        #print("NORMA = ", numpy.dot(evectors[:, i].T, evectors[:, i]))
    _logger.info("Total explained variance = %.2f %% " % totalExplainedVariance)

    # figure out if eigenvectors are to be multiplied by -1
    for i0 in range(ncomponents):
        if eigenvectors[i0].sum() < 0.0:
            _logger.info("PC%02d multiplied by -1" % i0)
            eigenvectors[i0] *= -1

    for i in range(ncomponents):
        colOffset = 0
        for j in range(len(stackList)):
            jVectorLength = shapeList[j][-1]
            images[i, :] +=\
                    dotblas.dot(stackList[j],
                                eigenvectors[i, colOffset:(colOffset + jVectorLength)])
            colOffset += jVectorLength

    #restore shapes and values
    for i in range(len(stackList)):
        numpy.add(stackList[i], avgList[i], stackList[i])
        stackList[i] = stackList[i].reshape(*shapeList[i])

    if c is None:
        images = images.reshape(ncomponents, r, 1)
    else:
        images = images.reshape(ncomponents, r, c)

    if legacy:
        return images, eigenvalues, eigenvectors
    else:
        return {"scores": images,
                "eigenvalues": eigenvalues,
                "eigenvectors": eigenvectors,
                "average": avgList,
                "pixels": npixels,
                "variance": calculatedTotalVariance}

def expectationMaximizationPCA(stack, ncomponents=10, binning=None, legacy=True, **kw):
    """
    This is a fast method when the number of components is small
    """
    _logger.debug("expectationMaximizationPCA")
    #This part is common to all ...
    if binning is None:
        binning = 1

    if hasattr(stack, "info") and hasattr(stack, "data"):
        data = stack.data
    else:
        data = stack
    if len(data.shape) == 3:
        r, c, N = data.shape
        data = data.reshape(r * c, N)
    else:
        r, N = data.shape
        c = 1

    if binning > 1:
        data = numpy.reshape(data, [data.shape[0], data.shape[1] / binning,
                                    binning])
        data = numpy.sum(data, axis=-1)
        N /= binning
    if ncomponents > N:
        raise ValueError("Number of components too high.")
    #end of common part
    avg = numpy.sum(data, axis=0, dtype=numpy.float64) / (1.0 * r * c)
    numpy.subtract(data, avg, data)
    dataw = data * 1
    images = numpy.zeros((ncomponents, r * c), data.dtype)
    eigenvalues = numpy.zeros((ncomponents,), data.dtype)
    eigenvectors = numpy.zeros((ncomponents, N), data.dtype)
    for i in range(ncomponents):
        #generate a random vector
        p = numpy.random.random(N)
        #10 iterations seems to be fairly accurate, but it is
        #slow when reaching "noise" components.
        #A variation threshold of 1 % seems to be acceptable.
        tmod_old = 0
        tmod = 0.02
        j = 0
        max_iter = 7
        while ((abs(tmod - tmod_old) / tmod) > 0.01) and (j < max_iter):
            tmod_old = tmod
            t = 0.0
            for k in range(r * c):
                t += dotblas.dot(dataw[k, :], p.T) * dataw[k, :]
            tmod = numpy.sqrt(numpy.sum(t * t))
            p = t / tmod
            j += 1

        eigenvectors[i, :] = p
        #subtract the found component from the dataset
        for k in range(r * c):
            dataw[k, :] -= dotblas.dot(dataw[k, :], p.T) * p
    # calculate eigenvalues via the Rayleigh Quotients:
    # eigenvalue = \
    # (Eigenvector.T * Covariance * EigenVector)/ (Eigenvector.T * Eigenvector)
    for i in range(ncomponents):
        tmp = dotblas.dot(data, eigenvectors[i, :].T)
        eigenvalues[i] = \
            dotblas.dot(tmp.T, tmp) / dotblas.dot(eigenvectors[i, :].T,
                                                  eigenvectors[i, :])

    #Generate the eigenimages
    for i0 in range(ncomponents):
        images[i0, :] = dotblas.dot(data, eigenvectors[i0, :])

    #restore the original data
    numpy.add(data, avg, data)

    #reshape the images
    images = images.reshape(ncomponents, r, c)
    if legacy:
        return images, eigenvalues, eigenvectors
    else:
        return {"scores": images,
                "eigenvalues": eigenvalues,
                "eigenvectors": eigenvectors,
                "average": avg,
                "pixels": r * c,
                # This method does not calculate the covariance matrix
                #"variance": calculatedTotalVariance,
                }


def numpyCovariancePCA(stack, ncomponents=10, binning=None, legacy=True, **kw):
    mask = kw.get("mask", None)
    spectral_mask = kw.get("spectral_mask", None)
    force = kw.get("force", True)
    return numpyPCA(stack,
                    ncomponents=ncomponents,
                    binning=binning,
                    legacy=legacy,
                    center=True,
                    scale=False,
                    mask=mask,
                    spectral_mask=spectral_mask,
                    force=force)

def numpyCorrelationPCA(stack, ncomponents=10, binning=None, legacy=True, **kw):
    mask = kw.get("mask", None)
    spectral_mask = kw.get("spectral_mask", None)
    force = kw.get("force", True)
    return numpyPCA(stack,
                    ncomponents=ncomponents,
                    binning=binning,
                    legacy=legacy,
                    center=True,
                    scale=True,
                    mask=mask,
                    spectral_mask=spectral_mask,
                    force=force)

def numpyPCA(stack, ncomponents=10, binning=None, legacy=True,
                     center=True, scale=False, mask=None, spectral_mask=None, force=True, **kw):
    """
    This is a covariance method using numpy
    """
    _logger.debug("PCAModule.numpyPCA called")
    if hasattr(stack, "info"):
        index = stack.info.get('McaIndex', -1)
    elif "index" in kw:
        index = kw["index"]
    else:
        print("WARNING: Assuming index is -1 in numpyPCA")
        index = -1
    return PCATools.numpyPCA(stack,
                             index=index,
                             ncomponents=ncomponents,
                             binning=binning,
                             legacy=legacy,
                             center=center,
                             scale=scale,
                             mask=mask,
                             spectral_mask=spectral_mask,
                             force=force)

def mdpPCASVDFloat32(stack, ncomponents=10, binning=None,
                     mask=None, spectral_mask=None, legacy=True, **kw):
    return mdpPCA(stack, ncomponents, binning=binning, dtype='float32',
                  svd='True', mask=mask, spectral_mask=spectral_mask, legacy=legacy, **kw)


def mdpPCASVDFloat64(stack, ncomponents=10, binning=None,
                     mask=None, spectral_mask=None, legacy=True, **kw):
    return mdpPCA(stack, ncomponents, binning=binning, dtype='float64',
                  svd='True', mask=mask, spectral_mask=spectral_mask, legacy=legacy, **kw)


def mdpICAFloat32(stack, ncomponents=10, binning=None,
                  mask=None, spectral_mask=None, legacy=True, **kw):
    return mdpICA(stack, ncomponents, binning=binning, dtype='float32',
                  svd='True', mask=mask, spectral_mask=spectral_mask, legacy=legacy, **kw)


def mdpICAFloat64(stack, ncomponents=10, binning=None,
                  mask=None, spectral_mask=None, legacy=True, **kw):
    return mdpICA(stack, ncomponents, binning=binning, dtype='float64',
                  svd='True', mask=mask, spectral_mask=spectral_mask, legacy=legacy, **kw)


def mdpPCA(stack, ncomponents=10, binning=None, dtype='float64', svd='True',
           mask=None, spectral_mask=None, legacy=True, **kw):
    _logger.debug("MDP Method")
    _logger.debug("binning = %s", binning)
    _logger.debug("dtype = %s", dtype)
    _logger.debug("svd = %s", svd)
    for key in kw:
        _logger.info("mdpPCA Key ignored: %s", key)
    #This part is common to all ...
    if binning is None:
        binning = 1

    if hasattr(stack, "info") and hasattr(stack, "data"):
        data = stack.data[:]
    else:
        data = stack[:]

    oldShape = data.shape
    if len(data.shape) == 3:
        r, c, N = data.shape
        # data can be dynamically loaded
        if isinstance(data, numpy.ndarray):
            data = data.reshape(r * c, N)
    else:
        r, N = data.shape
        c = 1

    if binning > 1:
        if isinstance(data, numpy.ndarray):
            data = numpy.reshape(data, [data.shape[0], data.shape[1] // binning,
                                        binning])
            data = numpy.sum(data, axis=-1)
        N = int(N / binning)

    if ncomponents > N:
        if binning == 1:
            if data.shape != oldShape:
                data = data.reshape(*oldShape)
        raise ValueError("Number of components too high.")
    #end of common part

    #begin the specific coding
    pca = mdp.nodes.PCANode(output_dim=ncomponents, dtype=dtype, svd=svd)

    shape = data.shape
    if len(data.shape) == 3:
        step = 10
        if r > step:
            last = step * (int(r / step) - 1)
            for i in range(0, last, step):
                for j in range(step):
                    print("Training data %d out of %d" % (i + j + 1, r))
                tmpData = data[i:(i + step), :, :]
                if binning > 1:
                    tmpData = tmpData.reshape(step * shape[1],
                                     shape[2] // binning,
                                     binning)
                    tmpData = numpy.sum(tmpData, axis=-1)
                else:
                    tmpData = tmpData.reshape(step * shape[1], shape[2])
                if spectral_mask is None:
                    pca.train(tmpData)
                else:
                    pca.train(tmpData[:, spectral_mask > 0])
            tmpData = None
            last = i + step
        else:
            last = 0
        if binning > 1:
            for i in range(last, r):
                print("Training data %d out of %d" % (i + 1, r))
                tmpData = data[i, :, :]
                tmpData = tmpData.reshape(shape[1], shape[2] // binning, binning)
                tmpData = numpy.sum(tmpData, axis=-1)
                if spectral_mask is None:
                    pca.train(tmpData)
                else:
                    pca.train(tmpData[:, spectral_mask > 0])
            tmpData = None
        else:
            for i in range(last, r):
                print("Training data %d out of %d" % (i + 1, r))
                if spectral_mask is None:
                    pca.train(data[i, :, :])
                else:
                    pca.train(data[i, :, spectral_mask > 0])
    else:
        if data.shape[0] > 10000:
            step = 1000
            last = step * (int(data.shape[0] / step) - 1)
            if spectral_mask is None:
                for i in range(0, last, step):
                    print("Training data from %d to %d of %d" %\
                          (i + 1, i + step, data.shape[0]))
                    pca.train(data[i:(i + step), :])
                print("Training data from %d to end of %d" %\
                      (i + step + 1, data.shape[0]))
                pca.train(data[(i + step):, :])
            else:
                for i in range(0, last, step):
                    print("Training data from %d to %d of %d" %\
                          (i + 1, i + step, data.shape[0]))
                    pca.train(data[i:(i + step), spectral_mask > 0])
                # TODO i is undefined here in the print statement
                print("Training data from %d to end of %d" %\
                      (i + step + 1, data.shape[0]))
                pca.train(data[(i + step):, spectral_mask > 0])
        elif data.shape[0] > 1000:
            i = int(data.shape[0] / 2)
            if spectral_mask is None:
                pca.train(data[:i, :])
            else:
                pca.train(data[:i, spectral_mask > 0])
            _logger.debug("Half training")
            if spectral_mask is None:
                pca.train(data[i:, :])
            else:
                pca.train(data[i:, spectral_mask > 0])
            _logger.debug("Full training")
        else:
            if spectral_mask is None:
                pca.train(data)
            else:
                pca.train(data[:, spectral_mask > 0])
    pca.stop_training()

    # avg = pca.avg
    eigenvalues = pca.d
    eigenvectors = pca.v.T
    proj = pca.get_projmatrix(transposed=0)
    if len(data.shape) == 3:
        images = numpy.zeros((ncomponents, r, c), data.dtype)
        for i in range(r):
            print("Building images. Projecting data %d out of %d" % (i + 1, r))
            if binning > 1:
                if spectral_mask is None:
                    tmpData = data[i, :, :]
                else:
                    tmpData = data[i, :, spectral_mask > 0]
                tmpData = tmpData.reshape(data.shape[1], data.shape[2] // binning, binning)
                tmpData = numpy.sum(tmpData, axis=-1)
                images[:, i, :] = numpy.dot(proj.astype(data.dtype), tmpData.T)
            else:
                if spectral_mask is None:
                    images[:, i, :] = numpy.dot(proj.astype(data.dtype),
                                                data[i, :, :].T)
                else:
                    images[:, i, :] = numpy.dot(proj.astype(data.dtype),
                                                data[i, :, spectral_mask > 0].T)
    else:
        if spectral_mask is None:
            images = numpy.dot(proj.astype(data.dtype), data.T)
        else:
            images = numpy.dot(proj.astype(data.dtype),
                               data[:, spectral_mask > 0].T)

    #make sure the shape of the original data is not modified
    if hasattr(stack, "info") and hasattr(stack, "data"):
        if stack.data.shape != oldShape:
            stack.data = stack.data.reshape(*oldShape)
    else:
        if stack.shape != oldShape:
            stack = stack.reshape(*oldShape)

    if spectral_mask is not None:
        eigenvectors = numpy.zeros((ncomponents, N), pca.v.dtype)
        for i in range(ncomponents):
            eigenvectors[i, spectral_mask > 0] = pca.v.T[i]

    #reshape the images
    images = images.reshape(ncomponents, r, c)
    if legacy:
        return images, eigenvalues, eigenvectors
    else:
        return {"scores": images,
                "eigenvalues": eigenvalues,
                "eigenvectors": eigenvectors,
                #"average": avgSpectrum,
                #"pixels": calculatedPixels,
                #"variance": calculatedTotalVariance,
                }


def mdpICA(stack, ncomponents=10, binning=None, dtype='float64',
           svd='True', mask=None, spectral_mask=None, legacy=True, **kw):
    for key in kw:
        print("mdpICA Key ignored: %s" % key)
    #This part is common to all ...
    if binning is None:
        binning = 1

    if hasattr(stack, "info") and hasattr(stack, "data"):
        data = stack.data[:]
    else:
        data = stack[:]

    oldShape = data.shape
    if len(data.shape) == 3:
        r, c, N = data.shape
        if isinstance(data, numpy.ndarray):
            data = data.reshape(r * c, N)
    else:
        r, N = data.shape
        c = 1

    if binning > 1:
        if isinstance(data, numpy.ndarray):
            data = numpy.reshape(data,
                                 [data.shape[0], data.shape[1] // binning,
                                  binning])
            data = numpy.sum(data, axis=-1)
        N = N // binning

    if ncomponents > N:
        if binning == 1:
            if data.shape != oldShape:
                data = data.reshape(*oldShape)
        raise ValueError("Number of components too high.")

    if 1:
        if (mdp.__version__ >= "2.5"):
            _logger.debug("TDSEPNone")
            ica = mdp.nodes.TDSEPNode(white_comp=ncomponents,
                                      verbose=False,
                                      dtype="float64",
                                      white_parm={'svd': svd})
            t0 = time.time()
            shape = data.shape
            if len(data.shape) == 3:
                if r > 10:
                    step = 10
                    last = step * (int(r / step) - 1)
                    for i in range(0, last, step):
                        print("Training data from %d to %d out of %d" %\
                              (i + 1, i + step, r))
                        tmpData = data[i:(i + step), :, :]
                        if binning > 1:
                            tmpData = tmpData.reshape((step * shape[1],
                                             shape[2] // binning,
                                             binning))
                            tmpData = numpy.sum(tmpData, axis=-1)
                        else:
                            tmpData = tmpData.reshape(step * shape[1], shape[2])
                        if spectral_mask is None:
                            ica.train(tmpData)
                        else:
                            ica.train(tmpData[:, spectral_mask > 0])
                    tmpData = None
                    last = i + step
                else:
                    last = 0
                if binning > 1:
                    for i in range(last, r):
                        print("Training data %d out of %d" % (i + 1, r))
                        tmpData = data[i, :, :]
                        tmpData = tmpData.reshape(shape[1], shape[2] // binning, binning)
                        tmpData = numpy.sum(tmpData, axis=-1)
                        if spectral_mask is None:
                            ica.train(tmpData)
                        else:
                            ica.train(tmpData[:, spectral_mask > 0])
                    tmpData = None
                else:
                    for i in range(last, r):
                        print("Training data %d out of %d" % (i + 1, r))
                        if spectral_mask is None:
                            ica.train(data[i, :, :])
                        else:
                            ica.train(data[i, :, spectral_mask > 0])
            else:
                if data.shape[0] > 10000:
                    step = 1000
                    last = step * (int(data.shape[0] / step) - 1)
                    for i in range(0, last, step):
                        print("Training data from %d to %d of %d" %\
                              (i + 1, i + step, data.shape[0]))
                        if spectral_mask is None:
                            ica.train(data[i:(i + step), :])
                        else:
                            ica.train(data[i:(i + step), spectral_mask > 0])
                    print("Training data from %d to end of %d" %\
                          (i + step + 1, data.shape[0]))
                    if spectral_mask is None:
                        ica.train(data[(i + step):, :])
                    else:
                        ica.train(data[(i + step):, spectral_mask > 0])
                elif data.shape[0] > 1000:
                    i = int(data.shape[0] / 2)
                    if spectral_mask is None:
                        ica.train(data[:i, :])
                    else:
                        ica.train(data[:i, spectral_mask > 0])
                    _logger.debug("Half training")
                    if spectral_mask is None:
                        ica.train(data[i:, :])
                    else:
                        ica.train(data[i:, spectral_mask > 0])
                    _logger.debug("Full training")
                else:
                    if spectral_mask is None:
                        ica.train(data)
                    else:
                        ica.train(data[:, spectral_mask > 0])
            ica.stop_training()
            _logger.debug("training elapsed = %f", time.time() - t0)
        else:
            if 0:
                print("ISFANode (alike)")
                ica = mdp.nodes.TDSEPNode(white_comp=ncomponents,
                                            verbose=False,
                                            dtype='float64',
                                            white_parm={'svd':svd})
            elif 1:
                _logger.debug("FastICANode")
                ica = mdp.nodes.FastICANode(white_comp=ncomponents,
                                            verbose=False,
                                            dtype=dtype)
            else:
                _logger.debug("CuBICANode")
                ica = mdp.nodes.CuBICANode(white_comp=ncomponents,
                                            verbose=False,
                                            dtype=dtype)
            ica.train(data)
            ica.stop_training()
            #output = ica.execute(data)

        proj = ica.get_projmatrix(transposed=0)

        # These are the PCA data
        eigenvalues = ica.white.d * 1
        eigenvectors = ica.white.v.T * 1
        vectors = numpy.zeros((ncomponents * 2, N), data.dtype)
        if spectral_mask is None:
            vectors[0:ncomponents, :] = proj * 1  # ica components?
            vectors[ncomponents:, :] = eigenvectors
        else:
            vectors = numpy.zeros((2 * ncomponents, N), eigenvectors.dtype)
            vectors[0:ncomponents, spectral_mask > 0] = proj * 1
            vectors[ncomponents:, spectral_mask > 0] = eigenvectors

        if (len(data.shape) == 3):
            images = numpy.zeros((2 * ncomponents, r, c), data.dtype)
            for i in range(r):
                _logger.info("Building images. Projecting data %d out of %d",
                             i + 1, r)
                if binning > 1:
                    if spectral_mask is None:
                        tmpData = data[i, :, :]
                    else:
                        tmpData = data[i, :, spectral_mask > 0]
                    tmpData = tmpData.reshape((data.shape[1],
                                     data.shape[2] // binning,
                                     binning))
                    tmpData = numpy.sum(tmpData, axis=-1)
                    tmpData = ica.white.execute(tmpData)
                else:
                    if spectral_mask is None:
                        tmpData = ica.white.execute(data[i, :, :])
                    else:
                        tmpData = ica.white.execute(data[i, :, spectral_mask > 0])
                images[ncomponents:(2 * ncomponents), i, :] = tmpData.T[:, :]
                images[0:ncomponents, i, :] =\
                    numpy.dot(tmpData, ica.filters).T[:, :]
        else:
            images = numpy.zeros((2 * ncomponents, r * c), data.dtype)
            if spectral_mask is None:
                images[0:ncomponents, :] =\
                    numpy.dot(proj.astype(data.dtype), data.T)
            else:
                tmpData = data[:, spectral_mask > 0]
                images[0:ncomponents, :] =\
                    numpy.dot(proj.astype(data.dtype), tmpData.T)
            proj = ica.white.get_projmatrix(transposed=0)
            if spectral_mask is None:
                images[ncomponents:(2 * ncomponents), :] =\
                    numpy.dot(proj.astype(data.dtype), data.T)
            else:
                images[ncomponents:(2 * ncomponents), :] =\
                    numpy.dot(proj.astype(data.dtype), data[:, spectral_mask > 0].T)
        images = images.reshape(2 * ncomponents, r, c)
    else:
        ica = mdp.nodes.FastICANode(white_comp=ncomponents,
                                    verbose=False, dtype=dtype)
        ica.train(data)
        output = ica.execute(data)

        proj = ica.get_projmatrix(transposed=0)

        # These are the PCA data
        # make sure no reference to the ica module is kept to make sure
        # memory is relased.
        eigenvalues = ica.white.d * 1
        eigenvectors = ica.white.v.T * 1
        images = numpy.zeros((2 * ncomponents, r * c), data.dtype)
        vectors = numpy.zeros((ncomponents * 2, N), data.dtype)
        vectors[0:ncomponents, :] = proj * 1  # ica components?
        vectors[ncomponents:, :] = eigenvectors
        images[0:ncomponents, :] = numpy.dot(proj.astype(data.dtype), data.T)
        proj = ica.white.get_projmatrix(transposed=0)
        images[ncomponents:(2 * ncomponents), :] =\
            numpy.dot(proj.astype(data.dtype), data.T)
        images = images.reshape(2 * ncomponents, r, c)

    if binning == 1:
        if data.shape != oldShape:
            data = data.reshape(*oldShape)
    if legacy:
        return images, eigenvalues, vectors
    else:
        return {"scores": images,
                "eigenvalues": eigenvalues,
                "eigenvectors": vectors,
                #"average": avgSpectrum,
                #"pixels": calculatedPixels,
                #"variance": calculatedTotalVariance,
                }


def main():
    from PyMca.PyMcaIO import EDFStack
    from PyMca.PyMcaIO import EdfFile
    import sys
    inputfile = r"D:\DATA\COTTE\ch09\ch09__mca_0005_0000_0000.edf"
    if len(sys.argv) > 1:
        inputfile = sys.argv[1]
        print(inputfile)
    elif os.path.exists(inputfile):
        print("Using a default test case")
    else:
        print("Usage:")
        print("python PCAModule.py indexed_edf_stack")
        sys.exit(0)
    stack = EDFStack.EDFStack(inputfile)
    r0, c0, n0 = stack.data.shape
    ncomponents = 5
    outfile = os.path.basename(inputfile) + "ICA.edf"
    e0 = time.time()
    images, eigenvalues, eigenvectors = mdpICA(stack.data, ncomponents,
                                               binning=1, svd=True,
                                               dtype='float64')
    #images, eigenvalues, eigenvectors =  lanczosPCA2(stack.data,
    #                                                 ncomponents,
    #                                                 binning=1)
    if os.path.exists(outfile):
        os.remove(outfile)
    f = EdfFile.EdfFile(outfile)
    for i in range(ncomponents):
        f.WriteImage({}, images[i, :])

    stack.data = stack.data.reshape(r0, c0, n0)
    print("PCA Elapsed = %f" % (time.time() - e0))
    print("eigenvectors PCA2 = ", eigenvectors[0, 200:230])
    stack = None
    stack = EDFStack.EDFStack(inputfile)
    e0 = time.time()
    images2, eigenvalues, eigenvectors = mdpPCA(stack.data, ncomponents,
                                                binning=1)
    stack.data = stack.data.reshape(r0, c0, n0)
    print("MDP Elapsed = %f" % (time.time() - e0))
    print("eigenvectors MDP = ", eigenvectors[0, 200:230])
    if os.path.exists(outfile):
        os.remove(outfile)
    f = EdfFile.EdfFile(outfile)
    for i in range(ncomponents):
        f.WriteImage({}, images[i, :])
    for i in range(ncomponents):
        f.WriteImage({}, images2[i, :])
    f = None

if __name__ == "__main__":
    main()

