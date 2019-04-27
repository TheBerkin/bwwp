import pygame
import time

NUM_CHANNELS = 6

CHAN_TELEPHONY = 0
CHAN_VOICE = 1
CHAN_SFX_A = 2
CHAN_SFX_B = 3
CHAN_SFX_C = 4
CHAN_SFX_D = 5

channels = None
master_volume = 1.0

class Sound:
	def __init__(self, path, volume = 1.0):
		snd = pygame.mixer.Sound(path)
		snd.set_volume(volume)
		self.snd = snd

def init():
	global channels
	channels = []
	pygame.mixer.init(frequency = 8000, size = -16, channels = 1, buffer = 1024)
	pygame.mixer.set_num_channels(10)
	pygame.mixer.set_reserved(6)

	# Initialize channels
	for i in range(NUM_CHANNELS):
		channels.append(pygame.mixer.Channel(i))


def set_volume(vol):
	global master_volume
	master_volume = vol
	
	for i in range(NUM_CHANNELS):
		# Even though volume is set when a channel starts playing, this ensures currently playing sounds also change
		channels[i].set_volume(vol)

def get_volume():
	return master_volume

def stop(index = -1):
	if index >= 0 and index < len(channels):
		channels[index].stop()
	else:
		pygame.mixer.stop()

def wait(index):
	if index < 0 or index >= len(channels):
		return
	ch = channels[index]
	while ch.get_busy():
		time.sleep(0.05)

def busy(index):
	if index < 0 or index >= len(channels):
		return False
	return channels[index].get_busy()

def play(index, snd, **kwargs):
	if index < 0 or index >= len(channels) or snd is None:
		return
	ch = channels[index]
	ch.play(snd.snd, loops = kwargs.get('loops', 0), fade_ms = kwargs.get('fade_ms', 0))
	ch.set_volume(master_volume)

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

