'''
Created on Apr 15, 2013

@author: stefano
'''
import threading
import time


class Looping(object):

    def __init__(self):
     self.isRunning = True
     self.timer = 1000
     
    def runForever(self):
       n = 1
       while self.isRunning == True:
           print "Loop number %u" % n
           n += 1
           time.sleep(1/self.timer)
    



def testThreadingTime(runTime):
    l = Looping()
    t = threading.Thread(target = l.runForever)
    start = time.clock()
    t.start()
    time.sleep(runTime)
    l.isRunning = False
    end = time.clock()
    print "I have run for %f seconds" % (end-start) 
