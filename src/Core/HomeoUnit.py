from __future__ import division
from Core.HomeoNeedleUnit import *
from PyQt4.QtCore import QObject, SIGNAL
from Core.HomeoUniselectorAshby import *
from Core.HomeoUniselector import *
from Core.HomeoUniselectorUniformRandom import  *
from Core.HomeoConnection import *
from Helpers.General_Helper_Functions import withAllSubclasses
import numpy as np
import sys, pickle
from copy import copy
import StringIO
from Helpers.QObjectProxyEmitter import emitter
from math import  floor
from Helpers.ExceptionAndDebugClasses import hDebug


class HomeoUnitError(Exception):
    pass

class HomeoUnit(object):
    '''
    Created on Feb 19, 2013

    @author: stefano

    Homeo Unit is the fundamental element of a Homeostat.
    
    HomeoUnit represents a basic unit of Ashby's Homeostat (see Ashby's Design for a Brain, 1960, chp. 8). 
    HomeoUnit does know about its connections to other units (including itself). 

    HomeoUnit holds the  values describing the state of the unit at time t, as specified by Ashby.
    The design of this simulation of the Homeostat  was influenced by the C simulation described 
    by Alice Eldridge in "Ashby's Homeostat in Simulation," unpublished, 2002, 
    available at: http://www.informatics.sussex.ac.uk/users/alicee/NEWSITE/ecila_files/content/papers/ACEhom.pdf 

    Instance Variables:
    criticalDeviation        <Float>                Deviation of the needle from equilibrium (0 state). In Ashby's original electromechanical model, 
                                                    this value is a function of the input current applied to the magnet that operates
                                                    the needle AND the possible manual operation on the needle itself
    currentOutput            <Float>                The current  the unit outputs at time t. This value is proportional to criticalDeviation and typically between 0 and 1.
    inputConnections         <List>                 A collection of HomeoConnections storing the units the presents unit is connected to and the associated weights. 
                                                    It includes a connection to itself. 
    maxDeviation             <Float>                Maximum deviation from equilibrium
    nextDeviation            <Float>                The needle's deviation the unit will assume at at t+1. This is a function of criticalDeviation, 
                                                    of viscosity (as a dampener), and potentiometer. It is limited at both ends by maxDeviation
                                                    (i.e. maxDeviation negated < nextDeviation < maxDeviation)
    outputRange              <Dict>                 The range of the output current, keyed as low and high. Default is -1 to 1.
    viscosity                <Float>                The viscosity of the medium in which the metallic needle of the original Ashbian unit is free to move. 
                                                    It acts as a dampening agent on the change of output. Min is 0 (no effect), max is 1 (no movement)
    noise                    <Float>                Represents the **internal** noise of the  unit affecting the value of its critical deviation.
                                                    The default value is np.random.uniform(0, 0.1): a uniformly distributed value between 0 and 0.1
                                                    The actual noise on each iteration is a *normally distributed value* centered around 0,  with 
                                                    standard deviation = to 1/3 of the noise value, and proportional to the absolute magnitude of noise's value.
                                                    In other words, noise is modeled as a kind of "static" distortion of fixed max magnitude
    potentiometer             <Float>               As per Ashby's implementation, it represents the weight of the unit's connection to itself. 
                                                    In our implementation it is always identical to the weight of a unit's 
                                                    first connection,---Check Design for a Brain, chp.8  for details
                                                    Notice that the polarity of the self-connection (the switch, in Ashby terminology, which we follow)
                                                    is **not** held in an instance variable. In our implementation it is always identical 
                                                    to the polarity of a unit's first connection, that is: self.inputConnections[0].switch,
    time                       <Integer>            The internal tick counter
    uniselectorTime            <Integer>            The internal tick counter for activation of the uniselector
    uniselectorTimeInterval    <Integer>            The number of ticks that specifies how often to check that the output is in range and eventually activate uniselector
    uniselector                <HomeoUniselector>   The uniselector that can modify the weights of input values coming from other units
    uniselectorActive          <Boolean>            Whether the uniselector mechanism is  active or not
    uniselectorActivated       <Integer>            Whether the Uniselector has just been activated
    needleCompMethod           <String>              Whether the unit's needle's displacement depends of the sum of its input, 
                                                    or on the ratio between the sum of the inputs and the maxDeviation. 
                                                    Possible values are 'linear' and 'proportional', default is 'linear'.
    inputTorque                <Float>              It represents the input force derived from the weighed sum of the inputs (as computed by computeTorque)
    active                     <String>             Whether the unit is active or not (on or off)
    status                     <String>             Active, Non Active, or other possible status
    debugMode                  <Boolean>            It control whether the running methods print out debugging information
    showUniselectorAction      <Boolean>            It controls whether the running methods print out when the uniselector kicks into action
    currentVelocity            <Float>              The current velocity of the needle moving in the trough
    needleUnit                 <HomeoNeedleUnit>    Holds an instance of HomeoNeedleUnit, the class containing the parameters 
                                                    of the needle used by the unit (mass, area, etc.)
    _physicalParameters        <Dict>               A dictionary containing equivalence factors between the simulation units and real physical parameters


    A HomeoUnit knows how to:

    - compute its next output on the basis of the input (received through connections stored in inputConnections) and its internal parameters
    - add a connection with a given unit as the incoming unit
    - periodically check that its outputValue has not become critical (outside the acceptable range) 
    - ask the uniselector to reset the weight of its inputConnections
    - print a description of itself with the values of all its parameters
     '''

    #===========================================================================
    # '''CLASS CONSTANTS'''
    #===========================================================================

    "The unit's output range is by default -1  to 1 to express the proportion of the needle's deviation" 
    unitRange = {'high':1,'low':-1}               

    "DefaultParameters is a class variable holding the  default values of all the various parameters of future created units."
    DefaultParameters  = dict(viscosity = 0,
                              maxDeviation=10,
                              outputRange = unitRange,
                              noise = 0,                        # Initially set noise on self to 0, will change to a random value later 
                              potentiometer= 1,
                              time = 0,
                              switch = -1,                      # This value is used to control the polarity of a unit's self-connection
                              inputValue=0,
                              uniselectorTime= 0,               # How often the uniselector checks the thresholds, in number of ticks
                              uniselectorTimeInterval = 100,
                              needleCompMethod= 'linear',       # switches between linear and proportional computation of displacement
                              uniselectorActive = True,
                              uniselectorActivated = 0,
                              maxViscosity = (10**1),            # Used to set the initial random values of viscosity and to validate user input in forms 
                              critThreshold = 0.9,               # the ratio of max deviation beyond which a unit's essential variable's value  is considered critical
                              mass = 100,                        # the mass of the needle unit, representing the inertia of the unit. A low value will make it very unstable
                              maxUniselectorTimeInterval = 1000, # Used in GA settings to pick a random value
                              maxTheoreticalDeviation = 1000,    # Used in GA settings to pick a random value
                              minTheoreticalDeviation = 0.1,     # Used in GA settings to pick a random value
                              maxMass = 10000,                   # Used in GA settings to pick a random value
                              minMass = 10)                      # Used in GA settings to pick a random value
    
    '''The value of the precision need for a correct working of PyQt sliders (which only allow integers). 
    Must be equal to same parameter set in HomeoStandardGui>>setupHomeostatGuiUnitsStandardCritDevSlider'''
    precision = 10**5  
    
    allNames = set()        # set of units' unique names
        
    #===========================================================================
    #  END OF CLASS CONSTANTS 
    #===========================================================================
    #===========================================================================
    # CLASS METHODS 
    #===========================================================================
    
    @classmethod    
    def readFrom(self,filename):
        '''This is a class method that creates a new HomeoUnit instance from filename'''
        fileIn = open(filename, 'r')
        unpickler = pickle.Unpickler(fileIn)
        newHomeoUnit = unpickler.load()
        fileIn.close()
        return newHomeoUnit
    
    @classmethod
    def clearNames(cls):
        '''Clear the set of HomeoUnits' names'''
        HomeoUnit.allNames = set()
    
    @classmethod
    def uniselectorTimeIntervalFromWeight(cls,uniselParam):
        '''Convert a GA parameter in the [0,1) range to a valid uniselectorInterval value'''
        return uniselParam * HomeoUnit.DefaultParameters['maxUniselectorTimeInterval'] 
    
    @classmethod
    def viscosityfromWeight(cls,viscParam):
        '''Convert a GA parameter in the [0,1) range into a viscosity value'''        
        return viscParam * HomeoUnit.DefaultParameters['maxViscosity']
    
    @classmethod
    def maxDeviationFromWeight(cls,maxDevParam):
        '''Convert a GA parameter in the [0,1) range to a valid maxDeviation value'''
        return ((HomeoUnit.DefaultParameters['maxTheoreticalDeviation'] - HomeoUnit.DefaultParameters['minTheoreticalDeviation']) * maxDevParam) + HomeoUnit.DefaultParameters['minTheoreticalDeviation']
    
    @classmethod    
    def massFromWeight(cls,massParam):
        '''Convert a GA parameter in the [0,1) range to a valid mass value'''
        return ((HomeoUnit.DefaultParameters['maxMass']-HomeoUnit.DefaultParameters['minMass']) * massParam) + HomeoUnit.DefaultParameters['minMass']

    #===========================================================================
    #  INITIALIZATIONS AND GETTERS, SETTERS, PROPERTIES
    #===========================================================================
    def __init__(self):

        "creates the connection collection and connects the unit to itself in manual mode with a negative feedback"
        self.initializeBasicParameters()
        self._inputConnections = []
        self.setDefaultSelfConnection()
        self.unit_essential_parameters = 4
        hDebug('unit', ("At time: %d unit: %s dev: %f output: %f" %(self.time, self.name, self.criticalDeviation, self._currentOutput)))


        
    def initializeBasicParameters(self):
        '''Reset uniselector to its default parameters, but do not change its type'''
        '''
        Initialize the HomeoUnit with the default parameters found in the Class variable 
        DefaultParameters. Assign a random but unique name and sets the output to 
        some value around 0, i.e. at equilibrium.
        These values are supposed to be overridden in normal practice, because the values are set by the simulation 
        (an instance of HomeoSimulation or by the graphic interface)
        '''
        self._showUniselectorAction = False
        self._viscosity = HomeoUnit.DefaultParameters['viscosity']
        self._maxDeviation = HomeoUnit.DefaultParameters['maxDeviation']     #set the critical deviation at time 0 to 0."
        self._outputRange = HomeoUnit.DefaultParameters['outputRange']
        self._noise = HomeoUnit.DefaultParameters['noise']
        self._potentiometer = HomeoUnit.DefaultParameters['potentiometer']
        self._time = HomeoUnit.DefaultParameters['time']
        self._uniselectorTime = HomeoUnit.DefaultParameters['uniselectorTime']
        self._uniselectorTimeInterval = HomeoUnit.DefaultParameters['uniselectorTimeInterval']
        self._needleCompMethod = HomeoUnit.DefaultParameters['needleCompMethod']
        self._uniselectorActive = HomeoUnit.DefaultParameters['uniselectorActive']
        self._uniselectorActivated = HomeoUnit.DefaultParameters['uniselectorActivated']
        self._critThreshold = HomeoUnit.DefaultParameters['critThreshold']
        
        '''A new unit is turned off, hence its velocity is 0, and 
          its criticalDeviation and nextDeviation are 0, and
          its inputTorque (from other units) is 0, and
          its currentOutput is 0'''
        self._currentVelocity = 0 
        self._criticalDeviation = 0
        self._nextDeviation = 0
        self._inputTorque = 0
        self._currentOutput = 0 
                


        "sets the correspondence between the simulation units and real physical units"
        self._physicalParameters=dict(timeEquivalence = 1,            # 1 simulation tick corresponds to 1 second of physical time"
                                      lengthEquivalence = 0.01,       # 1 unit of displacement corresponds to 1 cm (expressed in meters)"
                                      massEquivalence = 0.001)        # 1 unit of mass equals one gram, or 0.001 kg"
    
        "give the unit  a default name"
        try:
            HomeoUnit.allNames.discard(self.name)
        except AttributeError:
            self._name = None
        self.setDefaultName()

        'Set the mass of the needle unit. Its value must be rather high (~= 1000) to avoid instability)'
        self._needleUnit = HomeoNeedleUnit()
        self.mass = HomeoUnit.DefaultParameters['mass']

        
        "turn the unit on"
        self._status= 'Active'
