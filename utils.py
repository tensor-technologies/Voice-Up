class Counter:
	def __init__(self, total):
		self.total = total
		self.counter = 0
	
	def increment(self):
		self.counter += 1
		print('\r%d / %d' % (self.counter, self.total), end='')
		if self.counter == self.total:
			print('')
