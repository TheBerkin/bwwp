import os
import sys
import importlib
import threading

def get_services_path():
	return "phone_services"

__bwwp = None
__directory = {}

def init(bwwp):
	global __bwwp
	__bwwp = bwwp
	phoneModulePath = os.getcwd() + "/" + get_services_path()
	sys.path.append(phoneModulePath)
	(root, _, files) = os.walk(get_services_path()).next()
	for file in [file for file in files if file.endswith(".py")]:
		serviceName = os.path.splitext(file)[0]
		serviceModule = importlib.import_module(serviceName)
		serviceModuleInit = getattr(serviceModule, 'init')
		serviceModuleInit(bwwp)
		print "Imported phone service \"" + serviceName + "\""
	sys.path.remove(phoneModulePath)

# callFunc(bwwp, num, answer, hangup)
def add(number, callFunc, endCallFunc):
	if number is None:
		return False
	entry = {'number': number, 'call_func': callFunc, 'end_call_func': endCallFunc}
	__directory[number] = entry
	return True

def exists(number):
	return number is not None and __directory.has_key(number)

def call(number):
	if not __directory.has_key(number):
		return False
	
	service = __directory[number]
	
	def answerFunc():
		if __bwwp.phoneState == __bwwp.PHONE_STATE_RING:
			__bwwp.setPhoneState(__bwwp.PHONE_STATE_CALL)
			return True
		return False

	def hangupFunc():
		if __bwwp.phoneState == __bwwp.PHONE_STATE_CALL:
			__bwwp.setPhoneState(__bwwp.PHONE_STATE_BUSY)
			return True
		return False

	def phoneHangupWaitFunc():
		__bwwp.hangupEvent.wait()
		service['end_call_func'](__bwwp)

	callThread = threading.Thread(target = service['call_func'], args = [__bwwp, number, answerFunc, hangupFunc])
	callThread.daemon = True
	callThread.start()

	endcallThread = threading.Thread(target = phoneHangupWaitFunc)
	endcallThread.daemon = True
	endcallThread.start()
	
	return True