#        sys.stderr.write("At time %u unit %s status is in the ivar is: %s in the property is: %s and in the function is: %s\n" % (self.time, self.name, self._status, self.status, self.isActive()))
        self._debugMode = False

        "sets default uniselector settings."
        self.setDefaultUniselectorSettings()
                
        "generates a random output to set the unit close to equilibrium"
        #self.setDefaultOutputAndDeviation()
        
        
    
    def initializeUniselector(self):
        '''Reset uniselector to its default parameters, but do not change its type'''
        self.uniselector.setDefaults()

   #============================================================================
   # GA-methods for Genetic algorithms simulations
   #============================================================================
        
    def initialize_GA(self, essent_params):                
        '''
        The initialize_GA method sets the unit's essential parameters.
        essent_params is a list containing numeric values 
        for the unit's essential parameters, which must be passed to the class in this order:
        
        1 Mass
        2 Viscosity
        3 UniselectorTiming (integer)
        4 maxDeviation (integer)
        
        (the potentiometer (aka self-weight) is also an essential parameter, but it is set when connections are set))
        
        All parameters are in the [0,1) interval and are scaled appropriately by
        the respective functions.
        
        Subclasses of HomeoUnit may override this method and add parameters
        '''
        if len(essent_params) <> self.unit_essential_parameters:
            raise (HomeoUnitError, "The number of parameters needed to initialize the unit is incorrect.")
         
        self.mass = HomeoUnit.massFromWeight(essent_params[0])
        self.viscosity = HomeoUnit.viscosityfromWeight(essent_params[1])
        self.uniselectorTimeInterval = HomeoUnit.uniselectorTimeIntervalFromWeight(essent_params[2])
        self.maxDeviation=HomeoUnit.maxDeviationFromWeight(essent_params[3])                               
    
    #===============================================================================   
        

    
    def allValuesChanged(self):
        """
            Send out signals corresponding to changes for all the relevant values of a unit,
            so the GUI (if any) can update itself
        """
        'Name'
        QObject.emit(emitter(self), SIGNAL("nameChanged"),self._name)
        QObject.emit(emitter(self), SIGNAL("nameChangedLineEdit"),self._name)


        'Active'
        QObject.emit(emitter(self), SIGNAL('unitActiveIndexchanged'), ("Active", "Non Active").index(self.status))
        
        'Output'
        QObject.emit(emitter(self), SIGNAL("currentOutputChanged"), self._currentOutput)
        QObject.emit(emitter(self), SIGNAL("currentOutputChangedLineEdit"), str(round(self._currentOutput, 5)))
        
        'Input'
        QObject.emit(emitter(self), SIGNAL("inputTorqueChanged"), self._inputTorque)
        QObject.emit(emitter(self), SIGNAL("inputTorqueChangedLineEdit"), str(round(self._inputTorque, 5)))
        
        'Mass'
        QObject.emit(emitter(self), SIGNAL('massChanged'),  self.mass)
        QObject.emit(emitter(self), SIGNAL('massChangedLineEdit'), str(int( self.mass)))
        
        'Switch'
        QObject.emit(emitter(self), SIGNAL('switchChanged'), self._switch)
        QObject.emit(emitter(self), SIGNAL('switchChangedLineEdit'), str(int(self._switch)))

        
        'Potentiometer'
        QObject.emit(emitter(self), SIGNAL('potentiometerDeviationChanged'), self._potentiometer)
        QObject.emit(emitter(self), SIGNAL('potentiometerChangedLineEdit'), str(round(self._potentiometer, 4)))

        
        'Viscosity'
        QObject.emit(emitter(self), SIGNAL('viscosityChanged'), self._viscosity)
        QObject.emit(emitter(self), SIGNAL('viscosityChangedLineEdit'), str(round(self._viscosity, 4)))

        
        'Noise'
        QObject.emit(emitter(self), SIGNAL('noiseChanged'), self._noise)
        QObject.emit(emitter(self), SIGNAL('noiseChangedLineEdit'), str(round(self._noise, 4)))
        
        'SelfConnNoise'

        
        
        'Critical deviation, including min and max'        
        QObject.emit(emitter(self), SIGNAL('criticalDeviationChanged'), self._criticalDeviation)
        QObject.emit(emitter(self), SIGNAL('criticalDeviationChangedLineEdit'), str(round(self._criticalDeviation, 5)))
        scaledValueToEmit = int(floor(self._criticalDeviation * HomeoUnit.precision))
        QObject.emit(emitter(self), SIGNAL('criticalDeviationScaledChanged(int)'), scaledValueToEmit)
        
        QObject.emit(emitter(self), SIGNAL('minDeviationChanged'), - self._maxDeviation)
        QObject.emit(emitter(self), SIGNAL('minDeviationChangedLineEdit'), str(int(- self._maxDeviation)))
        scaledValueToEmit = int(floor(- self._maxDeviation * HomeoUnit.precision))
        QObject.emit(emitter(self), SIGNAL('minDeviationScaledChanged)'), scaledValueToEmit)
        QObject.emit(emitter(self), SIGNAL('deviationRangeChanged'), self.minDeviation, self.maxDeviation)

        QObject.emit(emitter(self), SIGNAL('maxDeviationChanged'), self._maxDeviation)
        QObject.emit(emitter(self), SIGNAL('maxDeviationChangedLineEdit'), str(int(self._maxDeviation)))
        scaledValueToEmit = int(floor(self._maxDeviation * HomeoUnit.precision))
        QObject.emit(emitter(self), SIGNAL('maxDeviationScaledChanged)'),scaledValueToEmit)
        QObject.emit(emitter(self), SIGNAL('deviationRangeChanged'), self.minDeviation, self.maxDeviation)

        'Uniselector parameters'
        QObject.emit(emitter(self), SIGNAL("uniselectorTimeIntervalChangedLineEdit"), str(int(self.uniselectorTimeInterval)))
        QObject.emit(emitter(self), SIGNAL("unitUniselOnChanged"), self.uniselectorActive)
        
 
    
    "properties with setter and getter methods for external access"
    
    def getCriticalDeviation(self):
        return self._criticalDeviation
    
    def setCriticalDeviation(self,aValue):       
        try:
            aValue = float(aValue)

