import time
from gpiozero import Button
from signal import pause
import pygame

# Constants
DIGITS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
SOUNDS_PATH = './sound'

# GPIO inputs
dial = Button(2, bounce_time = 0.025)
dialSwitch = Button(4, bounce_time = 0.1)

# Dial variables
dialPulses = 0
isDialSwitchOn = False

# Audio stuff
pygame.mixer.init()
digitSoundNames = ["1.wav", "2.wav", "3.wav", "4.wav", "5.wav", "6.wav", "7.wav", "8.wav", "9.wav", "0.wav"]
digitSounds = []
errorSound = pygame.mixer.Sound("./sound/etc/i_cant.wav")

for n in range(len(DIGITS)):
	digitSounds.append(pygame.mixer.Sound(SOUNDS_PATH + "/" + digitSoundNames[n]))


def onDialOn():
	global isDialSwitchOn, dialPulses
	if isDialSwitchOn:
		dialPulses += 1


def onDialSwitchOff():
	global dialPulses, isDialSwitchOn, errorSound
	#print "Dial switch off"
	isDialSwitchOn = False
	digitIndex = dialPulses - 1
	#print "Pulses: ", dialPulses
	if digitIndex >= 0 and digitIndex < len(DIGITS):
		digit = DIGITS[digitIndex]
		digitSounds[digitIndex].play()
		print digit
	else:
		print "(" + str(dialPulses) + " pulses) I can't..."
		errorSound.play()
	dialPulses = 0

def onDialSwitchOn():
	global isDialSwitchOn
	#print "Dial switch on"
	isDialSwitchOn = True

dial.when_released = onDialOn
dialSwitch.when_pressed = onDialSwitchOn
dialSwitch.when_released = onDialSwitchOff

print "Listening for dial events..."
pause()
