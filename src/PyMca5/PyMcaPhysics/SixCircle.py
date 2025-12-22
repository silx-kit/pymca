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
__doc__ = """
Methods to convert single point or complete images to reciprocal space.
It is fully vectorized and therefore very fast for converting complete
images.
"""
import numpy

cos = numpy.cos
sin = numpy.sin


class SixCircle(object):
    def __init__(self):
        self._energy = None
        self._lambda = None
        self._K = 1.0
        self._ub = None
        self.setLambda(1.0)
        self.setUB([1.0, 0.0, 0.0,
                    0.0, 1.0, 0.0,
                    0.0, 0.0, 1.0])

    def setUB(self, ublist):
        """
        :param ublist: the ub matrix element values
        :type ublist: list, tuple or array to convert to a 3x3 matrix
        """
        self._ub = numpy.array(ublist, copy=True, dtype=numpy.float64)
        self._ub = self._ub.reshape(3, 3)

    def getUB(self):
        """
        :return: the ub matrix element values
        :rtype: list(float)
        """
        a = self._ub * 1
        a = numpy.ravel(a)
        return a.tolist()

    def setEnergy(self, energy):
        """
        :param energy: the energy to set in KeV
        :type energy: float
        """
        self._lambda = 12.39842 / energy
        self._energy = energy
        self.update()

    def getEnergy(self):
        """
        :return: the energy in KeV
        :rtype: float
        """
        return self._energy

    def setLambda(self, value):
        """
        :param value: the wavelength to set in Angstroms
        :type value: float
        """
        self._lambda = value
        self._energy = 12.39842 / value
        self.update()

    def getLambda(self):
        """
        :return: the wavelength in Angstroms
        :rtype: float
        """
        return self._lambda

    def update(self):
        """
        compute K from the wavelength value
        """
        self._K = (2 * numpy.pi) / self._lambda

    def getPhiMatrix(self, phi):
        """
        :param phi: the phi angle in degree
        :type phi: float
        :return: the rotation matrix of the phi axis for a given angle
        :rtype: numpy.ndarray
        """
        angle = numpy.radians(phi)
        cphi = cos(angle)
        sphi = sin(angle)
        return numpy.array([[cphi, sphi, 0.0],
                            [-sphi, cphi, 0.0],
                            [0.0, 0.0, 1.0]], numpy.float64)

    def getChiMatrix(self, chi):
        """
        :param chi: the chi angle in degree
        :type chi: float
        :return: the rotation matrix of the chi
        :rtype: numpy.ndarray
        """
        angle = numpy.radians(chi)
        cchi = cos(angle)
        schi = sin(angle)
        return numpy.array([[cchi, 0.0, schi],
                            [0.0, 1.0, 0.0],
                            [-schi, 0.0, cchi]], numpy.float64)

    def getThetaMatrix(self, th):
        """
        :param th: the theta angle in Degree
        :type th: float
        :return: the rotation matrix of the theta axis
        :rtype: numpy.ndarray
        """
        angle = numpy.radians(th)
        cth = cos(angle)
        sth = sin(angle)
        return numpy.array([[cth, sth, 0],
                            [-sth, cth, 0],
                            [0, 0, 1]], numpy.float64)

    def getDeltaMatrix(self, delta):
        """
        :param delta: the delta angle in Degree
        :type delta: float
        :return: the rotation matrix of the delta axis
        :rtype: numpy.ndarray
        """
        angle = numpy.radians(delta)
        cdel = cos(angle)
        sdel = sin(angle)
        return numpy.array([[cdel, sdel, 0],
                            [-sdel, cdel, 0],
                            [0, 0, 1]], numpy.float64)

    def getGammaMatrix(self, gamma):
        """
        :param gamma: the gamma angle in Degree
        :type gamma: float
        :return: the rotation matrix of the gamma axis
        :rtype: numpy.ndarray
        """
        angle = numpy.radians(gamma)
        cgam = cos(angle)
        sgam = sin(angle)
        return numpy.array([[1.0, 0.0, 0.0],
                            [0.0, cgam, -sgam],
                            [0.0, sgam, cgam]], numpy.float64)

    def getMuMatrix(self, mu):
        """
        :param mu: the mu angle in degree
        :type mu: float
        :return: the rotation matrix of the mu axis
        :rtype: numpy.ndarray
        """
        angle = numpy.radians(mu)
        cmu = cos(angle)
        smu = sin(angle)
        return numpy.array([[1.0, 0.0, 0.0],
                            [0.0, cmu, -smu],
                            [0.0, smu, cmu]], numpy.float64)

    def _getDeltaDotGammaMatrix(self, delta, gamma, gamma_first=False):
        """
        :param delta: the delta angles in Degrees
        :type delta: numpy.ndarray (1D)
        :param gamma: the gamma values in Degrees
        :type gamma: numpy.ndarray (1D)
        :param gamma_first: if delta and gamma are arrays, which one variates first.
        :type gamma_first: boolean
        :return: all the rotation matrix of all the delta, gamma combinations
        :rtype: numpy.ndarray (3x3, len(delta) * len(gamma))
        """
        delr = numpy.radians(delta)
        gamr = numpy.radians(gamma)
        if gamma_first:
            cgam, cdel = numpy.meshgrid(numpy.cos(gamr), numpy.cos(delr))
            sgam, sdel = numpy.meshgrid(numpy.sin(gamr), numpy.sin(delr))
        else:
            #this is to give the same result as Didier and not the transpose
            cdel, cgam = numpy.meshgrid(numpy.cos(delr), numpy.cos(gamr))
            sdel, sgam = numpy.meshgrid(numpy.sin(delr), numpy.sin(gamr))
        deltaDotGamma = numpy.zeros((3, 3, len(delta), len(gamma)),
                                    numpy.float64)
        # 1st row of dot(deltamatrix, gammaMatrix)
        deltaDotGamma[0, 0, :] = cdel
        deltaDotGamma[0, 1, :] = (sdel * cgam)[:]
        deltaDotGamma[0, 2, :] = -sdel * sgam
        # 2nd row of dot(deltaMatrix, gammaMatrix)
        deltaDotGamma[1, 0, :] = -sdel
        deltaDotGamma[1, 1, :] = cdel * cgam
        deltaDotGamma[1, 2, :] = -cdel * sgam
        # 3rd row of dot(deltaMatrix, gammaMatrix)
        deltaDotGamma[2, 0, :] = 0.0
        deltaDotGamma[2, 1, :] = sgam
        deltaDotGamma[2, 2, :] = cgam
        deltaDotGamma = deltaDotGamma.reshape(3, 3, len(delta) * len(gamma))

        return deltaDotGamma

    def getQMu(self, phi=0., chi=0., theta=0., mu=0.,
                       delta=0., gamma=0., gamma_first=False):
        """
        :param phi: angle in Degrees
        :type phi: float
        :param chi: angle in Degrees
        :type chi: float
        :param theta: angle in Degrees
        :type theta: float
        :param mu: angle in Degrees
        :type mu: float
        :param delta: angle in Degrees
        :type delta: float or numpy.ndarray
        :param gamma: angle in Degrees
        :type gamma: float or numpy.ndarray
        :param gamma_first: if delta and gamma are arrays, which one variates first.
        :type gamma_first: boolean

        :return: Q coordinates for all the given delta, gamma values
        :rtype: numpy.ndarray (len(delta), len(gamma), 3)
        """
        PHIi = self.getPhiMatrix(phi).T
        CHIi = self.getChiMatrix(chi).T
        THi = self.getThetaMatrix(theta).T
        MUi = self.getMuMatrix(mu).T
        tmpArray = numpy.dot(PHIi, numpy.dot(CHIi, numpy.dot(THi, MUi)))
        Q = self.getQLab(mu=mu, delta=delta, gamma=gamma, gamma_first=gamma_first)
        Q = Q.reshape(3, -1)
        Q = numpy.transpose(numpy.dot(tmpArray, Q))
        if type(delta) in [type(1.0), type(1)]:
            lendelta = 1
        else:
            lendelta = len(delta)
        if type(gamma) in [type(1.0), type(1)]:
            lengamma = 1
        else:
            lengamma = len(gamma)
        Q = Q.reshape(lengamma, lendelta, 3)
        return Q

    def getQSurface(self, phi=0., chi=0., theta=0., mu=0.,
                        delta=0., gamma=0., gamma_first=False):
        """
        :param phi: angle in Degrees
        :type phi: float
        :param chi: angle in Degrees
        :type chi: float
        :param theta: angle in Degrees
        :type theta: float
        :param mu: angle in Degrees
        :type mu: float
        :param delta: angle in Degrees
        :type delta: float or numpy.ndarray
        :param gamma: angle in Degrees
        :type gamma: float or numpy.ndarray
        :param gamma_first: if delta and gamma are arrays, which one variates first.
        :type gamma_first: boolean

        :return: Q values for all the given delta, gamma values

        This is only true if the diffractometer has been properly aligned.
        """
        PHIi = self.getPhiMatrix(phi).T
        CHIi = self.getChiMatrix(chi).T
        THi  = self.getThetaMatrix(theta).T
        MUi   = self.getMuMatrix(mu).T
        tmpArray = numpy.dot(PHIi, numpy.dot(CHIi, numpy.dot(THi, MUi)))
        Q = self.getQLab(mu=mu, delta=delta, gamma=gamma, gamma_first=gamma_first)
        Q = Q.reshape(3, -1)
        return (numpy.dot(tmpArray, Q))

    def getQLab(self, mu=0.0, delta=0.0, gamma=0.0, gamma_first=False):
        """
        :param mu: angle in Degrees
        :type mu: float
        :param delta: angle in Degrees
        :type delta: float or numpy.ndarray
        :param gamma: angle in Degrees
        :type gamma: float or numpy.ndarray
        :param gamma_first: if delta and gamma are arrays, which one variates first.
        :type gamma_first: boolean

        :return: the Q coordinates in the Lab system
        :rtype: numpy.ndarray ()

        Q = Kf - Ki = (2 * pi / lambda) * (MU DELTA GAMMA - I) * (0, 1, 0)

        This gives (transforming angles to radians):

        (2*pi/lambda) * (        sin(delta) cos(gamma),
                         cos(mu) cos(delta) cos(gamma) - sin(mu) sin(gamma) - 1,
                         sin(mu) cos(delta) cos(gamma) + cos(mu) sin(gamma))

        or, in terms of DG = numpy.dot(DELTA, GAMMA):

        (2*pi/lambda) * (         DG[0,1],
                         cos(mu)* DG[1,1] - sin(mu) * DG[2,1] - 1
                         sin(mu)* DG[1,1] + cos(mu) * DG[2,1])


        """
        alpha = numpy.radians(mu)
        cmu = cos(alpha)
        smu = sin(alpha)
        alpha = numpy.radians(delta)
        cdel = cos(alpha)
        sdel = sin(alpha)
        alpha = numpy.radians(gamma)
        cgam = cos(alpha)
        sgam = sin(alpha)

        if isinstance(delta, numpy.ndarray) or \
           isinstance(gamma, numpy.ndarray):
            if gamma_first:
                cgam, cdel = numpy.meshgrid(cgam, cdel)
                sgam, sdel = numpy.meshgrid(sgam, sdel)
            else:
                # this is to give the same result as Didier and not the transpose
                cdel, cgam = numpy.meshgrid(cdel, cgam)
                sdel, sgam = numpy.meshgrid(sdel, sgam)
            Q = numpy.zeros((3, sdel.shape[0], sdel.shape[1]), numpy.float64)
            Q[0, :, :] = sdel * cgam
            Q[1, :, :] = cmu * cdel * cgam - smu * sgam - 1
            Q[2, :, :] = smu * cdel * cgam + cmu * sgam
        else:
            Q = numpy.zeros((3, 1), numpy.float64)
            Q[0, 0] = sdel * cgam
            Q[1, 0] = cmu * cdel * cgam - smu * sgam - 1
            Q[2, 0] = smu * cdel * cgam + cmu * sgam
        return Q * self._K

    def getHKL(self, phi=0., chi=0., theta=0., mu=0.,
                   delta=0., gamma=0., gamma_first=False):
        """
        :param phi: angle in Degrees
        :type phi: float
        :param chi: angle in Degrees
        :type chi: float
        :param theta: angle in Degrees
        :type theta: float
        :param mu: angle in Degrees
        :type mu: float
        :param delta: angle in Degrees
        :type delta: float or numpy.ndarray
        :param gamma: angle in Degrees
        :type gamma: float or numpy.ndarray
        :param gamma_first: if delta and gamma are arrays, which one variates first.
        :type gamma_first: boolean

        :return: HKL values for all the given delta, gamma values
        """
        PHIi = self.getPhiMatrix(phi).T
        CHIi = self.getChiMatrix(chi).T
        THi = self.getThetaMatrix(theta).T
        MUi = self.getMuMatrix(mu).T
        UBi = numpy.linalg.inv(self._ub)
        tmpArray = numpy.dot(UBi,
                             numpy.dot(PHIi,
                                       numpy.dot(CHIi,
                                                 numpy.dot(THi, MUi))))
        Q = self.getQLab(mu=mu, delta=delta, gamma=gamma, gamma_first=gamma_first)
        Q = Q.reshape(3, -1)
        return (numpy.dot(tmpArray, Q))


