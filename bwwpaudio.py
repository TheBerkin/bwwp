import pygame
import time
import os

NUM_CHANNELS = 12

CHAN_TELEPHONY = 0
CHAN_PULSE = 1
CHAN_VOICE = 2
CHAN_SPKR_A = 3
CHAN_SPKR_B = 4
CHAN_SPKR_C = 5
CHAN_SFX_A = 6
CHAN_SFX_B = 7
CHAN_SFX_C = 8
CHAN_SFX_D = 9
CHAN_SFX_E = 10
CHAN_SFX_F = 11

OPEN_LOOP_CHANNELS = [CHAN_SPKR_A, CHAN_SPKR_B, CHAN_SPKR_C, CHAN_PULSE]

channels = None
master_volume = 1.0

class Sound:
	def __init__(self, path, volume = 1.0):
		snd = pygame.mixer.Sound(path)
		snd.set_volume(volume)
		self.snd = snd

	def length(self):
		return self.snd.get_length()

class Channel:
	def __init__(self, channel):
		self.ch = channel
		self._mute = False
		self.prevVol = 1.0
		self.token = None

	def mute(self):
		if self._mute:
			return
		self._mute = True
		self.prevVol = self.ch.get_volume()
		self.ch.set_volume(0.0)

	def unmute(self):
		if not self._mute:
			return
		self._mute = False
		if self.ch.get_busy():
			self.ch.set_volume(self.prevVol)
			self.prevVol = 1.0

	def is_muted(self):
		return self._mute

	def play(self, snd, **kwargs):
		self.token = kwargs.get('token', None)
		self.ch.play(snd, fade_ms = kwargs.get('fade_ms', 0), loops = kwargs.get('loops', 0))

	def fadeout(self, ms):
		self.ch.fadeout(ms)

	def stop(self):
		self.token = None
		self.ch.stop()

	def set_current_sound_volume(self, vol):
		if self._mute:
			self.prevVol = vol
		elif self.ch.get_busy():
			self.ch.set_volume(vol)

def init():
	global channels
	channels = []
	pygame.mixer.pre_init(8000, -16, 1, 1024)
	pygame.mixer.init()
	print "Using sound parameters: %s" % (str(pygame.mixer.get_init()))
	pygame.mixer.set_num_channels(NUM_CHANNELS)
	pygame.mixer.set_reserved(NUM_CHANNELS)

	# Initialize channels
	for i in range(NUM_CHANNELS):
		channels.append(Channel(pygame.mixer.Channel(i)))


def load_sound_dir(dir, **kwargs):
	(root, _, files) = os.walk(dir).next()
	return [Sound(f, kwargs.get('volume', 1.0)) for f in [root + "/" + f for f in files if f.endswith(".wav")]]

def set_volume(vol):
	global master_volume
	master_volume = vol

	for i in range(NUM_CHANNELS):
		# Even though volume is set when a channel starts playing, this ensures currently playing sounds also change
		channels[i].set_current_sound_volume(vol)

def get_volume():
	return master_volume

def stop(index = -1, **kwargs):
	fadems = kwargs.get('fade_ms', 0)
	if index >= 0 and index < len(channels):
		if fadems > 0:
			channels[index].fadeout(fadems)
		else:
			channels[index].stop()
	else:
		if fadems > 0:
			pygame.mixer.fadeout(fadems)
		else:
			pygame.mixer.stop()

def stopspkr():
	stop(CHAN_SPKR_A)
	stop(CHAN_SPKR_B)
	stop(CHAN_SPKR_C)

def stopsfx():
	stop(CHAN_SFX_A)
	stop(CHAN_SFX_B)
	stop(CHAN_SFX_C)
	stop(CHAN_SFX_D)
	stop(CHAN_SFX_E)

def stop_token(token):
	for ch in channels:
		if ch.token is not None and len(ch.token) > 0 and ch.token == token and ch.ch.get_busy():
			ch.stop()

def open_loop():
	for i in [i for i in range(NUM_CHANNELS) if i not in OPEN_LOOP_CHANNELS]:
		channels[i].mute()

def close_loop():
	for i in [i for i in range(NUM_CHANNELS) if i not in OPEN_LOOP_CHANNELS]:
		channels[i].unmute()

def wait(index):
	if index < 0 or index >= len(channels):
		return
	ch = channels[index]
	while ch.ch.get_busy():
		time.sleep(0.05)

def busy(index):
	if index < 0 or index >= len(channels):
		return False
	return channels[index].ch.get_busy()

def play(index, snd, **kwargs):
	if index < 0 or index >= len(channels) or snd is None:
		return
	ch = channels[index]
	ch.play(snd.snd, **kwargs)
	ch.set_current_sound_volume(kwargs.get('volume', master_volume) * kwargs.get('volume_mul', 1.0))

def say(snd, **kwargs):
	play(CHAN_VOICE, snd, **kwargs)

def say_wait(snd, **kwargs):
	say(snd, **kwargs)
	wait(CHAN_VOICE)

def play_loop(index, snd, **kwargs):
	kwargs['loops'] = -1
	play(index, snd, **kwargs)

def quit():
	pygame.mixer.quit()

