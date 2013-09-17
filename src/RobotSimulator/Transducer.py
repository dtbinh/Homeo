'''
Created on Sep 3, 2013
@author: stefano

The Transducer module contains the classes necessary to operate 
a robot's actuators (motors, etc). The basic class is fairly abstract 
and may be subclassed to operate concrete robotic simulation environments
(player/Stage, Webots, etc) 
'''

from Helpers.General_Helper_Functions import SubclassResponsibility

class TransducerException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Transducer(object):
    '''
    Transducer is an abstract class. It subclasses control a robot's input /output interfaces. 
    It has just three instance variables:

    robot          <aRef>        a ref to the robot whose actuator it operates
    transdFunction <aString>    the name of the robot's function to operate the actuator
    parameters     <aList>      a list of  parameters to be passed to the function

    The basic methods (all defined in subclasses) are 
    
    act  ---  which activates the actuator by running robot.function(parameters)
    sense --- which read the sensor by running robot.function(parameters) and returning a value
    range --- which returns a 2 value list containing the minimum and maximum values of the transducer 
    
    '''


    def __init__(self):
        '''
        Basic setup
        '''
    #=================================================================
    # Class properties
    #=================================================================
    
    def setRobot(self, aValue):
        self._robot = aValue
    def getRobot(self):
        return self._robot
    robot = property(fget = lambda self: self.getRobot(),
                    fset = lambda self, value: self.setRobot(value))  

    def setTransdFunction(self, aValue):
        self._transdFunction = aValue
    def getTransdFunction(self):
        return self._transdFunction
    transdFunction = property(fget = lambda self: self.getTransdFunction(),
                    fset = lambda self, value: self.setTransdFunction(value))
    
    def setFuncParameters(self, aValue):
        self._funcParameters = aValue
    def getFuncParameters(self):
        return self._funcParameters
    funcParameters = property(fget = lambda self: self.getFuncParameters(),
                    fset = lambda self, value: self.setFuncParameters(value))  
  

    #======================================================================
    #  Running methods
    #======================================================================
    
    def act(self, parameters):
        '''act method is implemented only by Transducer's subclasses'''
        raise SubclassResponsibility()
    
    def read(self):
        '''read method is implemented only by Transducer's subclasses'''
        raise SubclassResponsibility()
        
    def range(self):
        '''range method is implemented only by Transducer's subclasses'''
        raise SubclassResponsibility()


class WebotsDiffMotor(Transducer): 
    '''
     webotsDiffMotor is the interface to the wheels of a Webots'
     Differential Wheel robot. Its "_wheel" variable specifies which wheel (right or left)
     it controls. It defines the transdFunction name and redefines
     setFuncParameters to modify only one of the values (corresponding to the right or left motor) 
     '''   
    
    def __init__(self, wheel):
        " initialize instance to Webots values and sets the right or left wheel accordingly"
        self._transdFunction = "setSpeed"
        if wheel not in ["right","left"]:
            raise TransducerException("Wheel must either be right or left")
        else:
            self._wheel = wheel
        
        self._functParameters = (0,0)
        
    def setFunctParameters(self,aNumber):
        if self._wheel == "right":
            self._functParameters = (self._robot.getLeftSpeed(), aNumber)
        else:
            self._functParameters = (aNumber, self._robot.getRightSpeed())
            
    def act(self):
        '''activates the wheel motor by calling the actuator function with the passed parameters'''
        self._robot.__getattribute__(self.transdFunction)(self.funcParameters)
        
    def range(self):
        '''return a list containing the min and max speed of the motor'''
        if self._wheel == "right":
            return [0, self._robot.getMaxSpeed[1]]
        else:
            return [0,self._robot.getMaxSpeed[0]]
        
class WebotsLightSensor(Transducer):
    '''Interface to a Webots' robot light sensor'''
    
    def __init__(self, sensor):
        '''Initialize the sensor with the Webots function name and the sensor's name'''
        self._transdFunction = "getValue"
        self._funcParameters = sensor
        
    def read(self):
        '''returns the light value''' 
        self._robot.__getattribute__(self.transdFunction)(self.funcParameters)
       
    def range(self):
        '''Returns the range of the light sensor.
           FIXME Webots actually has now access to the light sensor maximum value (its minimum value is 0).
           Raise an exception for now'''
        raise TransducerException("Webots does not give access to a sensor's max value")
    
    
