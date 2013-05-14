'''
Created on Mar 19, 2013

@author: stefano
'''
from Core.Homeostat import *
from Core.HomeoDataCollector  import *
from Core.HomeoUnitNewtonian  import *
from datetime import datetime
import os, pickle
from PyQt4.QtCore import  *
from PyQt4.QtGui import QApplication 

class HomeoQtSimulation(QObject):
    '''
    HomeoQSimulation is the class that manages a complete run of a Homeostat
    run in the Qt framework. 
    
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
        simulDelay                  <anInteger>        Delay, in milliseconds, between two simulation steps
    '''

#===============================================================================
# Class methods
#===============================================================================

    @classmethod    
    def readFrom(self,filename):
        '''This is a class method that create a new HomeoSimulation instance from a filename,
        by loading a pickled homeostat'''
        newHomeostat = Homeostat.readFrom(filename)
        newHomeoSimulation = HomeoQtSimulation()
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
        self.emit(SIGNAL("homeostatFilenameChanged"), self._homeostatFilename)

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
        self._maxRuns =  anInteger

    maxRuns = property(fget = lambda self: self.getMaxRuns(),
                       fset = lambda self, number: self.setMaxRuns(number)) 

    def getHomeostatIsSaved(self):
        return self._homeostatIsSaved
    
    def setHomeostatIsSaved(self,anInteger):
        self._homeostatIsSaved =  anInteger
        #Emit signal here"

    homeostatIsSaved = property(fget = lambda self: self.getHomeostatIsSaved(),
                       fset = lambda self, number: self.setHomeostatIsSaved(number)) 

    def getDataAreSaved(self):
        return self._dataAreSaved
    
    def setDataAreSaved(self,anInteger):
        self._dataAreSaved =  anInteger

    dataAreSaved = property(fget = lambda self: self.getDataAreSaved(),
                       fset = lambda self, number: self.setDataAreSaved(number)) 
    
    def getSimulDelay(self):
        return self._simulDelay
    
    def setSimulDelay(self,aValue):
        self._simulDelay = aValue
        
    simulDelay = property(fget=lambda self: self.getSimulDelay(),
                          fset = lambda self, value: self.setSimulDelay())
    
    def units(self):
        return self.homeostat.homeoUnits
    
    def __init__(self):
        '''
        Initialize the instance with a new homeostat and a default number of runs."
        '''
        super(HomeoQtSimulation,self).__init__()
        self._homeostat = Homeostat()
        self._maxRuns = 1000
        self._dataFilename = self.createDefaultDataFilename()
        self._homeostatFilename = self.createDefaultHomeostatFilename()
        self._dataAreSaved = True       # There are no data to save yet
        self._homeostatIsSaved = False  # A new simulation has a new random Homeostat, unless is loaded form file
        self._simulDelay = 10           # in milliseconds
        self._isRunning = False
        
    def initializeAshbySimulation(self):
        '''Adds four fully connected units with random values to the simulator 
           (as per Ashby basic design)'''
 
        for i in xrange(4):
            unit = HomeoUnitNewtonian()
            unit.setRandomValues()
            self._homeostat.addFullyConnectedUnit(unit)
    
    def initializeAshbyFirstExperiment(self):
        '''Initialize a 2-Unit Homeostat as per Ashby's first experiment (The Homeostat as an adaptor):
           2 Units, one (called "Agent") self-connected with negative feedback, 
           the second one ("Environment") not self-connected'''
        unit1 = HomeoUnitNewtonian()
        unit1.setRandomValues()
        unit1.name = "Agent"
        unit2 = HomeoUnitNewtonian()
        unit2.setRandomValues()
        unit2.name = "Environment"
        self._homeostat.addFullyConnectedUnit(unit1)
        self._homeostat.addFullyConnectedUnit(unit2)
        self._homeostat.removeConnectionFromUnit1ToUnit2(unit2, unit2)        # Environment unit is not self-connected"
        self._homeostat.unitWithName("Environment").uniselectorActive = False # Environment unit has no uniselector working"
        