def getHKL(wavelength, ub, phi=0., chi=0., theta=0., mu=0.,
           delta=0., gamma=0., gamma_first=False):
    """
    A convenience function that takes the whole input in one go.

    :param wavelength: the wavelength in Angstroms
    :type wavelength: float
    :param ub: the ub matrix element values
    :type ub: list(float)
    :param phi: angle in Degrees
    :type phi: float
    :param chi: angle in Degrees
    :type chi: float
    :param theta: angle in Degrees
    :type theta: float
    :param mu: angle in Degrees
    :type mu: float
    :param delta: angle in Degrees
    :type delta: float or numpy.ndarray
    :param gamma: angle in Degrees
    :type gamma: float or numpy.ndarray
    :param gamma_first: if delta and gamma are arrays, which one variates first.
    :type gamma_first: boolean

    :return: HKL values for all the given delta, gamma values
    """
    a = SixCircle()
    a.setLambda(wavelength)
    a.setUB(ub)
    return a.getHKL(delta=delta, theta=theta, chi=chi, phi=phi,
                    mu=mu, gamma=gamma, gamma_first=gamma_first)


def main():
    wavelength = 0.363504
    UB = [1.0, 0.0, 0.0,
          0.0, 1.0, 0.0,
          0.0, 0.0, 1.0]
    UB[0] = -4.080
    UB[1] = 0.000
    UB[2] = 0.000
    UB[3] = 0.000
    UB[4] = 4.080
    UB[5] = 0.000
    UB[6] = 0.000
    UB[7] = 0.000
    UB[8] = -4.080
    d = SixCircle()
    d.setLambda(wavelength)
    d.setUB(UB)
    print("H = 0 K = 0 L = 1")
    delta, theta, chi, phi, mu, gamma = 13.5558, 6.77779, -90, 0.0, 0.0, 0.0
    print(d.getHKL(delta=delta, theta=theta, chi=chi, phi=phi,
                   mu=mu, gamma=gamma))
    print("H = 0 K = 1 L = 0")
    delta, theta, chi, phi, mu, gamma = 13.5558, 96.77779, -90, 0.0, 0.0, 0.0
    print(d.getHKL(delta=delta, theta=theta, chi=chi, phi=phi,
                   mu=mu, gamma=gamma))
    print("H = 1 K = 1 L = 1")
    delta, theta, chi, phi, mu, gamma = 23.5910, 47.0595, -135., 0.0, 0.0, 0.0
    print(d.getHKL(delta=delta, theta=theta, chi=chi, phi=phi,
                   mu=mu, gamma=gamma))
    print("H = 2 K = -1 L = 0")
    delta, theta, chi, phi, mu, gamma = 30.6035, -11.2635, 180.0, 0.0, 0.0, 0.0
    print(d.getHKL(delta=delta, theta=theta, chi=chi, phi=phi,
                   mu=mu, gamma=gamma))

    print("H = 2 K = -1 L = 0")
    print(getHKL(wavelength, UB, delta=delta, theta=theta, chi=chi, phi=phi,
                 mu=mu, gamma=gamma))

if __name__ == "__main__":
    main()