class TransducerTCP(object):
    '''
    TransduceTCP is an abstract class. Its subclasses control a robot's input /output interfaces
    through a TCP connection to a server running on the robot. 
    It has just four instance variables:

    robotSocket    <aString>    the socket conneted to the robot server
    transdFunction <aString>    the string corresponding to the transducer command. Acceptable strings are defined by the server protocol 
                                and detailed in class WebotsTCPClient
    funcParameters     <aString>    a string containing a list of  parameters to be passed to the command
    transducRange  <aList>      the min and max range of the transducer. Cached here for efficiency reasons

    The basic methods (all defined in subclasses) are 
    
    act  ---  which activates the actuator by running robot.function(parameters)
    sense --- which read the sensor by running robot.function(parameters) and returning a value
    range --- which returns a 2 value list containing the minimum and maximum values of the transducer 
    
    '''


    def __init__(self):
        '''
        Basic setup
        '''
    #=================================================================
    # Class properties
    #=================================================================
    
    def setRobotSocket(self, aValue):
        self._robotSocket = aValue
    def getRobotSocket(self):
        return self.robotSocket
    robotSocket = property(fget = lambda self: self.getRobotSocket(),
                    fset = lambda self, value: self.setRobotSocket(value))  
    
    def setTransdFunction(self, aValue):
        self._transdFunction = aValue
    def getTransdFunction(self):
        return self._transdFunction
    transdFunction = property(fget = lambda self: self.getTransdFunction(),
                    fset = lambda self, value: self.setTransdFunction(value))
    
    def setFuncParameters(self, aValue):
        self._funcParameters = str(aValue)
    def getFuncParameters(self):
        return self._funcParameters
    funcParameters = property(fget = lambda self: self.getFuncParameters(),
                    fset = lambda self, value: self.setFuncParameters(value))  
  

    #======================================================================
    #  Running methods
    #======================================================================
    
    def act(self, parameters):
        '''act method is implemented only by Transducer's subclasses'''
        raise SubclassResponsibility()
    
    def read(self):
        '''read method is implemented only by Transducer's subclasses'''
        raise SubclassResponsibility()
        
    def range(self):
        '''range method is implemented only by Transducer's subclasses'''
        raise SubclassResponsibility()

class WebotsDiffMotorTCP(TransducerTCP): 
    '''
     webotsDiffMotor is the interface to the wheels of a Webots'
     Differential Wheel robot controlled by a server. 
     Its "_wheel" variable specifies which wheel (right or left)
     it controls. It defines the transdFunction name and redefines
     setFuncParameters to modify only one of the values (corresponding to the right or left motor) 
     '''   
    
    def __init__(self, wheel):
        " initialize instance to Webots values and sets the right or left wheel accordingly"
        if wheel not in ["right","left"]:
            raise TransducerException("Wheel must either be 'right' or 'left'")
        else:
            self._wheel = wheel
            if self._wheel == 'right':
                self._transdFunction = "R"
            else:
                self._transdFunction = 'L'

        
        self._functParameters = "0"
                    
    def act(self):
        '''activates the wheel motor by calling the actuator function with the passed parameters'''
        command = self.transdFunction + ',' + self.funcParameters
        self._robotSocket.send(command)
        "Discard reply from receive buffer"
        discard = self._robotSocket.recv(100)
                
    def range(self):
        '''return a list containing the min and max speed of the motor.
           notice that the min speed is always = to minus maxspeed in webots
           and the both wheels have identical maxspeed'''
        
        if self.transducRange is not None:
            self.robotSocket.send('M')
            commandReturn = self._robotSocket.recv(1024).rstrip('\r\n').split(',')
            self._transducRange = [-commandReturn[1], commandReturn[1]]
        
        return self.transducRange
        
class WebotsLightSensorTCP(TransducerTCP):
    '''Interface to a Webots' robot light sensor'''
    
    def __init__(self, aNumber):
        '''Initialize the sensor with the Webots function name and the number of the sensor.
           Notice that it is the caller class responsibility to make sure that there is actually 
           such a sensor in the robot and that the robot tcp server controller returns an approporate string'''
        self._transducFunction = "O"
        self._funcParameters = aNumber
        
    def read(self):
        '''returns the light value by reading the nth element of 
           the list of values returned by the read command.
           Convert the value to its complement to Max Value, because Webots
           use Max for the minimum stimulus and 0 for the max stimulus'''
        self._robotSocket.send(self._transducFunction)
        light_values = self._robotSocket.recv(1024).rstrip('\r\n').split(',')[1:]  
        return self.range()[1] - float(light_values[self._funcParameters])
       
    def range(self):
        '''Returns the range of the light sensor.
           FIXME Webots actually has no access to the light sensor maximum value (its minimum value is 0).
           return 1000'''
#        raise TransducerException("Webots does not give access to a sensor's max value")
        return [0,1000]   
        
    