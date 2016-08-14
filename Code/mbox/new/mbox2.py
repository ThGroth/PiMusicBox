import threading
import RPi.GPIO as GPIO
from mpd import MPDClient
import lcddriver
import time
import os

class LED(object):
    """LED"""
    def __init__(self,pin_no):
        self.status = False
        self._gpio_no_ = pin_no
        GPIO.setup(pin_no,GPIO.OUT)
        GPIO.output(pin_no, GPIO.LOW)
    def turn_on(self):
        GPIO.output(self._gpio_no_, GPIO.HIGH)
        self.status = True
    def turn_off(self):
        GPIO.output(self._gpio_no_, GPIO.LOW)
        self.status = False
    def toggle(self):
        if self.status:
            self.turn_off()
        else:
            self.turn_on()
        

class Switch(object):
    """Switch"""
    def __init__(self,pin_no):
        self._gpio_no_ = pin_no
        GPIO.setup(pin_no,GPIO.IN)
    def get_state(self):
        if GPIO.input(self._gpio_no_) == GPIO.HIGH:
            return True
        return False

class LCD(object):
    """docstring for LCD"""
    def __init__(self):
        self._lcd = lcddriver.lcd()
        self._on_time = 1 * 20 # in seconds
        self._standby_time = time.time()+self._on_time
        self.check_light();
    def check_light(self):
        if time.time()>=self._standby_time:
            self.standby()
            threading.Timer(self._on_time-1,self.check_light).start()
        else:
            threading.Timer(self._standby_time-time.time()+1, self.check_light).start()
    def check_light_for_next_song(self,player):
        if not player.currentsong()['title'] == player.lastSong:
            player.lastSong = player.currentsong()['title']
            self._standby_time = time.time()+self._on_time
            self.write_current_song_title(player)
        threading.Timer(5,lambda: self.check_light_for_next_song(player)).start()
    def set_on_time(self,t):
        self._on_time = t
    def center_text(self,text,offset_line=0):
        if (len(text)/3>20):
            self.write_line(text,1+offset_line)
        elif (len(text)/2)>20:
            self.center_text(text[:len(text)/3],0)
            self.center_text(text[len(text)/3:2*len(text)/3],1)
            self.center_text(text[2*len(text)/3],2)
        elif (len(text)>20):    
            self.center_text(text[:len(text)/2],0)
            self.center_text(text[len(text)/2:],1)
        else:
            white = (20-len(text))/2
            self.write_line(" "*white+text+" "*white,1+offset_line)
        self._standby_time = time.time()+self._on_time
    def write_line(self,text,line):
        if (len(text)>20):
            #scrolled text TODO
            self._lcd.lcd_display_string(text[:20],line)
        else:
        	text = text+" "*(20-len(text))
            self._lcd.lcd_display_string(text,line)
        self._standby_time = time.time()+self._on_time
    def write_current_song_title(self,player):
        title = player.currentsong()['title'].split(" - ")
        title[1]+="[]"
        interpret = title[1][:title[1].find("[")]
        album = title[1][title[1].find("[")+1:title[1].find("]")]
        title = title[0]
        display.write_line(interpret,2)
        display.write_line(title,3)
        display.write_line(album,4)
    def clear_display(self):
        self._lcd.lcd_clear()
    def standby(self):
        self._lcd.lcd_backlight("off")
    def turn_off(self):
        self.clear_display()
        self._lcd.lcd_backlight("off")

        
        
#
################## Setup the GPIOs #########################
# 
 
# Use RPi.GPIO BOARD Layout (wie Pin-numbering)
GPIO.setmode(GPIO.BOARD)
        
LedOn = LED(13)
#LedPause = LED(11)

SwitchPlaylist = Switch(16)
SwitchRadio    = Switch(18)

ButtonNextSong  = Switch(12)
ButtonNextAlbum = Switch(22)

#
################## Setup the player #########################
# 
# 
player = MPDClient()               
player.timeout = 10                
player.idletimeout = None          
player.connect("localhost", 6600)  
#Save the last mode, so after a pause it's clear where to resume.
player.LastMode = "undef"
player.lastSong = ""

#
################## Setup the display #########################
# 


display = LCD();
display.check_light_for_next_song(player)


#
#
################ Functions for first setup ######################
#
#
def SetupRadioPlaylist():
    #Remove a playlist "Radio" if existent
    for l in player.listplaylists():
        if l['playlist']=="Radio":
            player.rm("Radio")
            player.clear
    #Recreate the playlist "Radio"
    player.add('http://mp3.wunschradio.de/musicalradio.mp3')
    player.add('http://mp3channels.webradio.rockantenne.de/rockantenne')
    player.save("Radio")

def RadioStationName(song):
    return song['file'][song['file'].rfind('/')+1:]

#
########## Callback functions for controling the buttons ######
#
def ModeChange(channel):
    global LastMode;
    time.sleep(0.2)
    if SwitchRadio.get_state():
        if not player.LastMode == "radio":
            player.load("Radio") #SetupRadioPlaylist() at one time before       
        player.LastMode = "radio"
        display.clear_display()
        #display.write_line("Radio Mode",1)
        player.stop()
        player.play()
        time.sleep(0.1)
        player.lastSong = player.currentsong()['title']
        display.write_line(RadioStationName(player.currentsong()),1)
        display.write_current_song_title(player)
    elif SwitchPlaylist.get_state():
        if not player.LastMode == "playlist":
            player.load("Radio") #SetupRadioPlaylist() at one time before      
        player.LastMode = "playlist"
        display.write_line("Playlist Mode",1)
        if player.status()["state"] == "pause":
            player.pause()    # pause is a toggle command
        else:
            player.play()
    else:
        display.center_text("Pause",1)
        player.pause()

def next(channel):
    time.sleep(0.1)
    if not ButtonNextSong.get_state():
        #Button not pressed long enoug. So ignore.
        return
    #Action depends on mode
    if SwitchRadio.get_state():
        #next radio station in playlist. If last then back to first. 
        player.repeat(1)
        player.next()
    if SwitchPlaylist.get_state():
        player.repeat(0)
        player.next()

def shutdown(channel):
	player.stop()
    player.close()
    display.turn_off()
    #GPIO.cleanup() If so, then the power LED turns out immidiatly 
    os.system("halt");
    sys.exit(0) 

#
#    
########################  Start  ###########################      
#            
#                    
LedOn.turn_on();




###################### Not Done yet.


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

