import phonebook
import time
from datetime import datetime
import random
import subprocess
import threading
import bwwpaudio as ba
import schedule

connected = False

DARK_SCHEDULE = schedule.Hours('111111000000000000000000')

OPERATOR_VOLUME = 0.5

MENU_STATUS_NONE = 0
MENU_STATUS_HANGUP = 1
MENU_STATUS_BYE = 2

DARK_SFX_INTERVAL = (10.0, 60.0)
LIGHT_SFX_INTERVAL = (2.0, 35.0)

DARK_SOUND_LAYERS = 1
LIGHT_SOUND_LAYERS = 2

LIGHT_PICKUP_DELAY = (0.9, 1.5)
DARK_PICKUP_DELAY = (2.0, 5.5)

phrasesA = {}
phrasesB = {}
breathSound = None
amb = {}
darkMiscSounds = None
lightMiscSounds = None

endCallEvent = threading.Event()

def init(bwwp):
	global breathSound, bgSoundA, bgSoundB, darkMiscSounds, lightMiscSounds
	breathSound = ba.Sound("./sound/etc/vocal/breathing.wav", 0.5)
	amb['drip'] = ba.Sound("./sound/ambient/amb_drip.wav", 0.6)
	amb['flies'] = ba.Sound("./sound/ambient/amb_flies.wav", 0.05)
	amb['office'] = ba.Sound("./sound/ambient/amb_office.wav", 0.7)
	darkMiscSounds = ba.load_sound_dir("./sound/sewer", volume = 0.15)
	lightMiscSounds = ba.load_sound_dir("./sound/office", volume = 0.1)
	phrasesA['volume'] = ba.Sound("./sound/operator/a/op_volume.wav", OPERATOR_VOLUME)
	phrasesB['volume'] = ba.Sound("./sound/operator/b/op_volume.wav", OPERATOR_VOLUME)
	phrasesA['operator'] = ba.Sound("./sound/operator/a/op_operator.wav", OPERATOR_VOLUME)
	phrasesB['operator'] = ba.Sound("./sound/operator/b/op_operator.wav", OPERATOR_VOLUME)
	phrasesA['bye'] = ba.Sound("./sound/operator/a/op_haveniceday.wav", OPERATOR_VOLUME)
	phrasesB['bye'] = ba.Sound("./sound/operator/b/op_haveniceday.wav", OPERATOR_VOLUME)
	phrasesA['back'] = ba.Sound("./sound/operator/a/op_back.wav", OPERATOR_VOLUME)
	phrasesB['back'] = ba.Sound("./sound/operator/b/op_back.wav", OPERATOR_VOLUME)
	phrasesA['power_options'] = ba.Sound("./sound/operator/a/op_power_options.wav", OPERATOR_VOLUME)
	phrasesB['power_options'] = ba.Sound("./sound/operator/b/op_power_options.wav", OPERATOR_VOLUME)
	phrasesA['ring_test'] = ba.Sound("./sound/operator/a/op_ring_test.wav", OPERATOR_VOLUME)
	phrasesB['ring_test'] = ba.Sound("./sound/operator/b/op_ring_test.wav", OPERATOR_VOLUME)
	phrasesA['ok'] = ba.Sound("./sound/operator/a/op_okay.wav", OPERATOR_VOLUME)
	phrasesB['ok'] = ba.Sound("./sound/operator/b/op_okay.wav", OPERATOR_VOLUME)

# OPERATOR
# 1: Volume
#	1-9: Volume values
#	0: Back
# 2: Power Options
#	1: Reboot
#	2: Shutdown
#	0: Back
# 3: Ring Test
#	0: Back


