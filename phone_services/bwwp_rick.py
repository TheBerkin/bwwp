import phonebook
import time
import random

rickPhrase = None
connected = False

def init(bwwp):
	global rickPhrase
	rickPhrase = bwwp.load_sound("./sound/special/rick.wav")

def call(bwwp, num, answer, hangup):
	global connected
	time.sleep(random.uniform(3.0, 8.0))
	if not answer():
		return
	connected = True

	bwwp.chanEffectA.play(random.choice(bwwp.pickupSounds))

	time.sleep(random.uniform(1.7, 3.0))

	if not connected:
		return

	bwwp.say(rickPhrase)

	if not connected:
		return

	time.sleep(random.uniform(1.2, 3.0))

	if not connected:
		return

	bwwp.chanEffectA.play(random.choice(bwwp.hangupSounds))
	bwwp.wait_for_channel(bwwp.chanEffectA)

	hangup()

def endcall(bwwp):
	global connected
	connected = False

phonebook.add("4548326", call, endcall)
