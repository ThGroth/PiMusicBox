#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
import RPi.GPIO as GPIO
from mpd import MPDClient
import lcddriver
import time
import os
import sys
import signal

#logfile

class Logger(object):
    """docstring for Logger"""
    def __init__(self,fn):
        try:
            self._logfile = open(fn, 'a')
        except OSError as err:
            print("Logger: OS error: {0}".format(err))
            raise
        self._filename=fn
        self._printmode = False
        #sys.stdout = self._logfile
        #sys.stderr = self._logfile
        self.log("Logger started")      

    def log(self,string):
        self._logfile.write(time.strftime("%d.%m. %H:%M:%S", time.localtime(time.time()))+string+"\n")
        self._logfile.close()
        self._logfile = open(self._filename, 'a')

    def write(self,string):
        if self._printmode:
            print(string)
            return
        self.log(string)
    
    def set_print_mode(self):
        self._printmode = True

    def set_log_mode(self):
        self._printmode = False

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
    def __init__(self,pin_no,bounce=200):
        self._gpio_no_ = pin_no
        GPIO.setup(pin_no,GPIO.IN)
        self._bounce = bounce
    def get_state(self):
        if GPIO.input(self._gpio_no_) == GPIO.HIGH:
            return True
        return False
    def set_callback(self,callbackfunc,mode=GPIO.BOTH):
        GPIO.add_event_detect(self._gpio_no_, mode, callback=callbackfunc,bouncetime=self._bounce)  


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
    def light_on(self,player):
        try:
            player.lastSong = player.currentsong()['title']
            self._standby_time = time.time()+self._on_time
            self.write_current_song_title(player)
        except Exception as inst:
            Log.write("Error in \"light_on\": "+str(type(inst)))
    def check_light_for_next_song(self,player):
        try:
            if player.status()['state']=="play":
                if not player.currentsong()['title'] == player.lastSong: 
                    player.lastSong = player.currentsong()['title']
                    self._standby_time = time.time()+self._on_time
                    self.write_current_song_title(player)
        except Exception as inst:
            Log.write("Error in \"check_light_for_next_song\": "+str(type(inst)))
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
        song = player.currentsong()
        title = ""
        interpret = ""
        album = ""
        if song.has_key('title'):
            title = song['title']
        titleAr = title.split(" - ")
        if len(titleAr)>1:
            titleAr[1]+="[]"
            interpret = titleAr[1][:titleAr[1].find("[")]
            album = titleAr[1][titleAr[1].find("[")+1:titleAr[1].find("]")]
            title = titleAr[0]
        if title == "":
            Log.write("Error in write_current_song_title: Empty title")
        if song.has_key("album"):
            album = song["album"]
        if song.has_key("artist"):
            interpret = song["artist"]    
        self.write_line(interpret,2)
        self.write_line(title,3)
        self.write_line(album,4)
    def clear_display(self):
        self._lcd.lcd_clear()
    def clear_line(self,line):
        self.write_line(" ",line)
    def standby(self):
        self._lcd.lcd_backlight("off")
    def turn_off(self):
        self.clear_display()
        self._lcd.lcd_backlight("off")


class ShutdownManager(object):
    """docstring for ShutdownManager"""
    def __init__(self,player,display,standby_time):
        self._standby_time = standby_time
        self._shutdownTimer = threading.Timer(self._standby_time,self.shutdown)
    def stop_shutdown(self):
        self._shutdownTimer.cancel()
    def eventually_shutdown(self):
        self._shutdownTimer = threading.Timer(self._standby_time,self.shutdown)
        self._shutdownTimer.start()
        return time.strftime("%H:%M", time.localtime(time.time()+self._standby_time)) 
    def shutdown(self):
        try:
            player.stop()
        except Exception as inst:
            Log.write("Error in \"shutdown\": player.stop()"+str(type(inst)))
        
        try:
            player.close()
        except Exception as inst:
            Log.write("Error in \"shutdown\": player.close()"+str(type(inst)))
        
        display.turn_off()
        Log.write("Auschalten..")
        os.system("halt");
        os._exit(0)    
        #GPIO.cleanup() If so, then the power LED turns out immidiatly 
        #exit(0) 

def restartMusicPi():
    Log.write("Restart requested...")
    display.turn_off()
    try:
        player.stop()
        player.close()
    except Exception as inst:
        Log.write("Error in \"restartMusicPi\": player.close()"+str(type(inst)))   
    GPIO.cleanup()
    Log.write(str(os.system("service mpd restart")))
    prog = "/home/pi/PiMusicBox/Code/mbox2.py"
    os.execl(prog,prog)    

