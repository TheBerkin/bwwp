from gpiozero import Button
import time

on_digit = None

on_bad_digit = None

on_touched = None

on_pick_up = None

on_hang_up = None

digits = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
dial = None
dialSwitch = None
hook = None
dialPulses = 0
isDialSwitchOn = False

def init():
	global digits, dial, dialSwitch, dialPulses, isDialSwitchOn, hook
	dial = Button(2, bounce_time = 0.025)
	dialSwitch = Button(4, bounce_time = 0.1)
	hook = Button(5, bounce_time = 0.025)

	def onDialPulse():
		global isDialSwitchOn, dialPulses
		if isDialSwitchOn:
			dialPulses += 1

	def onDialSwitchOn():
		global isDialSwitchOn
		isDialSwitchOn = True
		if on_touched is not None:
			on_touched()

	def onDialSwitchOff():
		global isDialSwitchOn, dialPulses, digits, on_digit, on_bad_digit
		isDialSwitchOn = False
		digitIndex = dialPulses - 1
		if digitIndex >= 0 and digitIndex < len(digits):
			digit = digits[digitIndex]
			if on_digit is not None:
				on_digit(digit)
		else:
			if on_bad_digit is not None:
				on_bad_digit(dialPulses)

		dialPulses = 0

	def onHookUp():
		global on_pick_up
		if on_pick_up is not None:
			on_pick_up()

	def onHookDown():
		global on_hang_up
		if on_hang_up is not None:
			on_hang_up()

	dial.when_released = onDialPulse
	dialSwitch.when_pressed = onDialSwitchOn
	dialSwitch.when_released = onDialSwitchOff
	hook.when_pressed = onHookUp
	hook.when_released = onHookDown

	if hook.is_active:
		onHookUp()
	else:
		onHookDown()
