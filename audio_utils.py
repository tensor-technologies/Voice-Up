import os
import sys
from glob import glob
import soundfile as sf
import numpy as np

SILENCE_THESHOLD = 0.2
CLIPPED_PERCENTAGE_THRESHOLD = 0.15
NORMALIZATION_FACTOR_THRESHOLD = 50

def preprocess_wav(data, rate, th=SILENCE_THESHOLD):
	# Normalize (makes max amplitude scale to 1.0)
	data = data / np.max(np.abs(data))

	start = np.argmax(np.abs(data) > th)
	end = len(data) - np.argmax(data[::-1] > th)

	# Add a little buffer at start & end
	start = max(0, start - int(rate * 0.2))
	end = end + int(rate * 0.2)

	return data[start:end]

def load_recording_if_valid(wav_path, vad_and_normalization):
	try:
		wav, rate = sf.read(wav_path)
	except RuntimeError:
		return np.nan, np.nan
	
	if vad_and_normalization:
		wav = preprocess_wav(wav, rate)

	is_valid, reason = _is_a_valid_recording(wav, rate)
	if is_valid:
		return wav, rate
	return np.nan, np.nan
	


def _is_a_valid_recording(wav, rate):
	if np.count_nonzero(wav) == 0:
		return (False, 'Silence file')
	
	# TODO set threshold
	normalization_factor = 1.0 / np.max(np.abs(wav))
	if normalization_factor > NORMALIZATION_FACTOR_THRESHOLD:
		return (False, 'Volume too low')

	# Cut silence in the start & end.
	wav_normliazed = preprocess_wav(wav, rate)

	if len(wav_normliazed) / rate <= 0.2 * 0.001:
		return (False, 'Too short')

	clipped_samples = np.where(np.abs(wav_normliazed) > 0.98)
	# wav_is_clipped = (np.abs(wav_normliazed) > 0.98)
	# max_consecutive_clipped = _get_max_consecutive_true(wav_is_clipped)
	# clipped_percentage = max_consecutive_clipped / len(wav_normliazed)
	clipped_percentage = len(clipped_samples) / len(wav_normliazed)
	if clipped_percentage > CLIPPED_PERCENTAGE_THRESHOLD :
		return (False, 'Too clipped (%g)' % clipped_percentage)

	return (True, '')