#            '''Ugly hack to convert the magnified integer value we received from the slider 
#               into a float within Deviation range'''
#            if ((not -self.maxDeviation <= aValue <= self.maxDeviation) and 
#                    (-self.maxDeviation <= aValue/HomeoUnit.precision <= self.maxDeviation)):
#                    self._criticalDeviation = self.clipDeviation(aValue/HomeoUnit.precision)
#            else:
#                self._criticalDeviation = self.clipDeviation(aValue)
            self._criticalDeviation = self.clipDeviation(aValue)
              
            QObject.emit(emitter(self), SIGNAL('criticalDeviationChanged'), self._criticalDeviation)
            QObject.emit(emitter(self), SIGNAL('criticalDeviationChangedLineEdit'), str(round(self._criticalDeviation, 5)))
            scaledValueToEmit = int(floor(self._criticalDeviation * HomeoUnit.precision))
            QObject.emit(emitter(self), SIGNAL('criticalDeviationScaledChanged(int)'), scaledValueToEmit)

#            sys.stderr.write('Unit %s just emitted the signal criticalDeviationScaledChanged with value %s\n' 
#                             % (self.name, int(floor(self._criticalDeviation * HomeoUnit.precision))))
#            sys.stderr.write('Unit %s just emitted the signal criticalDeviationChanged with value %s\n' 
#                             % (self.name, self._criticalDeviation))
        except ValueError:
            sys.stderr.write("Tried to assign a non-numeric value to unit %s's Critical Deviation. The value was: %s\n" % (self.name, aValue))
    
    
    criticalDeviation = property(fget = lambda self: self.getCriticalDeviation(),
                                 fset = lambda self, value: self.setCriticalDeviation(value))
    
    def setCriticalDeviationFromSlider(self, aValue):
        '''Helper function to convert the magnified integer value 
        coming from Qt int only sliders into the needed float Value'''
        self.criticalDeviation = np.clip((aValue/HomeoUnit.precision), self.minDeviation, self.maxDeviation)
        QObject.emit(emitter(self), SIGNAL('criticalDeviationChanged'), self._criticalDeviation)

    
    def getNextDeviation(self):
        return self._nextDeviation
    
    def setNextDeviation(self,aValue):       
        self._nextDeviation = aValue
    
    nextDeviation = property(fget = lambda self: self.getNextDeviation(),
                                 fset = lambda self, value: self.setNextDeviation(value))

    def setViscosity(self, aValue):
        ''''Viscosity must be between 0 (zero effect)
        and maxViscosity (set in class's default parameters)'''
        
        try:
            aValue = float(aValue)
            if aValue < 0 or aValue > HomeoUnit.DefaultParameters['maxViscosity']:
                sys.stderr.write("The current value for maxViscosity is %f . Trying to set it to %f\n" % (HomeoUnit.DefaultParameters['maxViscosity'], aValue))  
                raise(HomeoUnitError, "The value of viscosity must always be between 0 and maxViscosity (included)")
            else: 
                self._viscosity = aValue
        except ValueError:
            sys.stderr.write("Tried to assign a non-numeric value to unit  %s's Viscosity. The value was: %s\n" % (self.name, aValue))
        finally:
            QObject.emit(emitter(self), SIGNAL('viscosityChanged'), self._viscosity)
            QObject.emit(emitter(self), SIGNAL('viscosityChangedLineEdit'), str(round(self._viscosity, 4)))


        
        
    def getViscosity(self):
        return self._viscosity
    
    viscosity = property(fget = lambda self: self.getViscosity(),
                         fset = lambda self, value: self.setViscosity(value))
    
    def setNeedleUnit(self, aValue):
        self._needleUnit = aValue
        
    def getNeedleUnit(self):
        return self._needleUnit
    
    needleUnit = property(fget = lambda self: self.getNeedleUnit(),
                         fset = lambda self, value: self.setNeedleUnit(value))

    def setPotentiometer(self, aValue):
        '''Changing the value of the potentiometer affects 
           the unit's connection to itself (which is always at position 0
           in the inputConnections list)'''
        try:
            self._potentiometer = float(aValue)
            self._inputConnections[0].newWeight(float(aValue)*self._inputConnections[0].switch) # Keep the old sign
        except ValueError:
            sys.stderr.write("Tried to assign a non-numeric value to unit  %s's Potentiometer. The value was: %s\n" % (self.name, aValue))
        finally:
            QObject.emit(emitter(self), SIGNAL('potentiometerChanged'), self._potentiometer)
            QObject.emit(emitter(self), SIGNAL('potentiometerChangedLineEdit'), str(round(self._potentiometer, 4)))

    def getPotentiometer(self):
        return self._potentiometer
    potentiometer = property(fget = lambda self: self.getPotentiometer(),
                             fset = lambda self, value: self.setPotentiometer(value))  
    
    def setNoise(self, aValue):
        '''Set the value of the unit's internal noise. 
            As noise must always be between 0 and 1,
            clip it otherwise'''
        try:
            self._noise = np.clip(float(aValue), 0,1)
        except ValueError:
            sys.stderr.write("Tried to assign a non-numeric value to unit  %s's Noise. The value was: %s\n" % (self.name, aValue))
        finally:
            QObject.emit(emitter(self), SIGNAL('noiseChanged'), self._noise)
            QObject.emit(emitter(self), SIGNAL('noiseChangedLineEdit'), str(round(self._noise, 4)))

                    
    def getNoise(self):
        return self._noise
    noise = property(fget = lambda self: self.getNoise(),
                     fset = lambda self, value: self.setNoise(value))  
        
    def setTime(self, aValue):
        self._time = aValue
    def getTime(self):
        return self._time
    time = property(fget = lambda self: self.getTime(),
                    fset = lambda self, value: self.setTime(value))  
    
    def setUniselectorTime(self, aValue):
        self._uniselectorTime = aValue
    def getUniselectorTime(self):
        return self._uniselectorTime
    uniselectorTime = property(fget = lambda self: self.getUniselectorTime(),
                               fset = lambda self, value: self.setUniselectorTime(value))  
    
    def setNeedleCompMethod(self, aString):
        self._needleCompMethod = aString
    def getNeedleCompMethod(self):
        return self._needleCompMethod
    
    needleCompMethod = property(fget = lambda self: self.getNeedleCompMethod(),
                                fset = lambda self, value: self.setNeedleCompMethod(value))  
        
    def setMaxDeviation(self,aNumber):
        '''Max deviation is always positive, 
           because the unit's deviation is centered around 0. 
           Ignore negative numbers'''
    
        try:
            aNumber = float(aNumber)
            if aNumber > 0: 
                self._maxDeviation = aNumber
                self.minDeviation = -aNumber
            else:
                print "THE VALUE YOU TRIED TO USE FOR MAXDEVIATION WAS: ", aNumber
                raise(HomeoUnitError, "The value of MaxDeviation must always be positive")
        except ValueError:
            sys.stderr.write('Unit %s tried to  assign a non-numeric value to maxDeviation. Value was %s\n' % (self.name, aNumber))
        finally:
            QObject.emit(emitter(self), SIGNAL('maxDeviationChanged'), self._maxDeviation)
            QObject.emit(emitter(self), SIGNAL('maxDeviationChangedLineEdit'), str(int(self._maxDeviation)))
            scaledValueToEmit = int(floor(self._maxDeviation * HomeoUnit.precision))
            QObject.emit(emitter(self), SIGNAL('maxDeviationScaledChanged)'),scaledValueToEmit)
            QObject.emit(emitter(self), SIGNAL('deviationRangeChanged'), self.minDeviation, self.maxDeviation)