def stopMusicPi(cleanGPIOs):
    Log.write("stop requested...")
    display.turn_off()
    try:
        player.stop()
        player.close()
    except Exception as inst:
        Log.write("Error in \"StopMusicPi\": player.close()"+str(type(inst)))   
    if cleanGPIOs:
        GPIO.cleanup()
    os._exit(0)    



Log = Logger('/var/log/PiMusicBox.log')
#Log.set_print_mode()
Log.set_log_mode()
        
#
################## Setup the GPIOs #########################
# 
 
# Use RPi.GPIO BOARD Layout (as Pin-numbering)

try:
    GPIO.setmode(GPIO.BOARD)
except Exception as inst:
    Log.write("Error in Setting up the GPIO trying again soon..."+str(type(inst)))            
    time.sleep(2)
    restartMusicPi()
        
LedOn = LED(13)
LedOn.turn_off()
#LedPause = LED(11)

SwitchPlaylist = Switch(16,400)
SwitchRadio    = Switch(18,400)

ButtonNextSong  = Switch(12)
ButtonLight = Switch(22)

#
################## Setup the player #########################
# 
# 
try:
    player = MPDClient()   
except Exception as inst:
    Log.write("Error in Setting up the player trying again soon..."+str(type(inst)))            
    time.sleep(2)
    restartMusicPi()

Log.write("Player setup part 1 succesfull")
player.timeout = 10                
player.idletimeout = None          
player.connect("localhost", 6600)  
#Save the last mode, so after a pause it's clear where to resume.
player.LastMode = "undef"
player.lastSong = ""
player.PlaylistsName = ""
Log.write("Player setup succesfull")


#
################## Setup the display #########################
# 


try:
    display = LCD();
except Exception as inst:
    Log.write("Error in Setting up the player trying again soon..."+str(type(inst)))            
    time.sleep(2)
    restartMusicPi()


display.check_light_for_next_song(player)
Log.write("Display setup succesfull")
#
################## Shutdown Manager #########################
# 


SM = ShutdownManager(player,display,10*60)


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

def RadioStationName(player):
    try:
        song = player.currentsong()
        station = song['file'][song['file'].rfind('/')+1:]
    except Exception as inst:
        Log.write("Error in \"RadioStationName\": "+str(type(inst)))
        station = "radio station"
    return station

#
########## Callback functions for controling the buttons ######
#
def ModeChange(channel):
    time.sleep(0.2)
    AktualTime = time.strftime("%H:%M:%S", time.gmtime(time.time())) 
    if SwitchRadio.get_state():
        Log.write("Radio Mode")
        SM.stop_shutdown()
        if not player.LastMode == "radio":
            Log.write("Reload radio playlist")
            try:
                player.clear()
            except Exception as inst:
                Log.write("Error in \"ModeChange\": player.clear()"+str(type(inst))) 
            try:
                player.load("Radio") #SetupRadioPlaylist() at one time before       
            except Exception as inst:
                Log.write("Error in \"ModeChange\": player.load(\"Radio\")"+str(type(inst))) 
            
        player.LastMode = "radio"
        display.clear_display()
        #display.write_line("Radio Mode",1)
        try:
           player.stop() 
        except Exception as inst:
            Log.write("Error in \"ModeChange\": player.stop()"+str(type(inst))) 
        try:
           player.play()
        except Exception as inst:
            Log.write("Error in \"ModeChange\": player.play()"+str(type(inst))) 
        time.sleep(0.1)
        try:
            player.lastSong = player.currentsong()['title']
        except Exception as inst:
            Log.write("Error in \"ModeChange\": "+str(type(inst)))
            player.lastSong = ""
        stationName = RadioStationName(player)
        #if len(stationName) <= 20-5:
        #    stationName = stationName+" "*(15-len(stationName))+AktualTime
        display.write_line(stationName,1)
        display.write_current_song_title(player)
    elif SwitchPlaylist.get_state():
        Log.write("Playlist Mode  ")
        SM.stop_shutdown()
        if not player.LastMode == "playlist":
            Playlists = []
            try:
                playerplaylists = player.listplaylists();
            except Exception as inst:
                Log.write("Error in \"ModeChange\": player.listplaylists"+str(type(inst)))
                playerplaylists = [];
            for P in playerplaylists:
                if not P['playlist']=="Radio": 
                    Playlists.append(P['playlist'])
            if len(Playlists)==0:
                Log.write("Error ModeChange: No Playlists")
                return
            player.clear()
            player.PlaylistsName = Playlists[0]
            player.PlaylistNumber = 0
            player.load(player.PlaylistsName) 
        player.LastMode = "playlist"
        display.clear_display()
        display.write_line(player.PlaylistsName,1)
        if player.status()["state"] == "pause":
            try:
                player.pause()    # pause is a toggle command
            except Exception as inst:
                Log.write("Error in \"ModeChange\": player.pause()"+str(type(inst))) 
        else:
            try:
                player.play()
            except Exception as inst:
                Log.write("Error in \"ModeChange\": player.play()"+str(type(inst))) 
        time.sleep(0.1)
        display.write_current_song_title(player)
    else:
        try:
            playerstatusstate = player.status()['state']    # pause is a toggle command
        except Exception as inst:
            Log.write("Error in \"ModeChange\": player.status()[state]"+str(type(inst))) 
            playerstatusstate = "pause"
        if not playerstatusstate == "pause":
            Log.write("Pause Mode")
            display.center_text("Pause",1)
            display.clear_line(3)
            display.write_line("Ausschalten um "+SM.eventually_shutdown(),4);
            try:
                player.pause()    # pause is a toggle command
            except Exception as inst:
                Log.write("Error in \"ModeChange\": player.pause()"+str(type(inst))) 

