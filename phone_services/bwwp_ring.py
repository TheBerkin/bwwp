import phonebook
import time
import random

connected = False

def init(bwwp):
	return

def call(bwwp, num, answer, hangup):
	global connected

	if not answer():
		return

	connected = True

	bwwp.set_ring_state(True)

def endcall(bwwp):
	global connected
	connected = False
	bwwp.set_ring_state(False)

phonebook.add("1111", call, endcall)
