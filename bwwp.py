import sys
import pygame
import random
import time
import dial
import threading
import phonebook
from signal import pause
from os import walk

# Phrase Constants
MIN_PHRASE_DELAY = 120
MAX_PHRASE_DELAY = 500
PHRASE_CLUSTER_DELAY_MIN = 3
PHRASE_CLUSTER_DELAY_MAX = 5
CLUSTER_SIZE_WEIGHTS = [(1, 15), (2, 3), (3, 1)]
CLUSTER_SIZES = sum([[x[0]] * x[1] for x in CLUSTER_SIZE_WEIGHTS], [])

FEEL_PHRASE_CHANCE_PERCENT = 2
PICKUP_PHRASE_CHANCE_PERCENT = 5
MIN_PICKUP_PHRASE_DELAY = 0.7
MAX_PICKUP_PHRASE_DELAY = 2.0

# Telephony constants
PHONE_STATE_IDLE = 0			# Inactive state (e.g. on hook)
PHONE_STATE_DIAL = 1			# Dial tone state
PHONE_STATE_DIAL_DELAY = 2		# Post-Dial Delay (PDD) state
PHONE_STATE_RING = 3			# Ringing state
PHONE_STATE_BUSY = 4			# Busy signal state
PHONE_STATE_OFF_HOOK = 5		# Off-hook signal state
PHONE_STATE_CALL = 6			# Call connected state

# Volume constants
VOICE_VOLUME = 0.2
TELEPHONY_VOLUME = 0.2
SFX_VOLUME = 0.2

# Dialing constants
POST_DIAL_DELAY = 4.0

# State variables
lastDigit = 0
digitEvent = threading.Event()
isPhoneOnHook = True
dialedNumber = ""
hangupEvent = threading.Event()
pddEvent = threading.Event()
pddThread = None
phoneState = PHONE_STATE_IDLE

# Initialize pygame stuff
print "Loading audio engine..."
pygame.mixer.pre_init(frequency = 8000, size = 8, buffer = 1024, channels = 1)
pygame.mixer.init()
pygame.mixer.set_num_channels(4)
pygame.mixer.set_reserved(4)
chanVoice = pygame.mixer.Channel(0)
chanTelephony = pygame.mixer.Channel(1)
chanEffectA = pygame.mixer.Channel(2)
chanEffectB = pygame.mixer.Channel(3)

chanVoice.set_volume(VOICE_VOLUME)
chanTelephony.set_volume(TELEPHONY_VOLUME)
chanEffectA.set_volume(SFX_VOLUME)
chanEffectB.set_volume(SFX_VOLUME)

# Load phrases
def loadSoundDirectory(dir):
	(root, _, contents) = walk(dir).next()
	return [pygame.mixer.Sound(f) for f in [root + "/" + f for f in contents if f.endswith(".wav")]]

phrases = loadSoundDirectory("./sound/etc")
feelPhrases = loadSoundDirectory("./sound/etc/feel")
pickupPhrases = loadSoundDirectory("./sound/etc/pickup")

# Load telephony signals
dialTone = pygame.mixer.Sound("./sound/tones/dial.wav")
ringTone = pygame.mixer.Sound("./sound/tones/ring.wav")
offHookTone = pygame.mixer.Sound("./sound/tones/offhook.wav")
busyTone = pygame.mixer.Sound("./sound/tones/busy.wav")

# Load SFX
pickupSounds = loadSoundDirectory("./sound/pickup")
hangupSounds = loadSoundDirectory("./sound/hangup")

def setPhoneState(state):
	global phoneState, dialedNumber
	if phoneState == state:
		return

	if state == PHONE_STATE_IDLE:
		chanTelephony.stop()
		chanVoice.stop()
		chanEffectA.stop()
		chanEffectB.stop()
		dialedNumber = ""
	elif state == PHONE_STATE_DIAL:
		chanTelephony.play(dialTone, loops = -1)
	elif state == PHONE_STATE_DIAL_DELAY:
		chanTelephony.stop()
	elif state == PHONE_STATE_OFF_HOOK:
		chanTelephony.play(offHookTone, loops = -1)
	elif state == PHONE_STATE_RING:
		chanTelephony.play(ringTone, loops = -1)
	elif state == PHONE_STATE_BUSY:
		chanTelephony.play(busyTone, loops = -1)
	elif state == PHONE_STATE_CALL:
		chanTelephony.stop()
	phoneState = state

def wait_for_channel(ch):
	while ch.get_busy():
		time.sleep(0.1)

def say(phrase):
	chanVoice.play(phrase)
	wait_for_channel(chanVoice)

def load_sound(path):
	return pygame.mixer.Sound(path)

