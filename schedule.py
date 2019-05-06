from datetime import datetime

HOUR_COUNT = 24
YES_CHAR = '1'
NO_CHAR = '0'

class Hours:

	def __init__(self, sched):
		chList = None
		if len(sched) > HOUR_COUNT:
			chList = list(sched)[:HOUR_COUNT]
		elif len(sched) < HOUR_COUNT:
			chList = list(sched) + YES_CHAR * (HOUR_COUNT - len(sched))
		else:
			chList = list(sched)

		self.hours = [(c == YES_CHAR) for c in chList]

	def is_now(self):
		return self.hours[datetime.now().hour]

	def is_then(self, hour):
		return self.hours[hour % HOUR_COUNT]
