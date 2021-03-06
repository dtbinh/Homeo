'''
Created on Mar 19, 2013

@author: stefano
'''
from Core.Homeostat import *
from Core.HomeoDataCollector  import *
from Core.HomeoUnitNewtonian  import *
from datetime import datetime
import os, pickle

class HomeoSimulation(object):
    '''
    HomeoSimulation is the class that manages a complete run of a Homeostat. 
    It takes care of the administrative tasks: 
    - setting up the initial conditions, 
    - starting and stopping the simulation. 
    It also knows how to read initial conditions from a file (for repeated experiments). 
    The real work of simulating the Homeostat is done by the Homeostat 
    class---an instance of which is held by the simulation---and its components.

    Instance Variables:
        homeostat                   <aHomeostat>       The Homeostat being run in the simulation
        maxRuns                     <anInteger>        The maximum number of simulation steps 
        dataFilename                <aString>          The filename used to save the simulation data
        dataAreSaved                <aBoolean>         Whether the simnulation run data have been saved
        homeostatFilename           <aString>          The filename used to save the homeostat
        homeostatIsSaved            <aBoolean>         Whether the homeostat being simulated has been saved        
    '''

#===============================================================================
# Class methods
#===============================================================================

    @classmethod    
    def readFrom(self,filename):
        '''This is a class method that create a new HomeoSimulation instance from a filename,
        by loading a pickled homeostat'''
        fileIn = open(filename, 'r')
        unpickler = pickle.Unpickler(fileIn)
        newHomeostat = unpickler.load()
        fileIn.close()
        newHomeoSimulation = HomeoSimulation()
        newHomeoSimulation.homeostat = newHomeostat
        newHomeoSimulation.homeostatIsSaved = True 
        return newHomeoSimulation



#===============================================================================
# Accessing and initialization
#===============================================================================

    def getDataFilename(self):
        return self._dataFilename
    
    def setDataFilename(self, aString):
        self._dataFilename = aString

    dataFilename = property(fget = lambda self: self.getDataFilename(),
                        fset = lambda self, aString: self.setDataFilename(aString))

    def getHomeostatFilename(self):
        return self._homeostatFilename
    
    def setHomeostatFilename(self, aString):
        self._homeostatFilename = aString

    homeostatFilename = property(fget = lambda self: self.getHomeostatFilename(),
                        fset = lambda self, aString: self.setHomeostatFilename(aString))

    def getHomeostat(self):
        return self._homeostat
    
    def setHomeostat(self,aHomeostat):
        self._homeostat = aHomeostat
    
    homeostat = property(fget = lambda self: self.getHomeostat(),
                         fset = lambda self, aHomeostat: self.setHomeostat(aHomeostat))
    
    def getMaxRuns(self):
        return self._maxRuns
    
    def setMaxRuns(self,anInteger):
        self._maxRuns=  anInteger

    maxRuns = property(fget = lambda self: self.getMaxRuns(),
                       fset = lambda self, number: self.setMaxRuns(number)) 

    def getHomeostatIsSaved(self):
        return self._homeostatIsSaved
    
    def setHomeostatIsSaved(self,anInteger):
        self._homeostatIsSaved=  anInteger

    homeostatIsSaved = property(fget = lambda self: self.getHomeostatIsSaved(),
                       fset = lambda self, number: self.setHomeostatIsSaved(number)) 

    def getDataAreSaved(self):
        return self._dataAreSaved
    
    def setDataAreSaved(self,anInteger):
        self._dataAreSaved=  anInteger

    dataAreSaved = property(fget = lambda self: self.getDataAreSaved(),
                       fset = lambda self, number: self.setDataAreSaved(number)) 

    def units(self):
        return self.homeostat.homeoUnits
    
    def __init__(self):
        '''
        Initialize the instance with a new homeostat and a default number of runs."
        '''
        
        self._homeostat = Homeostat()
        self._maxRuns = 1000
        self._dataFilename = self.createDefaultDataFilename()
        self._homeostatFilename = self.createDefaultHomeostatFilename()
        self._dataAreSaved = True       # There are no data to save yet
        self._homeostatIsSaved = False  # A new simulation has a new random Homeostat, unless is loaded form file
        
    def initializeAshbySimulation(self):
        '''Adds four fully connected units with random values to the simulator 
           (as per Ashby basic design)'''
 
        for i in xrange(4):
            unit = HomeoUnitNewtonian()
            unit.setRandomValues()
            self._homeostat.addFullyConnectedUnit(unit)