def startPostDialDelay():
	global pddThread

	if pddThread is not None:
		return

	def pddThreadFunc():
		global pddThread
		while True:
			pddEvent.wait(POST_DIAL_DELAY)
			# If PDD event set, the user either dialed another digit or they hung up
			# If PDD event unset, the user has waited after dialing, so call the number
			if pddEvent.is_set() and not isPhoneOnHook:
				pddEvent.clear()
				continue
			else:
				if not isPhoneOnHook:
					onNumberDialed()
			pddEvent.clear()
			break

		pddThread = None

	pddThread = threading.Thread(target = pddThreadFunc)
	pddThread.daemon = True
	pddThread.start()

def is_call():
	return phoneState == PHONE_STATE_CALL

def doIdleSpeech():
	while True:
		# Calculate delay before next cluster and wait
		delay = random.randint(MIN_PHRASE_DELAY, MAX_PHRASE_DELAY + 1)
		time.sleep(delay)

		# Determine cluster size
		clusterSize = random.choice(CLUSTER_SIZES)
		for x in range(clusterSize):
			# Wait for playing to finish
			wait_for_channel(chanVoice)
			# Choose random phrase and play it
			if not isPhoneOnHook:
				phrase = random.choice(phrases)
				chanVoice.play(phrase)
			# Calculate delay before next phrase in cluster and wait
			clusterDelay = random.uniform(PHRASE_CLUSTER_DELAY_MIN, PHRASE_CLUSTER_DELAY_MAX)
			time.sleep(clusterDelay)

def onNumberDialed():
	global isPhoneOnHook
	num = dialedNumber
	print "CALLING: " + num
	if phonebook.exists(num):
		setPhoneState(PHONE_STATE_RING)
		phonebook.call(num)
	else:
		setPhoneState(PHONE_STATE_BUSY)

def read_digit():
	digitEvent.clear()
	digitEvent.wait()
	digitEvent.clear()
	return lastDigit

def onDigit(n):
	global dialedNumber, lastDigit
	print "DIGIT: " + str(n)

	if isPhoneOnHook:
		return

	if phoneState == PHONE_STATE_DIAL:
		setPhoneState(PHONE_STATE_DIAL_DELAY)

	# Set last digit
	lastDigit = n

	# Digit event (for digit wait function)
	digitEvent.set()

	# Number dialing
	if phoneState == PHONE_STATE_DIAL or phoneState == PHONE_STATE_DIAL_DELAY:
		dialedNumber = dialedNumber + str(n)
		dialedLength = len(dialedNumber)
		# PDD event
		pddEvent.set()
		# Trigger PDD thread (if not running)
		startPostDialDelay()

def onTouched():
	if not isPhoneOnHook and not chanVoice.get_busy() and FEEL_PHRASE_CHANCE_PERCENT > random.randint(0, 100):
		phrase = random.choice(feelPhrases)
		chanVoice.play(phrase)

def onPickUp():
	global isPhoneOnHook
	isPhoneOnHook = False

	setPhoneState(PHONE_STATE_DIAL)

	def pickupRespond():
		delay = random.uniform(MIN_PICKUP_PHRASE_DELAY, MAX_PICKUP_PHRASE_DELAY)
		time.sleep(delay)
		if not isPhoneOnHook and not chanVoice.get_busy():
			phrase = random.choice(pickupPhrases)
			chanVoice.play(phrase)

	# Start pickup response on another thread so we don't hold up the GPIO handlers
	if PICKUP_PHRASE_CHANCE_PERCENT > random.randint(0, 100):
		pickupRespondThread = threading.Thread(target = pickupRespond)
		pickupRespondThread.daemon = True
		pickupRespondThread.start()

	print "PICKED UP"

def onHangUp():
	global isPhoneOnHook, dialedNumber
	isPhoneOnHook = True
	dialedNumber = ""
	pddEvent.set()
	hangupEvent.set()
	hangupEvent.clear()
	setPhoneState(PHONE_STATE_IDLE)
	print "HUNG UP"

# Start services
print "Loading directory service..."
phonebook.init(sys.modules[__name__])

print "Loading phone interface..."
dial.on_digit = onDigit
dial.on_touched = onTouched
dial.on_pick_up = onPickUp
dial.on_hang_up = onHangUp
dial.init()

print "Starting speech service..."
phraseThread = threading.Thread(target = doIdleSpeech)
phraseThread.daemon = True
phraseThread.start()

print "Awaiting orders"
try:
	pause()
except KeyboardInterrupt:
	print " Ctrl+C detected."
finally:
	pygame.mixer.quit()
	sys.exit()