#            sys.stderr.write('%s emitted signals maxDeviation with value %f, MinDeviation changed to %f\n' % (self._name, self._maxDeviation, self.minDeviation))
            
    def getMaxDeviation(self):
        return self._maxDeviation
    maxDeviation = property(fget = lambda self: self.getMaxDeviation(),
                            fset = lambda self, value: self.setMaxDeviation(value))  
    
    def setOutputRange(self, minOut,maxOut):
        aDict = {'low':minOut, 'high':maxOut}
        self._outputRange = aDict
    
    def getOutputRange(self):
        return self._outputRange
    outputRange = property(fget = lambda self: self.getOutputRange(),
                           fset = lambda self, minOut, maxOut: self.setOutputRange(minOut,maxOut))  
    def setUniselectorActive(self,aBoolean):
        self._uniselectorActive = aBoolean
    def getUniselectorActive(self):
        return self._uniselectorActive
    uniselectorActive = property(fget = lambda self: self.getUniselectorActive(),
                                 fset = lambda self, value: self.setUniselectorActive(value))  
    
    def toggleUniselectorActive(self):
        'Toggle state of uniselector'
        self._uniselectorActive = not self._uniselectorActive
    
    def setUniselectorActivated(self,aBoolean):
        self._uniselectorActivated = aBoolean
    def getUniselectorActivated(self):
        return self._uniselectorActivated
    uniselectorActivated = property(fget = lambda self: self.getUniselectorActivated(),
                                 fset = lambda self, value: self.setUniselectorActivated(value))  

    def setUniselectorTimeInterval(self,aValue):
        try:
            self._uniselectorTimeInterval = abs(int(aValue))
        except ValueError:
            sys.stderr.write('Unit %s tried to assign a non-numeric value to the Uniselector Time Interval. Value is %s\n' % (self.name, aValue))
        finally:
            QObject.emit(emitter(self), SIGNAL('uniselectorTimeIntervalChanged'), self._uniselectorTimeInterval)
            QObject.emit(emitter(self), SIGNAL('uniselectorTimeIntervalChangedLineEdit'), str(self._uniselectorTimeInterval))
#            sys.stderr.write('%s emitted signals UniselectorTimeIntervalChanged with value %f\n' 
#                             % (self._name,self._uniselectorTimeInterval))
            
    def getUniselectorTimeInterval(self):
        return self._uniselectorTimeInterval
    uniselectorTimeInterval = property(fget = lambda self: self.getUniselectorTimeInterval(),
                                       fset = lambda self, value: self.setUniselectorTimeInterval(value))  

#    def setActive(self, aBoolean):
#        if aBoolean == True or aBoolean == False:
#            self._active = aBoolean
#        else:
#            raise HomeoUnitError("The value of instance variable active can only be a Boolean") 
#        
#    def getActive(self):
#        return self._active
#    
#    active = property(fget = lambda self: self.getActive(),
#                      fset = lambda self, aBoolean: self.setActive(aBoolean))
                                
    def getCurrentOutput(self):
        return self._currentOutput
        
    def setCurrentOutput(self, aValue):
        self._currentOutput = aValue
        #print "In setcurrentOutput at time: %d. Value passed: %f unit: %s dev: %f output: %f" %(self.time, aValue, self.name, self.criticalDeviation, self._currentOutput)

        QObject.emit(emitter(self), SIGNAL("currentOutputChanged"), self._currentOutput)
        QObject.emit(emitter(self), SIGNAL("currentOutputChangedLineEdit"), str(round(self._currentOutput, 5)))
#        sys.stderr.write( 'Unit %s just emitted the signal currentOutputChanged \n' % self.name)   
        "For testing"
        if self._debugMode == True:
            sys.stderr.write(self.name + " curr output: " + str(self._currentOutput)+'\n')

    currentOutput = property(fget = lambda self: self.getCurrentOutput(),
                             fset = lambda self, aBoolean: self.setCurrentOutput(aBoolean))
  
    def getHighRange(self):
        return self.outputRange['high']

    def setHighRange(self,aValue):
        self.outputRange['high'] =  aValue

    highRange = property(fget = lambda self: self.getHighRange(),
                         fset = lambda self, aValue: self.setHighRange(aValue))
    
    def getLowRange(self):
        return self.outputRange['low']

    def setLowRange(self,aValue):
        self.outputRange['low'] =  aValue

    lowRange = property(fget = lambda self: self.getLowRange(),
                         fset = lambda self, aValue: self.setLowRange(aValue))

    def getInputConnections(self):
        return self._inputConnections
    
    def setInputConnections(self, aList):
        self._inputConnections = aList
        
    inputConnections = property(fget = lambda self: self.getInputConnections(),
                                fset = lambda self, aList: self.setInputConnections(self, aList))

    def getInputTorque(self):
        return self._inputTorque

    def setInputTorque(self,aValue):
        self._inputTorque = aValue
        QObject.emit(emitter(self), SIGNAL("inputTorqueChanged"), self._inputTorque)
        QObject.emit(emitter(self), SIGNAL("inputTorqueChangedLineEdit"), str(round(self._inputTorque, 5)))


    inputTorque = property(fget = lambda self: self.getInputTorque(),
                           fset = lambda self,aValue: self.setInputTorque(aValue))

    def getCurrentVelocity(self):
        return self._currentVelocity

    def setCurrentVelocity(self, aValue):
        self._currentVelocity = aValue
    
    currentVelocity = property(fget = lambda self: self.getCurrentVelocity(),
                              fset = lambda self, aValue: self.setCurrentVelocity(aValue)) 

    def setSwitch(self,aNumber):
        '''Set the polarity of the unit's self-connection. 
           aNumber must be either -1 or +1, otherwise method 
           raises an exception.
           
           The switch can only be set by changing the sign of the weight
           of the the unit's connection to itself (which is always 
           at location 0 in the inputConnections collection)'''

        acceptedValues = (-1,1)
        oldWeight = self.inputConnections[0].weight
        oldSwitch = self.inputConnections[0].switch
        oldUnitSwitch = self.switch
        
        try:
            if int(aNumber) in acceptedValues:
                newWeight = abs(oldWeight) * int(aNumber)
                self.inputConnections[0].newWeight(newWeight)
                self._switch = int(aNumber)
#                sys.stderr.write("Unit %s's new weight is %f: with switch equal to %f. The value passed from the GUI was %f . \nThe old weight was %f and the old switch was %f, and the old unit's switch was %f\n" 
#                                 % (self.name, self.inputConnections[0].weight, self.switch, int(aNumber), oldWeight, oldSwitch, oldUnitSwitch))
            else: 
                raise  ConnectionError
        except ValueError:
            sys.stderr.write("Tried to assign a non-numeric value to unit  %s's Switch. The value was: %s\n" % (self.name, aNumber))
        finally:
            QObject.emit(emitter(self), SIGNAL('switchChanged'), self._switch)
            QObject.emit(emitter(self), SIGNAL('switchChangedLineEdit'), str(int(self._switch)))
            QObject.emit(emitter(self.inputConnections[0]), SIGNAL('switchChanged'),self._switch) 
