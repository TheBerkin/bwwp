import phonebook
import time
import random
import subprocess
import threading
import bwwpaudio as ba

connected = False

OPERATOR_VOLUME = 0.75

MENU_STATUS_NONE = 0
MENU_STATUS_HANGUP = 1
MENU_STATUS_BYE = 2

phrases = {}
breathSound = None
bgSoundA = None
bgSoundB = None

def init(bwwp):
	global breathSound, bgSoundA, bgSoundB
	breathSound = ba.Sound("./sound/etc/vocal/breathing.wav", 0.8)
	bgSoundA = ba.Sound("./sound/ambient/amb_drip.wav", 0.6)
	bgSoundB = ba.Sound("./sound/ambient/amb_flies.wav", 0.05)
	phrases['volume'] = ba.Sound("./sound/operator/op_volume.wav", OPERATOR_VOLUME)
	phrases['operator'] = ba.Sound("./sound/operator/op_operator.wav", OPERATOR_VOLUME)
	phrases['bye'] = ba.Sound("./sound/operator/op_haveniceday.wav", OPERATOR_VOLUME)
	phrases['back'] = ba.Sound("./sound/operator/op_back.wav", OPERATOR_VOLUME)
	phrases['power_options'] = ba.Sound("./sound/operator/op_power_options.wav", OPERATOR_VOLUME)
	phrases['ok'] = ba.Sound("./sound/operator/op_okay.wav", OPERATOR_VOLUME)

# OPERATOR
# 1: Volume
#	1-9: Volume values
#	0: Back
# 2: Power Options
#	1: Reboot
#	2: Shutdown
#	0: Back

def call(bwwp, num, answer, hangup):
	global connected

	menuStatus = MENU_STATUS_NONE

	def menu_volume():
		print "OPERATOR: Volume menu"
		ba.say(phrases['volume'])
		digit = -1
		while True:
			digit = bwwp.read_digit()
			if not connected:
				return MENU_STATUS_NONE
			if digit == 0:
				ba.say(phrases['back'])
				print "OPERATOR: Back"
				break
			vol = float(digit) / 9.0
			print "OPERATOR: Volume set to %.2f" % (vol)
			ba.set_volume(vol)
		return MENU_STATUS_NONE

	def menu_power_options():
		print "OPERATOR: Power Options menu"
		ba.say(phrases['power_options'])
		digit = -1
		while True:
			digit = bwwp.read_digit()
			if not connected:
				return MENU_STATUS_NONE
			if digit == 1:
				ba.say_wait(phrases['ok'])
				def do_reboot():
					time.sleep(3)
					subprocess.Popen(['sudo', 'reboot'])
				threading.Thread(target = do_reboot).start()
				endFlag = True
				return MENU_STATUS_HANGUP
			elif digit == 2:
				ba.say_wait(phrases['ok'])
				def do_halt():
					time.sleep(3)
					subprocess.Popen(['sudo', 'halt'])
				threading.Thread(target = do_halt).start()
				endFlag = True
				return MENU_STATUS_HANGUP
			elif digit == 0:
				ba.say(phrases['back'])
				print "OPERATOR: Back"
				break
		return MENU_STATUS_NONE

	time.sleep(random.uniform(3.0, 8.0))

	if not answer():
		return

	connected = True

	# Start the gross sounds
	ba.play_loop(ba.CHAN_SFX_A, breathSound, fade_ms = 10000)
	ba.play(ba.CHAN_SFX_B, random.choice(bwwp.pickupSounds))
	ba.play_loop(ba.CHAN_SFX_C, bgSoundA)
	ba.play_loop(ba.CHAN_SFX_D, bgSoundB)

	# Say "Operator."
	time.sleep(random.uniform(0.3, 1.5))
	ba.say(phrases['operator'])

	digit = -1
	while connected and menuStatus == MENU_STATUS_NONE:
		digit = bwwp.read_digit()
		if digit == 1:
			menuStatus = menu_volume()
		elif digit == 2:
			menuStatus = menu_power_options()
		elif digit == 0:
			break

	print "OPERATOR: Exiting"

	if not connected:
		return

	if menuStatus != MENU_STATUS_HANGUP:
		ba.say_wait(phrases['bye'])
		time.sleep(0.25)

	ba.play(ba.CHAN_SFX_A, random.choice(bwwp.hangupSounds))
	ba.wait(ba.CHAN_SFX_A)

	hangup()

def endcall(bwwp):
	global connected
	connected = False

phonebook.add("0", call, endcall)
