#! /usr/bin/python
import sys
import bwwpaudio as ba
import random
import time
import dial
import ringer
import threading
import schedule
from datetime import datetime
import phonebook
from signal import pause
from os import walk

# Phrase Constants
MIN_PHRASE_DELAY = 120			# Minimum number of seconds between phrase clusters
MAX_PHRASE_DELAY = 500			# Maximum number of seconds between phrase clusters
PHRASE_CLUSTER_DELAY_MIN = 2		# Minimum delay between phrases in cluster
PHRASE_CLUSTER_DELAY_MAX = 5		# Maximum delay between phrases in cluster

CLUSTER_SIZE_WEIGHTS = [(1, 15), (2, 3), (3, 1)]				# Weight distribution for phrase cluster sizes
CLUSTER_SIZES = sum([[x[0]] * x[1] for x in CLUSTER_SIZE_WEIGHTS], [])		# Weight-multiplied phrase cluster size pool

FEEL_PHRASE_CHANCE_PERCENT = 2		# Chance % of dial touch phrase
PICKUP_PHRASE_CHANCE_PERCENT = 5	# Chance % of pickup phrase
MIN_PICKUP_PHRASE_DELAY = 0.7		# Minimum time before pickup phrase plays
MAX_PICKUP_PHRASE_DELAY = 2.0		# Maximum time before pickup phrase plays

# Dark Constants
DARK_SCHEDULE = schedule.Hours('1111110000000000000000000')
DARK_STATIC_FADE_MS = 600000
DARK_STATIC_VOLUME = 0.2
DARK_VOICE_VOLUME = 0.9
DARK_SFX_TOKEN = 'dark_spkr'

# Telephony constants
PHONE_STATE_IDLE = 0			# Inactive state (e.g. on hook)
PHONE_STATE_DIAL = 1			# Dial tone state
PHONE_STATE_DIAL_DELAY = 2		# Post-Dial Delay (PDD) state
PHONE_STATE_RING = 3			# Ringing state
PHONE_STATE_BUSY = 4			# Busy signal state
PHONE_STATE_OFF_HOOK_MSG = 5		# Off-hook message state
PHONE_STATE_OFF_HOOK = 6		# Off-hook signal state
PHONE_STATE_CALL = 7			# Call connected state

# Time constants
POST_DIAL_DELAY = 4.0			# Post-Dial Delay (PDD) time in seconds
OFF_HOOK_MESSAGE_DELAY = 20.0		# Seconds before off-hook message plays
OFF_HOOK_MESSAGE_INTERVAL = 8.0		# Seconds before off-hook message repeats
OFF_HOOK_MESSAGE_LOOPS = 2		# Number of times to reepat off-hook message before scaring user to death

# State variables
lastDigit = 0				# Last digit dialed
digitEvent = threading.Event()		# Event triggered by dialing a digit
isPhoneOnHook = True			# Flag if phone is on the hook
dialedNumber = ""			# String containing the currently dialed phone number
pickupEvent = threading.Event()		# Event triggered by picking up the receiver
hangupEvent = threading.Event()		# Event triggered by hanging up
pddEvent = threading.Event()		# Event triggered by PDD expiring
pddThread = None			# PDD thread
phoneState = PHONE_STATE_IDLE		# Current state of the phone
offHookCancelEvent = threading.Event()	# Event triggered by off-hook message being cancelled

# Initialize audio engine
print "Loading audio engine..."
ba.init()

# Load phrases
phrases = ba.load_sound_dir("./sound/etc/phrases")
feelPhrases = ba.load_sound_dir("./sound/etc/feel")
pickupPhrases = ba.load_sound_dir("./sound/etc/pickup")
readyPhrase = ba.Sound("./sound/status/ready.wav")
offHookPhraseA = ba.Sound("./sound/status/off_hook_message_a.wav")
offHookPhraseB = ba.Sound("./sound/status/off_hook_message_b.wav")

# Load telephony signals
dialTone = ba.Sound("./sound/tones/dial.wav")
ringTone = ba.Sound("./sound/tones/ring.wav")
offHookTone = ba.Sound("./sound/tones/offhook.wav")
busyTone = ba.Sound("./sound/tones/busy.wav")

