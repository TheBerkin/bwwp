import time
import dial
from signal import pause
import pygame

# Constants
SOUNDS_PATH = './sound'

# Audio stuff
print "Loading audio engine..."
pygame.mixer.init()
digitSoundNames = ["0.wav", "1.wav", "2.wav", "3.wav", "4.wav", "5.wav", "6.wav", "7.wav", "8.wav", "9.wav"]
digitSounds = []
errorSound = pygame.mixer.Sound("./sound/etc/i_cant.wav")

for n in range(len(digitSoundNames)):
	digitSounds.append(pygame.mixer.Sound(SOUNDS_PATH + "/" + digitSoundNames[n]))

def onDigit(n):
	global digitSounds
	digitSounds[n].play()
	print n

def onBadDigit(pulses):
	global errorSound
	errorSound.play()
	print "(" + str(pulses) + " pulses) I can't..."

print "Loading GPIO interface..."

dial.on_digit = onDigit
dial.on_bad_digit = onBadDigit
dial.init()

print "Listening for dial events..."
pause()
