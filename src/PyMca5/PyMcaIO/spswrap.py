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
if sys.platform in ['win32']:
    def getspeclist():
        return []
try:
    from . import sps
    STRING=sps.STRING
    CHAR=sps.CHAR
    DOUBLE=sps.DOUBLE
    FLOAT=sps.FLOAT
    SHORT=sps.SHORT
    UCHAR=sps.UCHAR
    USHORT=sps.USHORT
    TAG_ARRAY=sps.TAG_ARRAY
    TAG_MCA=sps.TAG_MCA
    TAG_IMAGE=sps.TAG_IMAGE
    TAG_SCAN=sps.TAG_SCAN
    TAG_INFO=sps.TAG_INFO
    TAG_MASK=sps.TAG_MASK
    TAG_STATUS=sps.TAG_STATUS
    IS_ARRAY=sps.IS_ARRAY
    IS_MCA=sps.IS_MCA
    IS_IMAGE=sps.IS_IMAGE
    error=sps.error
    updatecounter=sps.updatecounter
    TAG_FRAMES=sps.TAG_FRAMES
except Exception:
    #make sure older versions of sps do not give troubles
    TAG_FRAMES=0x0100
    #windows does not use it
    pass

try:
    import json
    JSON = True
except ImportError:
    JSON = False

import threading
import time

spsdefaultoutput ={"axistitles":   '',
                        "xlabel":       '',
                        "ylabel":       '',
                        "title":        '',
                        "nopts":        0,
                        "xbeg":         0,
                        "xend":         0,
                        "plotlist":     [],
                        "datafile":     '/dev/null',
                        "scantype":     16,
                        "aborted":      0}

spsdefaultarraylist={}

spslock = threading.Lock()

def getarrayinfo(spec,shm):
    result = [0,] * 4

    spslock.acquire()
    try:
       result = sps.getarrayinfo (spec,shm)
    except Exception:
       pass
    spslock.release()
    return result

def getarraylist( spec ):
    result = []
    if specrunning(spec):
        spslock.acquire()
        try:
           result = sps.getarraylist( spec )
           spsdefaultarraylist[spec]=result
        except Exception:
           print("Error reading memory", sys.exc_info())
           pass
        spslock.release()
    else:
        if spec in spsdefaultarraylist:
            return spsdefaultarraylist[spec]
        else:
            spsdefaultarraylist[spec]=[]
            return result
    return result

def isupdated(spec, shmenv):

    result = 0

    spslock.acquire()

    try:
        result = sps.isupdated( spec, shmenv  )
    except Exception:
        pass

    spslock.release()
    return result

def putenv(spec,shmenv,cmd,outp):

    result = None

    spslock.acquire()

    try:
       result = sps.putenv(spec,shmenv,cmd,outp)
    except Exception:
       pass

    spslock.release()

    return result

def getenv(spec,shmenv,key):
    result = ''

    spslock.acquire()

    try:
        #  if key != 'plotlist':
        result = sps.getenv(spec,shmenv,key)
    except sps.error:
        if key in spsdefaultoutput.keys():
            result = spsdefaultoutput[key]
        pass

    spslock.release()

    return result

def updatedone(spec,shmenv):
    result = 0

    spslock.acquire()

    try:
       result = sps.updatedone(spec,shmenv)
    except Exception:
       pass

    spslock.release()
    return result

def getdata(spec,shm):

    result = []

    spslock.acquire()
    try:
        result = sps.getdata(spec,shm)
    except Exception:
        pass
    spslock.release()
    return result

def getdatacol(spec,shm,idx):

    result = []

    spslock.acquire()
    try:
       result = sps.getdatacol(spec,shm,idx)
    except Exception:
       pass
    spslock.release()
    return result

def getdatarow(spec,shm,idx):
    result = []

    spslock.acquire()
    try:
       result = sps.getdatarow(spec,shm,idx)
    except Exception:
       pass
    spslock.release()
    return result

def getspeclist():

    result = []
    i = 0
    spslock.acquire()
    try:
       result = sps.getspeclist()
       # Awful patch because sometimes we miss the
       # shared memory detection on old machines.
       # We just try a maximum of three times
       while (not len(result)) and (i < 2):
           time.sleep(0.050)
           result = sps.getspeclist()
           i = i + 1
       if len(result):result.sort()
    except Exception:
       pass
    spslock.release()
    return result

def getkeylist(spec,shmenv):

    result = []

    spslock.acquire()

    try:
        result = sps.getkeylist(spec,shmenv)
    except Exception:
        pass

    spslock.release()

    return result

def specrunning(spec):
    spec_list = getspeclist()
    if spec not in spec_list:
        return 0
    else:
        return 1

def getmetadata(spec, shm):
    if hasattr(sps, "getmetadata"):
        try:        
            metadata = sps.getmetadata(spec, shm)
        except Exception:
            # this error arrives when accessing old SPEC versions
            # with new versions of the library
            return None
        if metadata.strip():
            if JSON:
                uncoded_data = json.loads(metadata)
            else:
                if shm != "SCAN_D":
                    return None
                # try to put a minimum of protection
                if ("os." not in metadata) and ("sys." not in metadata):
                    try:
                        uncoded_data = eval(metadata)
                    except Exception:
                        print("Error accessing SCAN_D information without json")
                        return None
                else:
                    print("NOT READ TO PREVENT PROBLEMS")
        else:
            # shared memory not populated yet
            return
    else:
        return None
    motors = {}
    metadata = {}
    if type(uncoded_data) in [type([]), type((1,))]:
        if len(uncoded_data) >= 2:
            motors = uncoded_data[0]
            metadata = uncoded_data[1]
        else:
            print("Unexpected metadata length %d instead of 2"  % len(uncoded_data))
    elif type(uncoded_data) == type({}):
        metadata = uncoded_data
    else:
        print("Cannot decode metadata")
    return motors, metadata

def getinfo(spec, shm):
    try:
        return eval(sps.getinfo(spec, shm))
    except Exception:
        return []