def call(bwwp, num, answer, hangup):
	global connected

	endCallEvent.clear()
	menuStatus = MENU_STATUS_NONE
	dt = datetime.now()
	dark = DARK_SCHEDULE.is_now()
	phrases = phrasesB if dark else phrasesA

	def menu_volume():
		print "OPERATOR: Volume menu"
		ba.say(phrases['volume'])
		digit = -1
		while True:
			digit = bwwp.read_digit()
			if not connected:
				return MENU_STATUS_NONE
			if digit == '0':
				ba.say(phrases['back'])
				print "OPERATOR: Back"
				break
			vol = float(digit) / 9.0 if digit in '1234567890' else 1.0
			print "OPERATOR: Volume set to %.2f" % (vol)
			ba.set_volume(vol)
			ba.say(phrases['ok'])
		return MENU_STATUS_NONE

	def menu_power_options():
		print "OPERATOR: Power Options menu"
		ba.say(phrases['power_options'])
		digit = -1
		while True:
			digit = bwwp.read_digit()
			if not connected:
				return MENU_STATUS_NONE
			if digit == '1':
				ba.say_wait(phrases['ok'])
				def do_reboot():
					time.sleep(3)
					subprocess.Popen(['sudo', 'reboot'])
				threading.Thread(target = do_reboot).start()
				endFlag = True
				return MENU_STATUS_HANGUP
			elif digit == '2':
				ba.say_wait(phrases['ok'])
				def do_halt():
					time.sleep(3)
					subprocess.Popen(['sudo', 'halt'])
				threading.Thread(target = do_halt).start()
				endFlag = True
				return MENU_STATUS_HANGUP
			elif digit == '0':
				ba.say(phrases['back'])
				print "OPERATOR: Back"
				break
		return MENU_STATUS_NONE

	def menu_ring_test():
		print "OPERATOR: Ring Test"
		ba.say_wait(phrases['ring_test'])
		bwwp.set_ring_state(True)
		digit = -1
		while True:
			digit = bwwp.read_digit()
			if not connected:
				break
			if digit == '0':
				ba.say(phrases['back'])
				print "OPERATOR: Back"
				break

		bwwp.set_ring_state(False)
		return MENU_STATUS_NONE

	def sfx_func(ch):
		miscSounds = darkMiscSounds if dark else lightMiscSounds
		while connected:
			interval = random.uniform(*(DARK_SFX_INTERVAL if dark else LIGHT_SFX_INTERVAL))
			if endCallEvent.wait(timeout = interval):
				return
			ba.wait(ch)
			ba.play(ch, random.choice(miscSounds), volume_mul = random.uniform(0.5, 1.0))

	sfxThreads = []
	sfxLayerCount = DARK_SOUND_LAYERS if dark else LIGHT_SOUND_LAYERS
	for i in range(sfxLayerCount):
		sfxThread = threading.Thread(target = sfx_func, args = (i + ba.CHAN_SFX_E,))
		sfxThread.daemon = True
		sfxThreads.append(sfxThread)

	try:
		time.sleep(random.uniform(*(DARK_PICKUP_DELAY if dark else LIGHT_PICKUP_DELAY)))
	
		if not answer():
			return
	
		connected = True

		# Play pickup sound
		ba.play(ba.CHAN_SFX_A, random.choice(bwwp.pickupSounds))

		# Start background ambience
		if dark:
			ba.play_loop(ba.CHAN_SFX_B, breathSound, fade_ms = 10000)
			ba.play_loop(ba.CHAN_SFX_C, amb['drip'])
			ba.play_loop(ba.CHAN_SFX_D, amb['flies'])
		else:
			ba.play_loop(ba.CHAN_SFX_B, amb['office'])

		# Start background SFX threads
		for sfxThread in sfxThreads:
			sfxThread.start()
	
		# Say "Operator."
		time.sleep(random.uniform(0.3, 1.5))
		ba.say(phrases['operator'])
	
		digit = -1
		while connected and menuStatus == MENU_STATUS_NONE:
			digit = bwwp.read_digit()
			if digit == '1':
				menuStatus = menu_volume()
			elif digit == '2':
				menuStatus = menu_power_options()
			elif digit == '3':
				menuStatus = menu_ring_test()
			elif digit == '0':
				break
	
		print "OPERATOR: Exiting"
	
		if not connected:
			return
	
		if menuStatus == MENU_STATUS_BYE:
			ba.say_wait(phrases['bye'])
			time.sleep(0.25)
	
		ba.play(ba.CHAN_SFX_A, random.choice(bwwp.hangupSounds))
		ba.wait(ba.CHAN_SFX_A)
	
		hangup()
	finally:
		endCallEvent.set()

def endcall(bwwp):
	global connected
	connected = False
	endCallEvent.set()

phonebook.add("0", call, endcall)
