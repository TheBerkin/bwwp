import threading
import time
from gpiozero import DigitalOutputDevice

RING_FREQUENCY = 20.0
RING_ON_DURATION = 2.0
RING_OFF_DURATION = 4.0

driver = None
ringing = False
ringStopEvent = None
ringLock = None

def init():
	global driver, ringStopEvent, ringLock
	driver = DigitalOutputDevice(17)
	ringStopEvent = threading.Event()
	ringLock = threading.RLock()

def on():
	global ringing
	try:
		ringLock.acquire()
		if ringing:
			return
	
		ringing = True
	
		def ringThreadFunc():
			global ringing
			ringStopEvent.clear()
			while True:
				pulseTime = 1.0 / (RING_FREQUENCY * 2.0)
				driver.blink(on_time = pulseTime, off_time = pulseTime, n = None, background = True)
				if ringStopEvent.wait(RING_ON_DURATION):
					break
				driver.off()
				if ringStopEvent.wait(RING_OFF_DURATION):
					break
			driver.off()
			ringStopEvent.clear()
			ringing = False
	
		ringThread = threading.Thread(target = ringThreadFunc)
		ringThread.daemon = True
		ringThread.start()
	finally:
		ringLock.release()

def off():
	ringStopEvent.set()