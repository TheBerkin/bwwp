from gpiozero import Button
import time
import threading

SH_MANUAL_PULSE_INTERVAL = 0.3
SH_HANGUP_DELAY = 0.4

on_digit = None

on_bad_digit = None

on_touched = None

on_pick_up = None

on_hang_up = None

on_pulse = None

on_loop_close = None

on_loop_open = None

digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'A', 'B', 'C', 'D', 'E', 'F']
dial = None
dialSwitch = None
hook = None
dialPulses = 0
isDialSwitchOn = False
isLoaded = False
hungUp = False
hookSwitchDownEvent = threading.Event()
hookSwitchUpEvent = threading.Event()
digitLock = threading.RLock()
hangupLock = threading.RLock()

def init():
	global isLoaded, digits, dial, dialSwitch, dialPulses, isDialSwitchOn, hook, hungUp

	if isLoaded:
		return

	dial = Button(2, bounce_time = 0.025)
	dialSwitch = Button(4, bounce_time = 0.1)
	hook = Button(5, bounce_time = 0.025)

	def onDialPress():
		if on_loop_close is not None and hook.is_active:
			on_loop_close()
		if on_pulse is not None:
			on_pulse()

	def onDialRelease():
		global dialPulses
		if on_loop_open is not None and hook.is_active:
			on_loop_open()
		if isDialSwitchOn:
			dialPulses += 1

	def onDialSwitchOn():
		global isDialSwitchOn
		isDialSwitchOn = True
		if on_touched is not None:
			on_touched()

	def handleDigit():
		global dialPulses
		try:
			digitLock.acquire()
			digitIndex = dialPulses - 1
			if digitIndex >= 0 and digitIndex < len(digits):
				digit = digits[digitIndex]
				if on_digit is not None:
					on_digit(digit)
			else:
				if on_bad_digit is not None:
					on_bad_digit(dialPulses)
		finally:
			dialPulses = 0
			digitLock.release()

	def onDialSwitchOff():
		global isDialSwitchOn, dialPulses, digits, on_digit, on_bad_digit
		isDialSwitchOn = False
		handleDigit()

	def onHookUp():
		global hungUp
		hangupLock.acquire()
		try:
			hookSwitchUpEvent.set()
			if on_loop_close is not None:
				on_loop_close()
			if hungUp:
				hungUp = False
				if on_pick_up is not None:
					on_pick_up()
		finally:
			hangupLock.release()

	def onHookDown():
		if on_loop_open is not None:
			on_loop_open()
		hookSwitchDownEvent.set()

	def hookSwitchFunc():
		global dialPulses, hungUp
		while True:
			# If hung up, wait indefinitely for hook to be released
			if hungUp:
				hookSwitchUpEvent.wait()
				hookSwitchUpEvent.clear()

			# Wait for hook to be pressed
			if dialPulses > 0 and not hookSwitchDownEvent.wait(timeout = SH_MANUAL_PULSE_INTERVAL):
				handleDigit()
				continue
			else:
				hookSwitchDownEvent.wait()

			if on_pulse is not None:
				on_pulse()

			hookSwitchDownEvent.clear()

			# Wait for hook to be released
			if hookSwitchUpEvent.wait(timeout = SH_HANGUP_DELAY):
				dialPulses += 1
			else:
				# If timed out, hang up
				try:
					dialPulses = 0 # Reset digit state

					hangupLock.acquire()
					hungUp = True
					if on_hang_up is not None:
						on_hang_up()
				finally:
					hangupLock.release()
			hookSwitchUpEvent.clear()


	dial.when_pressed = onDialPress
	dial.when_released = onDialRelease
	dialSwitch.when_pressed = onDialSwitchOn
	dialSwitch.when_released = onDialSwitchOff
	hook.when_pressed = onHookUp
	hook.when_released = onHookDown
	hookSwitchThread = threading.Thread(target = hookSwitchFunc)
	hookSwitchThread.daemon = True
	hookSwitchThread.start()

	hungUp = not hook.is_active

	if hook.is_active:
		if on_pick_up is not None:
			on_pick_up()
	else:
		if on_hang_up is not None:
			on_hang_up()

	isLoaded = True
