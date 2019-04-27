import sys
import bwwpaudio as ba
import random
import time
import dial
import ringer
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

# Initialize audio engine
print "Loading audio engine..."
ba.init()

# Load phrases
def loadSoundDirectory(dir):
	(root, _, contents) = walk(dir).next()
	return [ba.Sound(f) for f in [root + "/" + f for f in contents if f.endswith(".wav")]]

phrases = loadSoundDirectory("./sound/etc")
feelPhrases = loadSoundDirectory("./sound/etc/feel")
pickupPhrases = loadSoundDirectory("./sound/etc/pickup")
readyPhrase = ba.Sound("./sound/status/ready.wav")

# Load telephony signals
dialTone = ba.Sound("./sound/tones/dial.wav")
ringTone = ba.Sound("./sound/tones/ring.wav")
offHookTone = ba.Sound("./sound/tones/offhook.wav")
busyTone = ba.Sound("./sound/tones/busy.wav")

# Load SFX
pickupSounds = loadSoundDirectory("./sound/pickup")
hangupSounds = loadSoundDirectory("./sound/hangup")

# Initialize ringer
ringer.init()

def setPhoneState(state):
	global phoneState, dialedNumber
	if phoneState == state:
		return

	if state == PHONE_STATE_IDLE:
		ba.stop()
		dialedNumber = ""
		digitEvent.set()
		digitEvent.clear()
	elif state == PHONE_STATE_DIAL:
		ba.play_loop(ba.CHAN_TELEPHONY, dialTone)
	elif state == PHONE_STATE_DIAL_DELAY:
		ba.stop(ba.CHAN_TELEPHONY)
	elif state == PHONE_STATE_OFF_HOOK:
		ba.play_loop(ba.CHAN_TELEPHONY, offHookTone)
	elif state == PHONE_STATE_RING:
		ba.play_loop(ba.CHAN_TELEPHONY, ringTone)
	elif state == PHONE_STATE_BUSY:
		ba.stop()
		ba.play_loop(ba.CHAN_TELEPHONY, busyTone)
	elif state == PHONE_STATE_CALL:
		ba.stop(ba.CHAN_TELEPHONY)
	phoneState = state

def set_ring_state(isRinging):
	if isRinging:
		ringer.on()
	else:
		ringer.off()

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
			ba.wait(ba.CHAN_VOICE)
			# Choose random phrase and play it
			if not isPhoneOnHook:
				phrase = random.choice(phrases)
				ba.play(ba.CHAN_VOICE, phrase)
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
	if not isPhoneOnHook and not ba.busy(ba.CHAN_VOICE) and phoneState == PHONE_STATE_DIAL and FEEL_PHRASE_CHANCE_PERCENT > random.randint(0, 100):
		phrase = random.choice(feelPhrases)
		ba.play(ba.CHAN_VOICE, phrase)

def onPickUp():
	global isPhoneOnHook
	isPhoneOnHook = False

	setPhoneState(PHONE_STATE_DIAL)

	def pickupRespond():
		delay = random.uniform(MIN_PICKUP_PHRASE_DELAY, MAX_PICKUP_PHRASE_DELAY)
		time.sleep(delay)
		if not isPhoneOnHook and not ba.busy(ba.CHAN_VOICE):
			phrase = random.choice(pickupPhrases)
			ba.play(ba.CHAN_VOICE, phrase)

	# Start pickup response on another thread so we don't hold up the GPIO handlers
	if PICKUP_PHRASE_CHANCE_PERCENT > random.randint(0, 100):
		pickupRespondThread = threading.Thread(target = pickupRespond)
		pickupRespondThread.daemon = True
		pickupRespondThread.start()

def onHangUp():
	global isPhoneOnHook, dialedNumber
	isPhoneOnHook = True
	dialedNumber = ""
	pddEvent.set()
	hangupEvent.set()
	hangupEvent.clear()
	setPhoneState(PHONE_STATE_IDLE)

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

print "Ready"
ba.say_wait(readyPhrase)
ba.set_volume(0.5)

try:
	pause()
except KeyboardInterrupt:
	print " Ctrl+C detected."
finally:
	ba.quit()
	sys.exit()