# Load SFX
pickupSounds = ba.load_sound_dir("./sound/pickup")
hangupSounds = ba.load_sound_dir("./sound/hangup")
ambStatic = ba.Sound("./sound/ambient/amb_static.wav", DARK_STATIC_VOLUME)
pulseOpenSound = ba.Sound("./sound/tones/pulse.wav", 0.5)
pulseCloseSound = ba.Sound("./sound/tones/pulse.wav", 0.3)

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
		ba.stopsfx()
		ba.stop_token(DARK_SFX_TOKEN)
	elif state == PHONE_STATE_DIAL_DELAY:
		ba.stop(ba.CHAN_TELEPHONY)
	elif state == PHONE_STATE_OFF_HOOK_MSG:
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
	(ringer.on if isRinging else ringer.off)()

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
		if DARK_SCHEDULE.is_now() and phoneState == PHONE_STATE_IDLE:
			ba.channels[ba.CHAN_SPKR_A].unmute()
			if not ba.busy(ba.CHAN_SPKR_A):
				ba.play_loop(ba.CHAN_SPKR_A, ambStatic, fade_ms = DARK_STATIC_FADE_MS, token = DARK_SFX_TOKEN)

		# Calculate delay before next cluster and wait
		delay = random.randint(MIN_PHRASE_DELAY, MAX_PHRASE_DELAY + 1)
		time.sleep(delay)

		# Check if it's the right time to talk
		dt = datetime.now()

		if DARK_SCHEDULE.is_now() and phoneState == PHONE_STATE_IDLE:
			# Determine phrase cluster size
			clusterSize = random.choice(CLUSTER_SIZES)
			for x in range(clusterSize):
				# Wait for playing to finish
				ba.wait(ba.CHAN_SPKR_B)
				# Choose random phrase and play it
				phrase = random.choice(phrases)
				ba.play(ba.CHAN_SPKR_B, phrase, volume = DARK_VOICE_VOLUME, token = DARK_SFX_TOKEN)
				# Calculate delay before next phrase in cluster and wait
				clusterDelay = random.uniform(PHRASE_CLUSTER_DELAY_MIN, PHRASE_CLUSTER_DELAY_MAX)
				time.sleep(clusterDelay)
		elif phoneState == PHONE_STATE_IDLE:
			ba.stop(ba.CHAN_SPKR_A, fade_ms = DARK_STATIC_FADE_MS)

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

	# Set last digit
	lastDigit = n

	# Digit event (for digit wait function)
	digitEvent.set()

	# Off-hook cancel event
	offHookCancelEvent.set()

	# Number dialing
	if phoneState == PHONE_STATE_DIAL or phoneState == PHONE_STATE_DIAL_DELAY:
		dialedNumber = dialedNumber + str(n)
		dialedLength = len(dialedNumber)

def onPulse():
	# Number dialing
	if phoneState == PHONE_STATE_DIAL or phoneState == PHONE_STATE_DIAL_DELAY:
		# Switch to PDD state
		setPhoneState(PHONE_STATE_DIAL_DELAY)
		# PDD event to reset timer if needed
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
	hangupEvent.clear()

	def pickupRespond():
		delay = random.uniform(MIN_PICKUP_PHRASE_DELAY, MAX_PICKUP_PHRASE_DELAY)
		time.sleep(delay)
		if not isPhoneOnHook and not ba.busy(ba.CHAN_VOICE):
			phrase = random.choice(pickupPhrases)
			ba.play(ba.CHAN_VOICE, phrase)

	def offHookMessageDelay():
		if offHookCancelEvent.wait(timeout = OFF_HOOK_MESSAGE_DELAY):
			return
		setPhoneState(PHONE_STATE_OFF_HOOK_MSG)
		for i in range(OFF_HOOK_MESSAGE_LOOPS):
			msg = offHookPhraseA if i == 0 else offHookPhraseB
			ba.say(msg)
			if hangupEvent.wait(timeout = msg.length() + OFF_HOOK_MESSAGE_INTERVAL):
				return
		setPhoneState(PHONE_STATE_OFF_HOOK)

	# Start off-hook delay thread
	offHookCancelEvent.clear()
	offHookThread = threading.Thread(target = offHookMessageDelay)
	offHookThread.daemon = True
	offHookThread.start()

	# Start pickup response on another thread so we don't hold up the GPIO handlers
	if PICKUP_PHRASE_CHANCE_PERCENT > random.randint(0, 100):
		pickupRespondThread = threading.Thread(target = pickupRespond)
		pickupRespondThread.daemon = True
		pickupRespondThread.start()

	pickupEvent.set()

	print "PICKED UP"

def onHangUp():
	global isPhoneOnHook, dialedNumber
	isPhoneOnHook = True
	dialedNumber = ""
	pddEvent.set()
	hangupEvent.set()
	pickupEvent.clear()
	offHookCancelEvent.set()
	setPhoneState(PHONE_STATE_IDLE)

	print "HUNG UP"

def onLoopOpen():
	ba.open_loop()
	if not isPhoneOnHook:
		ba.play(ba.CHAN_PULSE, pulseOpenSound)

def onLoopClose():
	ba.close_loop()
	if not isPhoneOnHook:
		ba.play(ba.CHAN_PULSE, pulseCloseSound)

# Start services
print "Loading directory service..."
phonebook.init(sys.modules[__name__])

print "Loading phone interface..."
dial.on_digit = onDigit
dial.on_touched = onTouched
dial.on_pick_up = onPickUp
dial.on_hang_up = onHangUp
dial.on_pulse = onPulse
dial.on_loop_open = onLoopOpen
dial.on_loop_close = onLoopClose
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