#            sys.stderr.write('%s emitted signals switchChanged with value %f the object emitting the signal was %s\n' % (self._name, self._switch, emitter(self.inputConnections[0])))
            
    
    def getSwitch(self):
        return self.inputConnections[0].switch
    
    switch = property(fget = lambda self: self.getSwitch(),
                      fset = lambda self, aValue: self.setSwitch(aValue))
    
    def getMinDeviation(self):
        '''Deviation is always centered around 0. 
           Min deviation is less than 0 and equal to maxDeviation negated'''

        return - self.maxDeviation

    def setMinDeviation(self,aNumber):
        '''Deviation is always centered around 0. 
           Min deviation must be less than 0 and equal to maxDeviation negated. 
           If we change the minimum we must change the maximum as well'''        
                
        try:
            aNumber = float(aNumber)
            if aNumber < 0 and self.maxDeviation <> - aNumber: 
                self.maxDeviation = - aNumber
        except ValueError:
            sys.stderr.write("Unit %s tried to assign a non numeric value to  minDeviation. Value was %s\n" % (self.name, aNumber))
        finally:
#            QObject.emit(emitter(self), SIGNAL('maxDeviationChanged'), self._maxDeviation)
#            QObject.emit(emitter(self), SIGNAL('maxDeviationChangedLineEdit'), str(int(self._maxDeviation)))
            QObject.emit(emitter(self), SIGNAL('minDeviationChanged'), - self._maxDeviation)
            QObject.emit(emitter(self), SIGNAL('minDeviationChangedLineEdit'), str(int(- self._maxDeviation)))
            scaledValueToEmit = int(floor(- self._maxDeviation * HomeoUnit.precision))
            QObject.emit(emitter(self), SIGNAL('minDeviationScaledChanged)'), scaledValueToEmit)
            QObject.emit(emitter(self), SIGNAL('deviationRangeChanged'), self.minDeviation, self.maxDeviation)
#            sys.stderr.write('%s emitted signals maxDeviation with value %f, MinDeviation changed to %f\n' % (self._name, self._maxDeviation, - self._maxDeviation))
 
    
    minDeviation = property(fget = lambda self: self.getMinDeviation(),
                            fset= lambda self, aValue: self.setMinDeviation(aValue))
    
    def getStatus(self):
        return self._status

    def setStatus(self,aValue):
        self._status = aValue

    status = property(fget = lambda self: self.getStatus(),
                           fset = lambda self,aValue: self.setStatus(aValue))
    
    
    def getUniselector(self):
        return self._uniselector
    
    def setUniselector(self,aUniselectorInstance):
        '''Set the uniselector and check that it is a valid one'''
        
        if HomeoUniselector.includesType(aUniselectorInstance.__class__.__name__): 
            self._uniselector = aUniselectorInstance
            self.uniselectorTime = 0
    
    uniselector = property(fget = lambda self: self.getUniselector(),
                           fset = lambda self, aString: self.setUniselector(aString))
    
    def getCritThreshold(self):
        return self._critThreshold
    
    def setCritThreshold(self,aValue):
        "Must be > 0 and  < 1. Raise error otherwise"
        if aValue > 0 and aValue < 1:
            self._critThreshold = aValue
        else:
            raise(HomeoUnitError, "The value of the critical threshold must be between 0 and 1 excluded")
    
    critThreshold = property(fget = lambda self: self.getCritThreshold(),
                            fset = lambda self, aValue: self.setCritThreshold(aValue))
    
    def getName(self):
        return self._name
    
    def setName(self, aString):
        "aString must be a new name not present in HomeoUnit.allNames"

        if aString not in HomeoUnit.allNames: 
            HomeoUnit.allNames.discard(self._name)
            self._name = aString
            HomeoUnit.allNames.add(aString)
            QObject.emit(emitter(self), SIGNAL("nameChanged"),self._name)
        else:
            raise(HomeoUnitError, "The name %s exists already" % aString)
    
    name = property(fget = lambda self: self.getName(),
                    fset = lambda self, aString: self.setName(aString))  
 
    def activateUnit(self):
        self._status = 'Active'

    def toggleStatus(self):
        if self._status == 'Active':
            self._status = 'Non Active'
        else:
            self._status = 'Active'
            
    def getDebugMode(self):
        return self._debugMode
    
    def setDebugMode(self,aValue):
        '''Do nothing. _debugMode is set
         with the toggleDebugMode method'''
        pass
    
    debugMode = property(fget = lambda self: self.getDebugMode(),
                           fset = lambda self,aValue: self.setDebugMode(aValue))
    
    def getShowUniselectorAction(self):
        return self._showUniselectorAction
    
    def setShowUniselectorAction(self, aValue):
        '''Do nothing. _showUniselectorAction is set
         with the toggleShowUniselectorAction method'''
        
    'Convenience property to get to the mass stored in the needleUnit'
    def getMass(self):
        return self._needleUnit.mass
        
    def setMass(self,aValue):
        try:
            self._needleUnit.mass = float(aValue)
        except ValueError:
            sys.stderr.write("Tried to assign a non-numeric value to unit  %s's Mass. The value was: %s\n" % (self.name, aValue))
        finally:
            QObject.emit(emitter(self), SIGNAL('massChanged'),  self.mass)
            QObject.emit(emitter(self), SIGNAL('massChangedLineEdit'), str(int( self.mass)))
#            sys.stderr.write('%s emitted signals mass    Changed with value %f\n' % (self._name, self.mass))
            
        
    mass = property(fget = lambda self: self.getMass(),
                    fset = lambda self, value: self.setMass(value))

    
    #===========================================================================
    #  End of setter and getter methods"
    #===========================================================================

    def setDefaultSelfConnection(self):
        '''
        Connect the unit to itself in manual mode with the default feedback and low random noise
        Update value of self.switch
        '''
        self_connection_noise = np.random.uniform(0,0.05)
        self.addConnectionUnitWeightPolarityNoiseState(self,self.potentiometer,HomeoUnit.DefaultParameters['switch'],self_connection_noise,'manual')
        

#===============================================================================
#   
#    def setNewName(self):
#        pass
# 
#    def setDefaultOutputAndConnections(self):
#        pass
#===============================================================================

    def setDefaultUniselectorSettings(self):
        "set default uniselector settings"

        try:
            self.uniselector.setDefaults()
        except AttributeError:
            self.uniselector = HomeoUniselectorAshby()
        finally:
            self.uniselectorActive = True
    
    def setDefaultName(self):
        '''Assign a default unique name to the unit with the help of an auxiliary method'''
        self.name = self.produceNewName()
        
    def setDefaultOutputAndDeviation(self):

        randOutput = np.random.uniform(0,0.5)       #generates a random output to set the unit close to equilibrium"
        self.currentOutput = randOutput

        "set the critical deviation at time 0 to 0."
        self.criticalDeviation = 0

    def randomizeAllConnectionValues(self):
        '''Reset the weight, switch, and noise of all connections to random values 
           (see HomeoConnection for details),
           including the self connection of the unit to itself.  
           Do not change the uniselector operation.
           Reset Input Torque to 0'''

        for conn in self._inputConnections:  
