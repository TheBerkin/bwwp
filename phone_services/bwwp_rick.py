import phonebook
import time
import random
import bwwpaudio as ba

rickPhrase = None
connected = False

def init(bwwp):
	global rickPhrase
	rickPhrase = ba.Sound("./sound/special/rick.wav")

def call(bwwp, num, answer, hangup):
	global connected
	time.sleep(random.uniform(3.0, 8.0))
	if not answer():
		return
	connected = True

	ba.play(ba.CHAN_SFX_A, random.choice(bwwp.pickupSounds))

	time.sleep(random.uniform(1.7, 3.0))

	if not connected:
		return

	ba.play(ba.CHAN_VOICE, rickPhrase)
	ba.wait(ba.CHAN_VOICE)

	if not connected:
		return

	time.sleep(random.uniform(1.2, 3.0))

	if not connected:
		return

	ba.play(ba.CHAN_SFX_A, random.choice(bwwp.hangupSounds))
	ba.wait(ba.CHAN_SFX_A)

	hangup()

def endcall(bwwp):
	global connected
	connected = False

phonebook.add("4548326", call, endcall)
