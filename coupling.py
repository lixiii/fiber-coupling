import bpc203 as bpc
import camera as cam
import time
import numpy as np

__DEBUG__ = False

def main():
    ''' Example usage'''
    initBPC()
    initCam( False )
    print("Starting optimisation")
    optimise()
    close()


def initCam(adjustCamera = True, gain = -5, shutter = 0.005):
    """
        adjustCamera: If True, the function will attempt to set the shutter and gain values
    """
    cam.printNumOfCam()
    cam.init()
    if adjustCamera:
        cam.autoAdjustShutter()
    else:
        cam.setGain(gain)
        cam.setShutter(shutter)
        sat = cam.isSaturated()
        print( "Camera saturation: ",  sat)
        if sat:
            raise RuntimeWarning("WARNING: Camera is saturated. Optimisation will not work properly.")
    cam.capture()

def initBPC():
    bpc.init(Verbose=False)
    bpc.zero(1)
    bpc.zero(2)
    # now check for zeroing completion
    while bpc.zeroFinished(1) != True and bpc.zeroFinished(2) != True:
        # resend status check every 0.5s
        time.sleep(0.5)

    # moe to half position for channels 1 & 2
    bpc.position(1, bpc.MAX_POSITION/2)
    bpc.position(2, bpc.MAX_POSITION/2)
    print("Piezo controller initialisation complete. Please manually coarse couple the fiber to the waveguide using the camera interface.")
    print("ENSURE that the FlyCap interface is closed so that the programme can establish connection to the camera")
    input("Press enter to continue. ")

def optimise(stepCount = 5, waveguideSizeX = 5000, waveguideSizeZ = 2000, fineStep = 50, iterationLimit = 10):
    '''
        stepCount: The initial coarse optimisation step count in both directions. 
        waveguideSizeX: size of waveguide in nanometers in the x direction (along the 1D array)
        waveguideSizeZ: the thickness of waveguide
        fineStep: The fine tuning step in nanometers. 
        iterationLimit: The number of fine tuning routines
    '''
    
    # start with a rough scan through the entire waveguide + the space around it 
    stepSizeX = int( np.floor( 1.1 * waveguideSizeX / 2 / stepCount ) )
    stepSizeZ = int( np.floor( 1.1 * waveguideSizeZ / 2 / stepCount ) )
    X = bpc.getPosition(2)
    Z = bpc.getPosition(1)
    maxVal = 0
    maxX = X
    maxZ = Z

    for i in range(-stepCount, stepCount + 1, 1):
        # Scan in the X direction first
        pos = X + i * stepSizeX
        bpc.position(2, pos)
        img = cam.capture(False, True)
        val = np.max(img)
        _printDebugInfo(val, pos, Z, maxVal, maxX, maxZ)
        if val > maxVal:
            maxVal = val
            maxX = pos
    # return to max X position
    bpc.position(2, maxX)

    for i in range(-stepCount, stepCount + 1, 1):
        # Scan in the Z direction 
        pos = Z + i * stepSizeZ
        bpc.position(1, pos)
        img = cam.capture(False, True)
        val = np.max(img)
        _printDebugInfo(val, maxX, pos, maxVal, maxX, maxZ)
        if val > maxVal:
            maxVal = val
            maxZ = pos

    # position to maxX and max Z then start fine tuning
    print("------------------------")
    print("Coarse tuning complete. Current max CCD value is {} and position is at ({}, {})".format(maxVal, maxX, maxZ))
    bpc.position(1, maxZ)
    bpc.position(2, maxX)
    i = 0
    # Fine tuning moves the fiber around 20% of the waveguide (2 x 1 / 10)
    dX = int( waveguideSizeX / 10 )
    dZ = int( waveguideSizeZ / 10 )
    
    while i < iterationLimit:
        # Termination condition
        if i != 0 and maxX == bX and maxZ == bZ:
            print("*****************************************************************************")
            print("No improvement for the last completed fine tuning routine. Iteration complete. ")
            break
        print("------------------------")
        print("Iteration {} - Current maximum {} at position ({}, {})".format(i, maxVal, maxX, maxZ))
        i+=1
        # max values before each iteration
        bX = maxX
        bZ = maxZ

        # Optimise X
        for XX in range(maxX - dX, maxX + dX, fineStep):
            bpc.position(2, XX)
            img = cam.capture(False, True)
            val = np.max(img)
            _printDebugInfo(val, XX, maxZ, maxVal, maxX, maxZ)
            if val > maxVal:
                maxVal = val
                maxX = XX
        # Now return X to max position and optimise Z
        bpc.position(2, maxX)
        for ZZ in range(maxZ - dZ, maxZ + dZ, fineStep):
            bpc.position(1, ZZ)
            img = cam.capture(False, True)
            val = np.max(img)
            _printDebugInfo(val, maxX, ZZ, maxVal, maxX, maxZ)
            if val > maxVal:
                maxVal = val
                maxZ = ZZ
            
    return maxX, maxZ
    


def close():
    bpc.close()
    cam.close()


# Helper function
def _printDebugInfo(currentVal, X, Z, maxVal, maxX, maxZ):
    global __DEBUG__
    if __DEBUG__:
        print("Current position ({}, {}) and CCD max value: {}".format(X,Z, currentVal) )
        print("Maximum value of {} occurs at ({}, {}) ".format(maxVal, maxX, maxZ))

if __name__=="__main__":
    main()