#                if not conn.incomingUnit == self:
                conn.randomizeConnectionValues()
        self.inputTorque = 0
        
        
    def changeUniselectorType(self, aUniselClassName):
        "Change the unit's uniselector to a new instance of aUniselClassName (also abbreviated)"
        validUniselTypeNames = [x.__name__ for x in HomeoUniselector.__subclasses__()]
        if not "HomeoUniselector" in aUniselClassName:
            aUniselClassName = str("HomeoUniselector" + aUniselClassName) # PyQt returns QString, which will fail  as keys of globals()
        if aUniselClassName in validUniselTypeNames:
            uniSelInstance = globals()[aUniselClassName]()
            self.uniselector = uniSelInstance
        
    #===========================================================================
    # TESTING METHODS
    #===========================================================================
    def isActive(self):
        if self._status == 'Active':
            return True
        else:
            return False
    
    def isConnectedTo(self,aHomeoUnit):
        '''Test whether there is a connection coming from aHomeoUnit'''
            
        connUnits = [x.incomingUnit for x in self._inputConnections]
        return (aHomeoUnit in connUnits)


    def sameAs(self,aHomeoUnit):
        '''Test whether two units are the same, by checking (and delegating the actual checks):
               1. name and other first-level parameters (potentiometer, switch, etcetera
               2. the number of connections
               3. the parameters of each  connection
               4. the names of the connected units'''

        return self.sameFirstLevelParamsAs(aHomeoUnit)  and \
               self.sameConnectionsAs(aHomeoUnit)
               
    def sameFirstLevelParamsAs(self,aHomeoUnit):
        '''Checks whether the first level parameters of two units 
            (i.e. not the connections) are the same.
            Does not include dynamic parameters (output, currentOutput, 
            nextDeviation, criticalDeviation, time, uniselectorTime, inputTorque).
            Do not check uniselector transition tables, only kind of device'''

        return (self.name ==  aHomeoUnit.name and
                self.viscosity == aHomeoUnit.viscosity and 
                self.maxDeviation == aHomeoUnit.maxDeviation and 
                self.outputRange['high'] == aHomeoUnit.outputRange['high'] and 
                self.outputRange['low'] == aHomeoUnit.outputRange['low'] and 
                self.noise == aHomeoUnit.noise and 
                self.potentiometer == aHomeoUnit.potentiometer and 
                self.switch == aHomeoUnit.switch and 
                self.uniselector.sameKindAs(aHomeoUnit.uniselector) and 
                self.uniselectorTimeInterval == aHomeoUnit.uniselectorTimeInterval and 
                self.uniselectorActive == aHomeoUnit.uniselectorActive and 
                self.needleCompMethod == aHomeoUnit.needleCompMethod and 
                self.status == aHomeoUnit.status)
        
    def sameConnectionsAs(self, aHomeoUnit): 
        "Check that two units have the same connections"

        connSame = True
        if not len(self.inputConnections) == len(aHomeoUnit.inputConnections): 
            return False
        else:
            for conn1, conn2 in zip(self.inputConnections, aHomeoUnit.inputConnections):
                if not conn1.sameAs(conn2):
                        connSame = False
        
        return connSame
        

    def isReadyToGo(self):
        '''Make sure that unit has 
           all the parameters it needs to operate properly.
        '''
        if self.uniselectorActive:
            uniselectorConditions = (self.uniselector is not None and 
                                     self.uniselectorTime is not None and 
                                     self.uniselectorTimeInterval is not None)
        else:
            uniselectorConditions = True
        
        return (self.criticalDeviation is not None and 
                self.maxDeviation is not None and 
                self.outputRange is not None and 
                self.viscosity is not None and 
                self.noise is not None and 
                self.potentiometer is not None and 
                uniselectorConditions)
   
    def essentialVariableIsCritical(self):
        '''Checks if the next output is critical, 
            i.e. too close to the limit of the  acceptable range, stored in maxDeviation.
            The critical threshold is stored in critThreshold and defaults to 0.9
            in DefaultParameters['critThreshold']'''

        return (self.nextDeviation >= (self.critThreshold * self.maxDeviation) or
                self.nextDeviation <= (self.critThreshold * self.minDeviation))

#------------------------------------------------------------------------------ 

#============================================================================
# CONNECTION METHODS
#============================================================================
   
    def addConnectionUnitWeightPolarityState(self,aHomeoUnit,aWeight,aSwitch,aString):
        '''
        Add a new connection to the unit and set the connection parameters.
        Notice that you always connect the unit starting from the destination, 
        HomeoUnits don't know anything at all about where their output goes.
        If the parameters are not within the expected values, 
        the accessor methods of HomeoConnection will raise exceptions
        '''
        aNewConnection = HomeoConnection()

        aNewConnection.incomingUnit = aHomeoUnit
        aNewConnection.outgoingUnit = self
        aNewConnection.newWeight(aWeight * aSwitch) #must be between -1 and +1
        aNewConnection.state = aString          # must be 'manual' or 'uniselector'"
                
        self.inputConnections.append(aNewConnection)

    def addConnectionUnitWeightPolarityNoiseState(self,aHomeoUnit,aWeight,aSwitch,aNoise,aString):
        '''
        Add a new connection to the unit and set the connection parameters.
        Notice that you always connect the unit starting from the destination, 
        HomeoUnits don't know anything at all about where their output goes.
        If the parameters are not within the expected values, 
        the accessor methods of HomeoConnection will raise exceptions
        '''
        aNewConnection = HomeoConnection()

        aNewConnection.incomingUnit = aHomeoUnit
        aNewConnection.outgoingUnit = self
        aNewConnection.newWeight(aWeight * aSwitch) # must be between -1 and +1
        aNewConnection.noise = aNoise               # must be between 0 and 1"
        aNewConnection.state = aString              # must be 'manual' or 'uniselector'"
                
        self.inputConnections.append(aNewConnection)

    def removeConnectionFromUnit(self, aHomeoUnit): 
        '''Remove the connection(s) to self and originating from aHomeoUnit'''
        
        for conn in self._inputConnections:
            if conn.incomingUnit == aHomeoUnit:
                self.inputConnections.remove(conn)

    def addConnectionWithRandomValues(self,aHomeoUnit):
        '''
        Add a new connection to the unit. Uses the random values (weight, noise, and polarity) 
        selected by the initialization method of HomeoConnection.
        Notice that you always connect the unit starting from the destination, i.e. from the input side, and never from the output side.
        HomeoUnits don't know anything at all about where their output goes.
        If the parameters are not within the expected values, the accessor methods of HomeoConnection will raise exceptions
        '''

        aNewConnection = HomeoConnection()        # The initialize method of HomeoConnection sets random weights"
        aNewConnection.incomingUnit =  aHomeoUnit
        aNewConnection.outgoingUnit =  self
        self._inputConnections.append(aNewConnection)
    

    def saveTo(self,filename):
        "Pickle yourself to filename"

        fileOut = open(filename, 'w')
        pickler = pickle.Pickler(fileOut)
        pickler.dump(self) 
        fileOut.close()

    
    def setRandomValues(self):
        "sets up the unit with random values"

        self.viscosity = np.random.uniform(0.8,HomeoUnit.DefaultParameters['maxViscosity'])
        self.noise = np.random.uniform(0, 0.1)
        self.potentiometer = np.random.uniform(0, 1)

        switchSign = np.sign(np.random.uniform(-1, 1)) #sets the polarity of the self-connection, avoid  0"
        if switchSign == 0:
            switchSign = 1
        self.switch = switchSign 

        "generates a random output  over the whole range"
        self.currentOutput =  np.random.uniform(0, 1)    
        "set the critical deviation to a random value over the whole range"                                                         
        self._criticalDeviation = np.random.uniform(self.outputRange['low'], self.outputRange['high']) 
   
