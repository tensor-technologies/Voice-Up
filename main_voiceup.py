import random
import numpy as np
import matplotlib.pyplot as plt
from voiceup import VoiceUp
from person import Person

def main():
	DATASET_ROOT = 'D:\\Programming\\Skynet\\Datasets\\voca-corona-dataset-2020-04-10'
	v = VoiceUp(DATASET_ROOT, limit_rows=100)
	v.load_recordings_data('cough')

	data = list(zip(v.df['cough_data'].dropna().tolist(), v.df['cough_rate'].dropna().tolist(), v.df['recordings_cough'].dropna().tolist()))

	# Wide raw data analysis
	for _ in range(5):
		wav, rate, audiofile = random.choice(data)
		plt.plot(wav)
	plt.title('Random cough samples')
	plt.show()
	
	# Wide functionals analysis
	original_keys = set(v.df.columns)
	v.load_functionals('cough')
	new_keys = set(v.df.columns) - original_keys
	print('Added %d new columns after loading functionals!' % len(new_keys))
	print(new_keys)

	# Targeted analysis
	p = Person(v.dataset_root, id='5e730b5d19fe630007a3e97a')
	p.load_recording('cough')
	# Not we can access the features as normal attributes
	print('p.cough_F0_sma_range:', p.cough_F0_sma_range)
	print('p.cough_F0env_sma_min:', p.cough_F0env_sma_min)
	print('p.cough_F0env_sma_max:', p.cough_F0env_sma_max)


if __name__ == '__main__':
	main()