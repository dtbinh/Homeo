from Helpers.HomeoNoise import *
import numpy as np
from scipy.stats import * 


class ConnectionError(Exception):
    '''
    Base class for exceptions in the HomeoConnection module
    '''
    pass

class HomeoConnection:
    '''
    HomeoConnection represents a connection between two HomeoUnits.
    It  holds the incoming unit (the unit the signal is coming from), 
    the outgoing unit (the unit the signal goes to---typically the unit that is holding the connection),  
    the weight of the connection, and the polarity of the connection.

    Instance Variables:
    incomingUnit        <aHomeoUnit>      the HomeoUnit the signal is coming from
    outgoingUnit        <aHomeoUnit>      the HomeoUnit the signal is going to (typically the unit holding on to this HomeoConnection)
    switch               <anInteger>      polarity of the connection ( +1 or -1)
    weight               <aFloat>         weight of the connection : between 0 and 1
    noise                <aFloat>         possible noise on the connection (between 0--no noise - to 1, so noisy to break the connection)
    state                <aString>        determines whether the connection is governed by weight and switch or by the uniselector. 
                                          The value can only be 'manual' or 'uniselector'
    status               <aString>        whether the connection is active or not. Values can be 'Yes' or 'No'
    active               <aBoolean>       whether or not the connection is active
    '''
    
    
    def __init__(self):
        '''
        A new connection is always initialized to some random values. 
        '''
        self.randomizeConnectionValues()
        
    def randomizeConnectionValues(self):
        '''Initialize the connection to some random value for noise and weight, 
           and set the default state to "uniselector"'''

        self.noise = np.random.uniform(0,0.1)
        self.state = 'uniselector'
        self.weight = np.random.uniform(0,1)
        self.switch = np.sign(np.random.uniform(-1,1))
        self.active = True
        self.status = 'Yes'

    "class methods"
    @classmethod    
    def newWithIncomingUnitWeightSwitchNoiseStateActive(cls,incomingUnit, aWeight, aSwitch, aNoise, aState, anActive):
        '''
        Return a new connection with values initialized as specified
        '''
        conn = HomeoConnection()
        conn.incomingUnit = incomingUnit
        conn.weight = aWeight
        conn.switch = aSwitch
        conn.noise = aNoise
        conn.state = aState
        conn.active = anActive
        
        return conn 
    
    @classmethod    
    def newWithIncomingUnitOutgoingUnitWeightSwitchNoiseStateActive(cls,aUnit,anotherUnit,aWeight,aSwitch,aNoise,aState,anActive):
        '''
        Return a new connection with values initialized as specified.
        '''
        
        conn = HomeoConnection()
        conn.incomingUnit = aUnit
        conn.outgoingUnit = anotherUnit
        conn.weight = aWeight
        conn.switch = aSwitch
        conn.noise = aNoise
        conn.state = aState
        conn.active = anActive
        
        return conn 

    @classmethod    
    def newFromUnitToUnit(self,aHomeoUnit,anotherUnit):
        '''Creates a new connection with  the incoming and outgoing units'''
        
        conn = HomeoConnection()
        conn.outgoingUnit =  aHomeoUnit
        conn.incomingUnit =  anotherUnit
        return conn

    def getIncomingUnit(self):
        return self._incomingUnit
    
    def setIncomingUnit(self, aHomeoUnit):
        "Do nothing. Noise is set through other methods"
        self._incomingUnit = aHomeoUnit
    
    incomingUnit = property(fget = lambda self: self.getIncomingUnit(),
                          fset = lambda self, value: self.setIncomingUnit(value))   
    def getOutgoingUnit(self):
        return self._outgoingUnit
    
    def setOutgoingUnit(self, aHomeoUnit):
        "Do nothing. Noise is set through other methods"
        self._outgoingUnit = aHomeoUnit
    
    outgoingUnit = property(fget = lambda self: self.getOutgoingUnit(),
                          fset = lambda self, value: self.setOutgoingUnit(value))   

    def getSwitch(self):
        return self._switch
    
    def setSwitch(self, aSwitch):
        '''Raise an exception: switch is only set through the newWeight method'''
        raise ConnectionError("A HomeoConnection's switch can only be set through the newWeight method")
    
    switch = property(fget = lambda self: self.getSwitch(),
                          fset = lambda self, value: self.setSwitch(value))   

    def getWeight(self):
        return self._weight
    
    def setWeight(self, aWeight):
        '''''Raise an exception:  weight can only be set with  
        newWeight: a value, which takes care of absolute value and polarity (switch)'''
        raise ConnectionError("A HomeoConnection's weight can only be set  through the newWeight method")
    
    weight = property(fget = lambda self: self.getWeight(),
                          fset = lambda self, value: self.setWeight(value))   

    def getNoise(self):
        return self._noise
    
    def setNoise(self, aNoise):
        self._noise = aNoise
    
    noise = property(fget = lambda self: self.getNoise(),
                          fset = lambda self, value: self.setNoise(value))   
    def getState(self):
        return self._state
    
    def setState(self, aString):
        '''raise an exception if the input value is neither "manual" or "uniselector"'''
        if aString in ['manual','uniselector']:                 
            self._state = aString
        else:
            raise ConnectionError("The state value %s is not allowed. Only allowed values are manual and uniselector" % aString)
    
    state = property(fget = lambda self: self.getState(),
                          fset = lambda self, value: self.setState(value))   

    def getStatus(self):
        return self._status
    
    def setStatus(self, aState):
        self._status = aState
    
    status = property(fget = lambda self: self.getStatus(),
                          fset = lambda self, value: self.setStatus(value))   

    def getActive(self):
        return self._active
    
    def setActive(self, aHomeoUnit):
        "Do nothing. Active is set through other methods"
        self._active = aHomeoUnit
    
    active = property(fget = lambda self: self.getActive(),
                          fset = lambda self, value: self.setActive(value))   
    
    def newWeight(self, aWeight):
        "updates weight and switch on the basis -1 >=  aWeight <= 1"

        self._weight= abs(aWeight)
        if aWeight == 0:
            self._switch = 1
        else:
            self._switch = np.sign(aWeight)

    def outgoingUnit(self):
        ''' the "outgoingUnit" is the unit the signal is going *to*. 
            It is typically the HomeoUnit holding on to the connection''' 
        
        return self._outgoingUnit
    
    def output(self):
        ''''Return the value of the connection times the weight, possibly switched,  and  include  the noise. 
            The noise  is computed with the help of the HomeoNoise utility class. 
            Several different algorithms are available, see the instance methods of HomeoNoise for details'''
        
        newNoise = HomeoNoise()
        newNoise.withCurrentAndNoise(self.incomingUnit.currentOutput(), self._noise)

        newNoise.normal()          # select noise as normally (Gaussian) distributed around the value for the unit's connection noise"
        newNoise.distorting()      # select  noise as distorting the current"
        newNoise.proportional()    # consider the noise on the communication line as a ration of the current being transmitted"

        return (self._incomingUnit.currentOutput() * self._switch * self._weight) + newNoise.getNoise()
    
    def isActive(self):
        '''sets the connection to active'''
        self.status = 'Yes'
        return self._status
    
    def switchToManual(self):
        "Change the state of the connection to manual"

        self.state = 'manual'

    def switchToUniselector(self):
        "Change the state of the connection to uniselector"

        self.state = 'uniselector'
        
    def sameAs(self,aConnection): 
        '''Test if two connections are the same, which means:
        - same parameters, 
        - same incoming Unit  (first level parameters only)

        Notice that since incoming units have, in turn, input connections, 
        we cannot pursue the testing that deep because we may enter into a loop. 
        We only check the first level parameters'''

        sameAs = self.weight == aConnection.weight and \
                 self.switch == aConnection.switch and \
                 self.noise == aConnection.noise and \
                 self.state == aConnection.state and \
                 self.status == aConnection.status and \
                 self.incomingUnit.sameFirstLevelParamsAs(aConnection.incomingUnit)
        return sameAs
