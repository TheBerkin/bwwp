import pyaudio
import time
import math
from array import array
from sys import byteorder

CHUNK_TIME = 1.0
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

THRESHOLD = 0.2
DEBOUNCE_TIME = 10

def listen():
	chunk_size = int(CHUNK_TIME * RATE)
	debounce_frames = 0

	p = pyaudio.PyAudio()

	stream = p.open(
		format = FORMAT,
		channels = CHANNELS,
		rate = RATE,
		input = True,
		frames_per_buffer = chunk_size)

	print "Recording"
	try:
		while True:
			samples = array('h', stream.read(chunk_size, exception_on_overflow = False))
			if (byteorder == 'big'):
				samples.byteswap()
			# Calculate average noise in frame
			soundLevel = math.sqrt(sum([(float(abs(x)) / 32767) ** 2 for x in samples], 0) / len(samples))
			# Calculate time since last event
			time_since_debounce = debounce_frames * CHUNK_TIME
			if soundLevel > THRESHOLD and time_since_debounce >= DEBOUNCE_TIME:
				debounce_frames = 0
				print "TRIGGERED: ", soundLevel
			else:
				debounce_frames += 1
	except KeyboardInterrupt:
		print "Finished recording"
		return
	except:
		raise

	stream.stop_stream()
	stream.close()
	p.terminate()


listen()
