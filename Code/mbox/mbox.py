import RPi.GPIO as GP
import time
import os

ledon=16
ledpause=12

buttonplay=15
buttonnext=13
buttonstop=11

GP.setmode(GP.BOARD)
GP.setup(ledon,GP.OUT)
GP.setup(ledpause,GP.OUT)

GP.setup(buttonnext,GP.IN)
GP.setup(buttonplay,GP.IN)
GP.setup(buttonstop,GP.IN)

GP.output(ledon,True)
GP.output(ledpause,False)

os.system("mpc play")
os.system("mpc play")

def pause(channel):
        time.sleep(0.2)
        if (GP.input(buttonplay)):
                print "Resume playing"
                GP.output(ledpause,False)
                os.system("mpc play")
        else:
                print "Pause playing"
                GP.output(ledpause,True)
                os.system("mpc pause")
        print "In pause. Aufgerufen mit Channel:"+str(channel)+"Der Wert von buttonplay ist:"+str(GP.input(buttonplay))

def next(channel):
        print "In nexttitle. Aufgerufen mit Channel:"+str(channel)+"Der Wert von buttonnext ist:"+str(GP.input(buttonnext))
        time.sleep(4)
        print "jetzt niht mehr"


GP.add_event_detect(buttonplay,GP.BOTH,callback=pause,bouncetime=200)
GP.add_event_detect(buttonnext,GP.FALLING,callback=next,bouncetime=200)
try:
        GP.wait_for_edge(buttonstop, GP.FALLING)
        print "In end. Der Wert von buttonstop ist:"+str(GP.input(buttonstop))
        print "stopping"
        os.system("mpc stop")
except KeyboardInterrupt:
        GP.cleanup()
        os.system("mpc stop")
GP.cleanup()
