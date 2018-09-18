import bpc203 as bpc
import camera as cam
import time
import numpy as np

__DEBUG__ = True

def main():
    ''' Example usage'''
    initBPC()
    # initCam()

    # To save time, you can also set the gain and shutter directly
    initCam(False, False, 3, 0.5)
    print("Starting optimisation")
    X,Y = optimise()
    input("Optimisation complete. Press enter to close the camera connection and BPC203 connection. This will not reset the positions")
    cam.close()
    bpc.closePort()
    input("Press enter to reset the system or terminate the programme now.")
    close()


def initCam(autoAdjust = True, retainCameraSettings = False, gain = -5, shutter = 0.005):
    """
        autoAdjust: If True, the function will attempt to automatically set the shutter and gain values by iteration. This will take a while
        retainCameraSettings: If True, no camera settings will be changed. The Gain and Shutter values will be left as they are, but this function checks if the camera is saturated. 
    """
    cam.printNumOfCam()
    cam.init()
    if autoAdjust:
        cam.autoAdjustShutter()
    elif retainCameraSettings == False:
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
    print("------------------------")
    print("Starting coarse optimisation. This should take only a short while. ")

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
    """ This function terminates all connections and resets the system. To preserve the position of the controller, use bpc.closePort()"""
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