#    def activate(self):
#        self.active = True
#
#    def disactivate(self):
#        self.active = False
#        
#    def toggleActive(self):
#        self.active = not self.active

    def maxConnectedUnits(self, anInteger):
        "Changes the parameter to the Uniselector for the maximum number of connected units"
        
        self._uniselector.unitsControlled = anInteger

    def toggleDebugMode(self):
        "Controls whether the running methods print out debug information"

        self._debugMode = not self._debugMode

    def toggleShowUniselectorAction(self):
        "Control whether the running methods print out information when the uniselector kicks into action"

        self._showUniselectorAction = not self._showUniselectorAction
            
    def isNeedleWithinLimits(self, aValue):
        '''Check whether the proposed value exceeds the unit's range (both + and -)'''

        return np.clip(aValue, self.minDeviation, self.maxDeviation) == aValue

    def uniselectorChangeType(self,uniselectorType):
        "Switch the uniselector type of the unit"
        
        if HomeoUniselector.includesType(uniselectorType): 
            self.uniselector = eval(uniselectorType)()
            self.uniselectorTime = 0
        else:
            raise HomeoUnitError("%s is not a valid HomeoUniselector class" % uniselectorType)
        
    def produceNewName(self):
        '''Produce a name made up of  'Unit-'  plus a unique integer.
           Check the name does not exist yet'''
        
        i = 1
        while ('Unit-' + str(i)) in HomeoUnit.allNames:
            i += 1
        else:
            return ('Unit-' + str(i))
        
    def disactivateSelfConn(self):
        '''Convenience method that disactivates a unit self-connection 
        (always at 0 in self.inputConnections'''
        self.inputConnections[0].status = False
        
    def disactivate(self):
        "set the unit to a non active state"
        self.status = 'Non Active'
            

    #===========================================================================
    # "Running methods that update a HomeoUnit's value"
    #===========================================================================
    
    def clearFutureValues(self):
        '''Set to 0 the internal values used for computing future states'''

        self.nextDeviation = 0
        self.inputTorque = 0
        self.currentOutput =  0

    def clipDeviation(self, aValue): 
        '''Clip the unit's criticalDeviation value if it exceeds its maximum or minimum. 
            Keep the sign of aValue'''
            
        return np.clip(aValue,self.minDeviation,self.maxDeviation)

    def newRandomNeedlePosition(self):
        '''Compute a random value for the needle position within the accepted range'''

        return np.random.uniform(self.minDeviation, self.maxDeviation)
    
    def selfUpdate(self):
        '''This is the master loop for the HomeoUnit. It goes through the following sequence:
        1. Compute new needle's deviation (nextDeviation (includes reading inputs))
        2. Update times
        3. Check whether it's time to check the essential value and if so do it 
           and  update the counter (uniselectorTime) [this might change the weight of the connections]
        4. Move the needle to new position and compute new output'''

        "1. compute where the needle should move to"
        "Testing"
        if self._debugMode:
            sys.stderr.write('Current Deviat. at time: %s for unit %s is %f' 
                             % self.name, str(self.time), str(self.criticalDeviation)) 
            sys.stderr.write('\n')
        
        self.computeNextDeviation()

        "2. update times"
        self.updateTime()
        self.updateUniselectorTime()

        '''3. check whether it's time to check the uniselector/detection mechanism and if so do it. 
           Register that the uniselector is active in an instance variable'''
        if (self.uniselectorTime >= self.uniselectorTimeInterval and
            self.uniselectorActive):
            if self.essentialVariableIsCritical():
                if self.debugMode == True:
                    sys.stderr.write(('############################################Operating uniselector for unit %s' % self.name))
                self.operateUniselector()
                self.uniselectorActivated = 1
            else:
                self.uniselectorActivated = 0
            self.uniselectorTime = 0
        else:
            self.uniselectorActivated = 0        

        '''4. updates the needle's position (critical deviation) with clipping, 
            if necessary, and updates the output'''
        self.criticalDeviation = self.clipDeviation(self.nextDeviation)
        self.computeOutput()
        self.nextDeviation = 0
    
    def computeNextDeviation(self):
        '''Compute the value of the needle's deviation at time t+1 on the basis of the current input 
        and the various parameters of the unit.
        This basic function mimicks Asbhy's original device by the following procedure:

        1. Apply noise to the current value of the unit's deviation
        2. Compute the value of the torque affecting the unit's needle
        3. Compute the value for the unit's new deviation by on the basis of the computed torque value
        4. Store the new value in an internal variable  
        '''
    
        self.updateDeviationWithNoise()
        self.computeTorque()
        self.nextDeviation  = self.newNeedlePosition(self.inputTorque)

    def computeOutput(self):
        '''Scale the current criticalDeviation to the output range.
           Clip the output to within the allowed output range.'''

        "1. Scaling"
        outRange = float((self.outputRange['high'] - self.outputRange['low']))
        lowDev = self.minDeviation
        devRange = float(self.maxDeviation - lowDev)
        out = ((self.criticalDeviation - lowDev) *
               (outRange / devRange ) + self.outputRange['low'])
                        
        "2.Clipping"
        self.currentOutput = np.clip(out, self.outputRange['low'],self.outputRange['high'])

    def computeTorque(self):
        '''In order to closely simulate Asbhy's implementation, 
        computeTorque would have to compute the torque affecting the needle
        by solving a set of differential equations whose coefficients 
        represents the weighted values of the input connections. This is the 
        approach followed by Capehart (1967) in his simulaton of the Homeostat 
        in Fortran. See the comment to the method newNeedlePosition for a discussion.
        
        Here we simply compute the sum of the weighted input values extracted from 
        the inputsCollection on all the connections that are active'''

        activeConnections = [conn for conn in self.inputConnections if (conn.isActive() and 
                                                                        conn.incomingUnit.isActive())]
        #=======================================================================
        # print "For Unit %s the active connections are" % self.name
        # for conn in activeConnections:
        #     print "%s, %s " % (conn.incomingUnit.name,
        #                    conn.isActive())
        #=======================================================================
        #print "The active connections list for unit %s has exactly %u units, with outputs" % (self.name, len(activeConnections))
        #=======================================================================
        # runningSum = 0
        # for conn in activeConnections:
        #     print "%d: into %s with mass: %.0f from %s with critDev: %f, outp:  %f with noise %f, currOut: %f switch: %f and weight: %f.  Running total  is %f " % (self.time,
        #                                                                                                                            self.name,
        #                                                                                                                            self.needleUnit.mass,
        #                                                                                                                            conn.incomingUnit.name, 
        #                                                                                                                            conn.incomingUnit.criticalDeviation, 
        #                                                                                                                            conn.output(), 
        #                                                                                                                            conn.noise,
        #                                                                                                                            conn._incomingUnit.currentOutput,
        #                                                                                                                            conn.switch,
        #                                                                                                                            conn.weight, 
        #                                                                                                                            runningSum)
        #     runningSum += conn.output()
        # print "and the sum is %f " % runningSum
        # print
        #=======================================================================
        self.inputTorque = sum([conn.output() for conn in activeConnections])
        #print "the computed input torque is %f and the delta is %f" % (self.inputTorque, self.inputTorque - runningSum)
        "Testing"
        if self._debugMode:
            sys.stderr.write('Current torque at time: %s for unit %s is %f' %
                             (str(self.time), self.name, self.inputTorque))
            sys.stderr.write('\n')

    def newLinearNeedlePosition(self,aTorqueValue):
        '''See method newNeedlePosition for an extended comment on how 
        to compute the displacement of the needle. Briefly, here we just sum 
        aTorqueValue to the current deviation.
        
        Internal noise is computed in method updateDeviationWithNoise, while noise
        on the connections is computed by HomeoConnections when they return values'''

        totalForce = aTorqueValue    
        '''NOTE: the HomeoUnit method that computes aTorqueValue (passed to this method)
        does not  compute the net force acting on the needle 
        by adding the (negative) force produced by the drag and/ or frictional forces). 
        
        Only subclasses of HomeoUnit do that. Here we simply consider the viscosity 
        of the medium as a fractional multiplier of the torque.
        Viscosity is max at HomeoUnit.DefaultParameters['maxViscosity']  (All force canceled out) and minimum at 0 (no effect)   
        It is a proxy for the more sophisticated computation of drag carried out
        in subclasses'''
        
        normalizedViscosity = self.viscosity / HomeoUnit.DefaultParameters['maxViscosity']
        "Applying the viscosity "
        totalForce = totalForce * (1 - normalizedViscosity)
        
        newVelocity = totalForce / self.needleUnit.mass    
        '''In an Aristotelian model, the change in displacement (= the velocity) 
        is equal to the force affecting the unit divided by the mass: F = mv or v = F/m
        '''
        
        
        "Testing"
        if self._debugMode:
            sys.stderr.write('new position at time: %s for unit %s will be %f ' %
                             str(self.time + 1),
                             self.name,
                             self.criticalDeviation + newVelocity)
            sys.stderr.write('\n')
    
        return self.criticalDeviation + newVelocity    
        '''In an Aristotelian model, new displacement is old displacement totalForce
        plus velocity: x = x0 + vt, with t obviously = 1 in our case'''

    def newNeedlePosition(self,aTorqueValue):
        '''Compute the new needle position on the basis of aTorqueValue, 
        which represents the torque applied to the unit's needle. 
        This method is marquedly different from Ashby's implementation, 
        even if it somehow captures its intent. A longer discussion is appended  below.'''

        if self.needleCompMethod == 'linear':
            return self.newLinearNeedlePosition(aTorqueValue)
        else:
            if self.needleCompMethod == 'proportional':
                return self.newProportionalNeedlePosition(aTorqueValue)
            else:
                return self.newRandomNeedlePosition()       #defaults to a random computation method if the method is not specified"

        """In Asbhy's original implementation, each incoming connection corresponded to a coil 
        around the unit's magnet. The sum of the input currents flowing through the coils produced  
        a torque on the magnet, which, in turn, moved the needle in the trough.
        In order to closely simulate Asbhy's implementation, newNeedlePosition would have 
        to compute the torque affecting the needle by solving a set of differential equations 
        whose coefficients represent the weighted values of the input connections. This is 
        the approach followed by Capehart (1967) in his simulaton of the Homeostat in Fortran.
        
        However, it seems pointless to use differential equations to model a physical mechanism 
        which was originally devised to model a physiological system. After all, as Capehart 
        himself acknowledges, the Homeostat is a kind of analogue computer set up to compute 
        the fundamental features of the system it models. We might as well use a different 
        kind of computer, assuming we are able to capture the essential features as accurately. 
        In this respect, we follow Ashby's suggestion that 'the torque on the magnet 
        [ i.e. the needle] is approximately proportional to the algebraic sum of the currents 
        in A, B, and C' (Ashby 1960:102, sec 8/2), where the coils A, B, C, (and D, i.e. 
        the unit itself) carry a current equal to the weighted input. Thus, this method 
        produces a value that is proportional to the inputValue.
        
        However,  it might be argued (for instance by a dynamic system theorist) that 
        a thoroughly digital simulation of the Homeostat like this one loses what is 
        most essential to it: the continuity of real-valued variables operating in 
        real time. Anyone accepting this objection may partially meet it by:
        
        1. subclassing HomeoUnit, 
        2. adding a method that produces differential equation describing the Torque
        3. and replacing the two methods computeTorque and newNeedlePosition: aTorqueValue 
        with numeric computations of the solutions of the diff equations.
        
        See Ashby, Design for a Brain, chps. 19-22 for a mathematical treatment of the 
        Homeostat and Capehart 1967 for suggestions on a possible implementation 
        (which requires a Runge-Kutta diff solution routine or equivalent and 
        Hurwitz convergence test on the coefficient matrix)
        
        Our method(s) assumes:
        
        1. that the torque is simply the sum of the input connections, hence a value 
        included in +/-  (inputConnections size) (since the max value of any unit's output 
        and hence  of any input, is 1 and the minimum  -1)
        
        2. the torque represents the force that displaces the needle from its current position. 
        The value of this displacement is obviously directly proportional to the force. 
        However, the constant of proportionality is important: if the displacement is 
        simply equal to the torque, which, in turn, is equal to the sum of inputs, 
        then the ***potential displacement*** grows linearly with the connected units. 
        If, instead, the displacement is equal to the ratio between the maximum torque 
        and the maximum deviation, then the ***potential displacement*** is independent 
        from the number of connected units and will depend more directly on the values of 
        the incoming units rather than their number. It is obvious that the behavior of a 
        collection of units, i.e. a homeostat, will be different in either case. Ashby's 
        probably followed the former model, as evidenced by his (widely reported) comments 
        about the direct relation between instability and number of units (see also 
        Capehart 1967 for comments to the same effect). 
        It must be admitted, however, that a careful manipulation of the weights of the 
        connection may reduce the difference between the two methods: one would have to 
        uniformly reduce the weights whenever a new connection is added to transform the 
        first ('Ashby's') approach into the second.
        
        In order to allow experimentation with either approach, we include both methods: 
        HomeoUnit().newLinearNeedlePosition and HomeoUnit().newProportionalNeedlePosition
        The choice between the two is determined by the value of the instance variable 
        needleCompMethod. Default (stored in the class variable) is linear.
        
        The viscosity is between 0 and 1, with 0 being the maximum (needle unable to move) 
        and 1 being the minimum (no effect on movement)"""


    def newProportionalNeedlePosition(self, aTorque):
        '''See method newNeedlePosition for an extended comment on how 
        to compute the displacement of the needle'''

        normalizedViscosity = self.viscosity / HomeoUnit.DefaultParameters['maxViscosity']
        
        totalForce = aTorque  / (self.maxDeviation  * 2.)
        totalForce = totalForce * (1- normalizedViscosity)
        newVelocity = totalForce / self.needleUnit.mass   
        return self.criticalDeviation + newVelocity
    
    def operateUniselector(self):
        '''Activate the uniselector to randomly change the weights of the input connections        
         (excluding the self connection)'''



        "We save the values about the units that have changed weights, old weights and new weight for debugging"
        weightChanges = []
        for conn in self.inputConnections:
