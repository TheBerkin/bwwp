import phonebook
import time
import random

rickPhrase = None
connected = False

def init(bwwp):
	return

def call(bwwp, num, answer, hangup):
	global connected
	time.sleep(random.uniform(3.0, 8.0))
	if not answer():
		return
	connected = True

	bwwp.chanEffectA.play(random.choice(bwwp.pickupSounds))

	digit = -1
	while digit != 0:
		digit = bwwp.read_digit()
		print "OPERATOR: " + str(digit)
	
	if not connected:
		return

	bwwp.chanEffectA.play(random.choice(bwwp.hangupSounds))
	bwwp.wait_for_channel(bwwp.chanEffectA)

	hangup()

def endcall(bwwp):
	global connected
	connected = False

phonebook.add("0", call, endcall)
