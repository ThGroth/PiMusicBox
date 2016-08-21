#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
import RPi.GPIO as GPIO
from mpd import MPDClient
import lcddriver
import time
import os

#logfile

class Logger(object):
    """docstring for Logger"""
    def __init__(self,):
        self._logfile = open(fn, 'w')
        self._printmode = False
    
    def log(self,string):
        self._logfile.write(time.strftime("%d.%m. %H:%M:%S", time.gmtime(time.time()))+string+"\n")

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
        return time.strftime("%H:%M", time.gmtime(time.time()+self._standby_time)) 
    def shutdown(self):
        player.stop()
        player.close()
        display.turn_off()
        Log.write("Auschalten..")
        os.system("halt");
        os._exit(0)    
        #GPIO.cleanup() If so, then the power LED turns out immidiatly 
        #exit(0) 


Log = Logger('/var/log/PiMusicBox.log')
#L.set_print_mode()
L.set_log_mode()
        
#
################## Setup the GPIOs #########################
# 
 
# Use RPi.GPIO BOARD Layout (wie Pin-numbering)
GPIO.setmode(GPIO.BOARD)
        
LedOn = LED(13)
#LedPause = LED(11)

SwitchPlaylist = Switch(16,400)
SwitchRadio    = Switch(18,400)

ButtonNextSong  = Switch(12)
ButtonLight = Switch(22)

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
player.PlaylistsName = ""

#
################## Setup the display #########################
# 


display = LCD();
display.check_light_for_next_song(player)

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

def RadioStationName(song):
    return song['file'][song['file'].rfind('/')+1:]

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
            player.clear()
            player.load("Radio") #SetupRadioPlaylist() at one time before       
        player.LastMode = "radio"
        display.clear_display()
        #display.write_line("Radio Mode",1)
        player.stop()
        player.play()
        time.sleep(0.1)
        if player.currentsong().has_key('title'):
            player.lastSong = player.currentsong()['title']
        else:
            player.lastSong = ""
        stationName = RadioStationName(player.currentsong())
        #if len(stationName) <= 20-5:
        #    stationName = stationName+" "*(15-len(stationName))+AktualTime
        display.write_line(stationName,1)
        display.write_current_song_title(player)
    elif SwitchPlaylist.get_state():
        Log.write("Playlist Mode  ")
        SM.stop_shutdown()
        if not player.LastMode == "playlist":
            Playlists = []
            for P in player.listplaylists():
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
            player.pause()    # pause is a toggle command
        else:
            player.play()
        display.write_current_song_title(player)
    else:
        if not player.status()['state'] == "pause":
            Log.write("Pause Mode")
            display.center_text("Pause",1)
            display.clear_line(3)
            display.write_line("Ausschalten um "+SM.eventually_shutdown(),4);
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
        time.sleep(0.1)
        stationName = RadioStationName(player.currentsong())
        display.write_line(stationName,1)
        display.light_on(player)
    if SwitchPlaylist.get_state():
        player.repeat(0)
        player.next()
        time.sleep(0.1)
        display.light_on(player)
        time.sleep(1)
        if not ButtonNextSong.get_state():
            #realy only next song
            return
        #next Album
        Playlists = []
        for P in player.listplaylists():
            if not P['playlist']=="Radio": 
                Playlists.append(P['playlist'])
        if len(Playlists)==0:
            Log.write("Error ModeChange: No Playlists")
            return
        player.PlaylistNumber = (player.PlaylistNumber+1) % len(Playlists) 
        player.clear()
        player.PlaylistsName = Playlists[player.PlaylistNumber]
        player.load(player.PlaylistsName)
        display.clear_display()
        display.write_line(player.PlaylistsName,1)
        player.play()
        time.sleep(0.1)
        display.light_on(player)


def light(channel):
    time.sleep(0.05)
    if not ButtonLight.get_state():
        #Button not pressed long enoug. So ignore.
        return
    display.light_on(player)
    
#
#    
########################  Start  ###########################      
#            
#                    
LedOn.turn_on();
ModeChange(0)
SwitchPlaylist.set_callback(ModeChange);
SwitchRadio.set_callback(ModeChange);
ButtonNextSong.set_callback(next,GPIO.RISING);
ButtonLight.set_callback(light,GPIO.RISING);