#            if not conn.incomingUnit == self:                  #This is not necessary. Even though the default is 'manual' it is sometimes useful to operate on the self-connection "
            if conn.state ==  'uniselector' and conn.active:
                change = []
                change.append(conn.incomingUnit.name)
                change.append(conn.weight)
                changedWeight = self.uniselector.produceNewValue()
                change.append(changedWeight)
                weightChanges.append(change)
                conn.newWeight(changedWeight)
        self.uniselector.advance()



        "For debugging"
        if self._showUniselectorAction:
            for connChange in weightChanges:
                sys.stderr.write('At time: %i, %s activated uniselector for unit %s switching weight from: %f to: %f \n' %
                                 (self.time) + 1,
                                 self.name,
                                 connChange[0],
                                 connChange[1],
                                 connChange[2])

    def physicalVelocity(self):
        '''Convert the velocity of the unit into a value expressed in 
           physical units (m/s) according to the physical equivalence parameters'''

        return self.currentVelocity * (self._physicalParameters['lengthEquivalence'] / self._physicalParameters['timeEquivalence'])

    def updateDeviationWithNoise(self):
        '''Apply the unit's internal noise to the critical deviation and update accordingly.  
           Computation of noise uses the utility HomeoNoise class'''
        
        newNoise = HomeoNoise()
        newNoise.withCurrentAndNoise(self.criticalDeviation, self.noise)
        newNoise.distorting()    # since the noise is a distortion randomly select either a positive or negative value for noise"
        newNoise.normal()        # compute a value for noise by choosing a normally distributed random value centered around 0."
#        newNoise.proportional()  # consider noise as the ratio of the current affected by noise"
        newNoise.linear()        # consider noise as  proportional to the  absolute magnitude of the noise parameter
        addedNoise = newNoise.getNoise()
        hDebug('unit', ("Noise for unit %s is: %f" % (self.name, addedNoise)))
#        sys.stderr.write("New noise is %f at time: %u\n" % (addedNoise, self.time))
#        self.criticalDeviation = np.clip((self.criticalDeviation + addedNoise), self.minDeviation, self.maxDeviation)    # apply the noise to the critical deviation value"
        self.criticalDeviation = self.criticalDeviation + addedNoise    # apply the noise to the critical deviation value"


    def updateTime(self):
        '''Do nothing. In the current model, time is updated by the homeostat, 
           the homeounit are basically computing machine with no knowledge of time'''

        pass

    def updateUniselectorTime(self):
        '''Updates the tick counter for the uniselector'''
        
        self.uniselectorTime = self.uniselectorTime + 1

#==============================================================================
# Printing
#==============================================================================
 
    def printDescription(self):
        '''Return a string containing a text representation of 
           all of the the unit's instance variables'''

        aStream = StringIO.StringIO()
        aStream.write('aHomeoUnit with values: \n')
        for ivar in sorted(vars(self).keys()):
            aStream.write(ivar)
            aStream.write(' --> ')
            aStream.write(vars(self)[ivar])
            aStream.write('\t')
            aStream.write
        aStream.write('\n')
        content = aStream.getvalue()     
        aStream.close()
        return content

    def printOn(self, aStream):
        "Returns a brief description of the unit"

        aStream.write(self.__class__.__name__)
        aStream.write(': ')
        aStream.write(self.name)
        return aStream
        
    def __del__(self):
        ''''Remove a HomeoUnit's name from the set of used names.
            Subclasses' instances must call this method explicitly 
            to remove  their names'''
        if self._name is not None:
            HomeoUnit.allNames.remove(self._name)
        
        
        
        
        