#===============================================================================
# Running methods
#===============================================================================

    def go(self):
        '''Start the homeostat and runs it for the number of runs specified in maxRuns. 
           This method must be run in a thread, or it will block further access 
           to the interpreter. 
           The homeostat can be paused by sending #pause to the simulation'''
           
        self._dataAreSaved = False
        self._homeostatIsSaved = False
        self._isRunning = True
        
        while self._homeostat.time  < self._maxRuns  and self._isRunning == True:
#            print "I am running cycle number: %u" % self._homeostat.time
            self._homeostat.runOnce()
            time.sleep(self._simulDelay / 1000)
            QApplication.processEvents() 

    def pause(self):
        "Pause the simulation" 

        self._isRunning = False
        
    def resume(self):
        "Resume the simulation"
        
        self._isRunning = True
        self.go()
    
    def step(self):
        "Advance the simulation one step"
        if self._homeostat.time  < self._maxRuns:
#            print "I am running cycle number: %u" % self._homeostat.time
            self._homeostat.runOnce()
        

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
# Saving and loading methods
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
        name = 'Homeostat'
    
        number = 1
        completeName = name + '-' + dateString + '-' + '1'+'.pickled'
    
        while os.path.exists(completeName):
            number += 1
            completeName = name + '-' + dateString  + '-' + str(number)+'.pickled'
    
        return completeName

    def saveCompleteRunOnFile(self,aFilename):
        "Asks the datacollector of the homeostat to save all data on dataFilename"

        self.homeostat.dataCollector.saveCompleteDataOnFile(aFilename)
        self._dataAreSaved = True

    def saveEssentialDataOnFile(self,aFilename):
        '''Ask the datacollector of the homeostat 
           to save only the essential data on dataFilename'''

        self.homeostat.dataCollector.saveEssentialDataOnFile(aFilename)
        
    def essentialSimulationData(self):
        "Ask the DataCollector to teturn a string with the essential data about the simulaiton"
        return self.homeostat.dataCollector.printPlottingDataForROnAString('')

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
    
    def loadNewHomeostat(self, aFilename):
        "loads a new homeostat from aFilename"
        try:
            newHomeostat = Homeostat.readFrom(aFilename)
        except HomeostatError:
            sys.stderr.write(("Could not load a new homeostat from filename: %s" % aFilename))
            raise
        self.homeostat = newHomeostat
        self.homeostatFilename = aFilename
        self.homeostatIsSaved = True
        self.dataAreSaved = True

#===============================================================================
# Changing simulation values methods
#===============================================================================

    def timeReset(self):
        """
        Restart the  simulation: 
        resets simulation time to zero     
        clear the simulation data
        set dataAreSaved to true
        """
        self._homeostat.timeReset()
        self._homeostat.flushData()
        self._dataAreSaved = True
        
    def fullReset(self):
        """
        Start a new simulation:
        fully reset the homeostat
        clear the simulation data
        set dataAreSaved to true
        pick a new name
        """
        self._homeostat.fullReset()
        self._homeostat.flushData()
        self._dataAreSaved = True
        self._homeostatFilename = self.createDefaultHomeostatFilename()

        
#===============================================================================
# Debugging methods
#===============================================================================

    def toggleDebugMode(self):
        'Toggle the debugMode switch of  all the units in the homeostat'
        for unit in self._homeostat.homeoUnits:
            unit.toggleDebugMode()
        
    def toggleShowUniselectorAction(self):
        'Toggle the ShowUniselectorAction switch of all the units in the homeostat'
        for unit in self._homeostat.homeoUnits:
            unit.toggleShowUniselectorAction()
    
    def toggleDiscardData(self):
        "toggle the collects data switch of the homeostat"
        self._homeostat.collectsData = not self.homeostat.collectsData