def next(channel):
    time.sleep(0.1)
    if not ButtonNextSong.get_state():
        #Button not pressed long enoug. So ignore.
        return
    #Action depends on mode
    if SwitchRadio.get_state():
        #next radio station in playlist. If last then back to first. 
        try:
            player.repeat(1)
        except Exception as inst:
            Log.write("Error in \"next\": player.repeat(1)"+str(type(inst))) 
        try:
            player.next()
        except Exception as inst:
            Log.write("Error in \"next\": player.next()"+str(type(inst))) 
        time.sleep(0.1)
        stationName = RadioStationName(player.currentsong())
        display.write_line(stationName,1)
        display.light_on(player)
    if SwitchPlaylist.get_state():
        try:
            player.repeat(0)
        except Exception as inst:
            Log.write("Error in \"next\": player.repeat(1)"+str(type(inst))) 
        try:
            player.next()
        except Exception as inst:
            Log.write("Error in \"next\": player.next()"+str(type(inst))) 
        time.sleep(0.1)
        display.light_on(player)
        time.sleep(1)
        if not ButtonNextSong.get_state():
            #realy only next song
            return
        #next Album
        Playlists = []
        try:
            playerplaylists = player.listplaylists();
        except Exception as inst:
            Log.write("Error in \"Next\": player.listplaylists"+str(type(inst)))
            playerplaylists = [];
        for P in playerplaylists:
            if not P['playlist']=="Radio": 
                Playlists.append(P['playlist'])
        if len(Playlists)==0:
            Log.write("Error ModeChange: No Playlists")
            return
        player.PlaylistNumber = (player.PlaylistNumber+1) % len(Playlists) 
        try:
            player.clear()
        except Exception as inst:
            Log.write("Error in \"next\": player.clear()"+str(type(inst))) 
        player.PlaylistsName = Playlists[player.PlaylistNumber]
        try:
            player.load(player.PlaylistsName)
        except Exception as inst:
            Log.write("Error in \"next\": player.load(player.PlaylistsName)"+str(type(inst))) 
        display.clear_display()
        display.write_line(player.PlaylistsName,1)
        try:
            player.play()
        except Exception as inst:
            Log.write("Error in \"next\": player.play()"+str(type(inst))) 
        time.sleep(0.1)
        display.light_on(player)

def light(channel):
    time.sleep(0.05)
    if not ButtonLight.get_state():
        #Button not pressed long enoug. So ignore.
        return
    display.light_on(player)
    time.sleep(1)
    if not ButtonLight.get_state():
        #Button not pressed long enoug for restart
        return
    #Restart the program
    restartMusicPi()

def signal_term_handler(signal, frame):
    Log.write("got SIGTERM")
    StopMusicPi(false)

def exit_gracefully(signum, frame):
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if raw_input("\nReally quit? (y/n)> ").lower().startswith('y'):
            Log.write("got SIGINT")
            StopMusicPi(true)

    except KeyboardInterrupt:
        Log.write("got SIGINT and pressure")
        StopMusicPi(true)
    # restore the exit gracefully handler here    
    signal.signal(signal.SIGINT, exit_gracefully)

#
#    
########################  Start  ###########################      
#            
#                    
LedOn.turn_on()
ModeChange(0)
Log.write("Starting Mode")

SwitchPlaylist.set_callback(ModeChange);
SwitchRadio.set_callback(ModeChange);
ButtonNextSong.set_callback(next,GPIO.RISING);
ButtonLight.set_callback(light,GPIO.RISING);
#Handler for kill request
signal.signal(signal.SIGTERM, signal_term_handler)
#Handler for CTRL-C request. Store the default one in original_sigint
original_sigint = signal.getsignal(signal.SIGINT)
signal.signal(signal.SIGINT, exit_gracefully)

while true:
    sleep(1)
    pass





