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
	bwwp.setPhoneState(bwwp.PHONE_STATE_OFF_HOOK)

def endcall(bwwp):
	global connected
	connected = False

phonebook.add("666", call, endcall)