#===============================================================================
# Running methods
#===============================================================================

    def runForever(self):
        '''Start the homeostat and runs it indefinitely. 
           This method must be run in a thread, or it will block further access 
           to the interpreter. 
           The homeostat can be stopped by sending #stop to the simulation'''
    
        self._dataAreSaved = False
        self._homeostatIsSaved = False
        self._homeostat.start()

    def start(self):
        '''Run the homeostat for the number of runs specified in maxRuns'''

        self._dataAreSaved = False
        self._homeostatIsSaved = False
        self._homeostat.runFor(self._maxRuns)

    def stop(self):
        "Stop the simulation" 

        self.homeostat.stop()

#===============================================================================
# Adding methods 
#===============================================================================

    def addFullyConnectedUnit(self, aHomeoUnit):
        '''Add a fully connected unit to the simulation's homeostat'''

        self.homeostat.addFullyConnectedUnit(aHomeoUnit)


    def addUnit(self, aHomeoUnit):
        '''Add a  unit to the simulation's homeostat'''

        self._homeostat. addUnit(aHomeoUnit)

#===============================================================================
# Saving methods
#===============================================================================

    def createDefaultDataFilename(self):
        '''Create a default string corresponding to the dataFilename. 
           Check that no file with the same name exists in current directory'''
        
        dateString = ''
        now_ = datetime.now()
        dateString += str(now_.month) + '-' + str(now_.day) + '-' + str(now_.year)
        name = 'HomeoSimulationData'
    
        number = 1
        completeName = name + '-' + dateString + '-' + '1'
    
        while os.path.exists(completeName):
            number += 1
            completeName = name + '-' + dateString  + '-' + str(number)+'.txt'
    
        return completeName

    def createDefaultHomeostatFilename(self):
        '''Create a default string corresponding to the dataFilename. 
           Check that no file with the same name exists in current directory'''
        
        dateString = ''
        now_ = datetime.now()
        dateString += str(now_.month) + '-' + str(now_.day) + '-' + str(now_.year)
        name = 'HomeoSimulation'
    
        number = 1
        completeName = name + '-' + dateString + '-' + '1'
    
        while os.path.exists(completeName):
            number += 1
            completeName = name + '-' + dateString  + '-' + str(number)+'.pickled'
    
        return completeName

    def saveCompleteRunOnFile(self):
        "Asks the datacollector of the homeostat to save all data on dataFilename"

        fileContent = self.homeostat.dataCollector.printEssentialDataOnAString('')
        fileOut  = open(self.dataFilename, 'w')
        fileOut.write(fileContent)
        fileOut.close()
        self._dataAreSaved = True

    def saveEssentialDataOnFile(self):
        '''Ask the datacollector of the homeostat 
           to save only the essential data on dataFilename'''

        fileContent = self.homeostat.dataCollector.printEssentialDataOnAString('')
        fileOut  = open(self.dataFilename, 'w')
        fileOut.write(fileContent)
        fileOut.close()

    def saveEssentialDataOnFileWithSeparator(self, aCharacter):
        '''Ask the datacollector of the homeostat 
           to save only the essential data on dataFilename,
           using aCharacter as a column separator'''

        fileContent = self.homeostat.dataCollector.saveEssentialsOnAStringWithSeparator('', aCharacter)
        fileOut  = open(self.dataFilename, 'w')
        fileOut.write(fileContent)
        fileOut.close()
        
        
    def save(self):
        '''Save the homeostat the simulation manages to a pickled file
           It will erase the old content of aFilename.'''

        self.homeostat.saveTo(self.homeostatFilename)
        self._homeostatIsSaved = True


    def isReadyToGo(self):
        '''Check that the homeostat is ready to go and that 
           the maxRuns and dataFilename are present'''

        return (self._homeostat.isReadyToGo() and
                self.maxRuns is not None and
                self._dataFilename is not None and
                self._homeostatFilename is not None)
        