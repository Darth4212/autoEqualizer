#!/usr/bin/python

# autoEqualizer - Script to load equalizer presets ondemand based on what genre of track is playing
# Copyright (C) 2007 Ritesh Raj Sarraf <rrs@researchut.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import threading
import signal

from time import sleep

try:
    from qt import *
except ImportError:
    sys.stderr.write("Error! I need the Python Qt modules. Please install the python-qt3 package.\n")

DEBUG=1
MODE=1

try:
    from dcopext import DCOPClient, DCOPApp
except ImportError:
    sys.stderr.write("Error! I can't find the dcopext module.\n")
    os.popen( "kdialog --sorry 'PyKDE3 (KDE3 bindings for Python) is required for this script.'" )
    raise

if DEBUG:
    if os.path.isfile(__file__+".log") is True:
	try:
	    os.remove(__file__+".log")
	except IOError:
	    sys.stderr.write("Couldn't remove the file. Do you have ownership.\n")
	
    f = open(__file__+".log", 'a')

#class Notification( QCustomEvent ):
class Notification( QCustomEvent ):
    __super_init = QCustomEvent.__init__
    def __init__( self, str ):
        self.__super_init(QCustomEvent.User + 1)
        self.string = str

class autoEqualizer( QApplication):
    """ The main application, also sets up the Qt event loop """

    def __init__( self, args, mode ):
        QApplication.__init__( self, args )
        
        # create a new DCOP-Client
        self.client = DCOPClient()

	# Select what mode we want to run in
	# 1 => shortStatusMessage
	# 2 => popupMessage
	self.mode = mode
        
        # connect the client to the local DCOP-Server
        if self.client.attach() is not True:
            os.popen( "kdialog --sorry 'Could not connect to local DCOP server. Something weird happened.'" )
            sys.exit(1)
            
        # create a DCOP-Application-Object to talk to Amarok
        self.amarok = DCOPApp('amarok', self.client)
        debug( "Started.\n" )
        
        # Start separate thread for reading data from stdin
        self.stdinReader = threading.Thread( target = self.readStdin )
        self.stdinReader.start()
        
        self.readSettings()

    def osCommands(self, command):
	    # Execute the command and return the exit value
	    # Once the extraction problem is root-caused, we can fix this easily.
	    os.environ['__autoEqualizer_command'] = command
	    try:
		    old_environ = os.environ['LANG']
	    except KeyError:
		    old_environ = "C"
		    os.environ['LANG'] = "C"

		    #if os.system(command '> __autoEqualizer_output 2>&1') != 0:
		    #	    debug("Couldn't execute the command using the dcopy command interface also.")

    def saveState(self, sessionmanager):
        # script is started by amarok, not by KDE's session manager
        debug("We're in saveState. We should be avoiding session starts with this in place.\n")
        sessionmanager.setRestartHint(QSessionManager.RestartNever)

    def readSettings( self ):
        """ Reads settings from configuration file """

        try:
            foovar = config.get( "General", "foo" )

        except:
            debug( "No config file found, using defaults.\n" )


############################################################################
# Stdin-Reader Thread
############################################################################

    def readStdin( self ):
        """ Reads incoming notifications from stdin """

        while True:
            # Read data from stdin. Will block until data arrives.
            line = sys.stdin.readline()
            debug ("Line is %s.\n" % (line) )

            if line:
                qApp.postEvent( self, Notification(line) )
            else:
                break


############################################################################
# Notification Handling
############################################################################

    def customEvent( self, notification ):
        """ Handles notifications """

        string = QString(notification.string)
        debug( "Received notification: " + str( string ) + "\n" )

        if string.contains( "configure" ):
            self.configure()

        if string.contains( "engineStateChange: play" ):
            debug("Play event triggered.\n")
            self.engineStatePlay()

        if string.contains( "engineStateChange: idle" ):
            self.engineStateIdle()

        if string.contains( "engineStateChange: pause" ):
            self.engineStatePause()

        if string.contains( "engineStateChange: empty" ):
            self.engineStatePause()

        if string.contains( "trackChange" ):
            debug("Track change event occured.\n")
            self.trackChange()

# Notification callbacks. Implement these functions to react to specific notification
# events from Amarok:

    def configure( self ):
        debug( "configuration" )

        self.dia = ConfigDialog()
        self.dia.show()
        self.connect( self.dia, SIGNAL( "destroyed()" ), self.readSettings )

    def engineStatePlay( self ):
        """ Called when Engine state changes to Play """
	debug ("Enable the equalizer to On")
	self.equalizerState()

    def engineStateIdle( self ):
        """ Called when Engine state changes to Idle """
        pass

    def engineStatePause( self ):
        """ Called when Engine state changes to Pause """
        pass

    def engineStateEmpty( self ):
        """ Called when Engine state changes to Empty """
        pass

    def trackChange( self ):
        """ Called when a new track starts """
        debug ("Track Change event called.\n")
        self.setEqualizer()


    def getGenre(self):
        # get the Genre from the current song.
        retval, genre = self.amarok.player.genre()
	genre = genre.__str__()
        if retval is not True:
            debug("I couldn't get the genre using the library. Is Amarok running?")
	    #TODO: debug("Will try using the dcop commandline interface")
        else:
            return genre

    def setEqualizer(self):
        # set the equalizer accordingly
        # TODO: It would be good to have a list of preset equalizers
        # and match them
        self.genre = self.getGenre()
        retval, success = self.amarok.player.setEqualizerPreset(self.genre)
        if retval is not True:
            debug("I couldn't get the equalizer preset. Is Amarok running?")
        else:
	    if self.mode == 1:
		    self.amarok.playlist.shortStatusMessage("Activated equalizer preset -> %s" % (self.genre) )
		    debug ("Activated equalizer preset -> %s\n" % (self.genre) )
	    elif self.mode == 2:
		    self.amarok.playlist.popupMessage("Activated equalizer preset -> %s" % (self.genre) )
		    debug ("Activated equalizer preset -> %s\n" % (self.genre) )
	    else:
		    # Default Mode
		    self.amarok.playlist.popupMessage("Activated equalizer preset -> %s" % (self.genre) )
		    debug ("Activated equalizer preset -> %s\n" % (self.genre) )

    def equalizerState(self):
        # check if the equalizer is on or not
        # FIXME: Currently, it looks like dcopext has a bug
        # even though I try to set the equalizer to on, it doesn't
        # so for now we will check if the equalizer is on or not and
        # enable it using the dcop command
        retval, equalizerState = self.amarok.player.equalizerEnabled()
        if not equalizerState:
            os.system( "dcop amarok player setEqualizerEnabled True" )
	    debug("Enable the Equalizer.")



############################################################################

def debug( message ):
    """ Prints debug message to stdout """
    f.writelines(message)
    f.flush()

    #print debug_prefix + " " + message

def onStop(signum, stackframe):
    """ Called when script is stopped by user """
    debug("I'm in onStop.\n")
    debug("We need to kill the process, otherwise it strays around even if amarok exits.\n")
    os.kill(os.getpid(), 9)

def main( ):
    app = autoEqualizer ( sys.argv, MODE )

    app.exec_loop()

if __name__ == "__main__":
    mainapp = threading.Thread(target=main)
    mainapp.start()
    signal.signal(signal.SIGTERM, onStop)
    # necessary for signal catching
    while 1: sleep(120)
