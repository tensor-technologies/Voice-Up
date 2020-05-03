import os
import sys
import argparse
import json
import wave
import audioop
import zipfile
import shutil
from glob import glob
from io import BytesIO
from functools import partial
import soundfile as sf
import numpy as np
import pandas as pd

# ----------- Configuration -----------
# The maximum multiplier allowed for the volumed to be normalized to 1.0
NORMALIZATION_FACTOR_THRESHOLD = 50
APPLY_VAD_AND_RESAMPLING_TO_OUTPUT = False
#  The sample rate which the model needs to work properly
# *relevant only with APPLY_VAD_AND_RESAMPLING_TO_OUTPUT=true*
TARGET_SAMPLE_RATE = 16000
# The max "energy" of an audio to be considered silence
SILENCE_THESHOLD = 0.2
OUTPUT_FOLDER = '.\\generated_data'
# The max allowed fraction of an audio file clipped samples (e.g 0.15/1 of the audio is at maximum/minimun energy)
CLIPPED_PERCENTAGE_THRESHOLD = 0.15
# The fields by which the dataset will be ordered and selected.
# Age should be last (as it's a numeric field, see implementation of _find_similar_people_to_person)
KEY_FIELDS = ['formData.gender', 'formData.smokingHabits', 'formData.country', 'formData.age']
# Create a summary Excel file
CREATE_XLS_FILE = True
# Copy the files to the output folder
COPY_FILES_TO_DEDICATED_FOLDER = True
# Output json (submissions like) files of the 2 groups (positives & control group)
CREATE_GROUP_JSONS = True

def preprocess_wav(data, rate, th=SILENCE_THESHOLD):
	data = data / np.max(np.abs(data))
	start = np.argmax(np.abs(data) > th)
	end = len(data) - np.argmax(data[::-1] > th)
	# Add a little buffer at start & end
	start = max(0, start - int(rate * 0.2))
	end = end + int(rate * 0.2)

	return data[start:end]

def copy_wav_and_change_rate(input_filepath, output_filepath, target_sample_rate):
	with wave.open(input_filepath, 'r') as input_wav:
		n_frames = input_wav.getnframes()
		audioData = input_wav.readframes(n_frames)
		originalRate = input_wav.getframerate()
		with wave.open(output_filepath, 'w') as output_wav:
			final_sr = originalRate if target_sample_rate == None else target_sample_rate
			output_wav.setnchannels(1)
			output_wav.setparams((1, 2, final_sr, 0, 'NONE', 'Uncompressed'))
			converted = audioop.ratecv(audioData, 2, 1, originalRate, final_sr, None)
			output_wav.writeframes(converted[0])
	
	if APPLY_VAD_AND_RESAMPLING_TO_OUTPUT:
		wav, rate = sf.read(output_filepath)
		wav = preprocess_wav(wav, rate)
		sf.write(output_filepath, wav, rate)

# def _get_max_consecutive_true(arr):
# 	max_seq = 0
# 	current_seq = 0
# 	for v in arr:
# 		if v == True:
# 			current_seq += 1
# 		else:
# 			max_seq = max(current_seq, max_seq)
# 			current_seq = 0
# 	max_seq = max(current_seq, max_seq)
# 	return max_seq

def copydir(src, dst, copy_function=shutil.copy2):
	"""
	Custom implementaion of shutil.copytree
	can handle both directories and zipfiles
	hacky implementaion, needs refining before production
	"""
	if '.zip\\' in src:
		zip_path, dirname = src.split('.zip\\')
		zip_path += '.zip'
		dirname = dirname.replace('\\', '/')
		if not dirname.endswith('/'):
			dirname += '/'
		
		os.makedirs(dst)
		archive = zipfile.ZipFile(zip_path, 'r')
		
		listdir = [ (info.filename, info.is_dir()) for info in archive.infolist() if info.filename.startswith(dirname) and info.filename != dirname ]
		for filepath, is_dir in listdir:
			if is_dir:
				copydir(os.path.join(zip_path, filepath), os.path.join(dst, filepath), copy_function=copy_function)
			else:
				fileobj = BytesIO(archive.read(filepath))
				copy_function(fileobj, os.path.join(dst, os.path.basename(filepath)))
	else:
		names = os.listdir(src)
		os.makedirs(dst)
		for name in names:
			s = os.path.join(src, name)
			d = os.path.join(dst, name)
			if os.path.isdir(s):
				copydir(s, d)
			else:
				copy_function(s, d)

def _is_a_valid_recording(wav_path_or_filelike):
	try:
		wav, rate = sf.read(wav_path_or_filelike)
	except RuntimeError:
		return (False, 'Corruped file')

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

def _check_if_has_valid_recordings(dataset_root, person):
	id = person._id

	# Read the recordings of the person with the proper method
	if dataset_root.endswith('.zip'):
		archive = zipfile.ZipFile(dataset_root, 'r')
		recording_files = [ BytesIO(archive.read(name)) for name in archive.namelist() if name.startswith('data/%s' % id) and name.endswith('.wav') ]
	else:
		recording_files = glob(os.path.join(dataset_root, id, '*.wav'))
	
	if len(recording_files) == 0:
		return (False, 'Has no recordings')

	for wav_path_or_filelike in recording_files:
		is_valid, reason = _is_a_valid_recording(wav_path_or_filelike)
		if not is_valid:
			return (False, reason)
	return (True, '')

def _filter_nan_people_and_normalize(df, match_fields):
	# drop data with no recording
	no_recordings_inds = df.loc[:, 'recordings.cough': 'recordings.story'].isna().all(axis=1)
	print('Dropped %d people with no recordings' % len(df[no_recordings_inds]))
	df = df[~no_recordings_inds]

	df['formData.age'] = pd.to_numeric(df['formData.age'], errors='coerce')

	# drop rows with missing match fields and address specific fields issues
	for mf in match_fields:
		df = df[df[mf].notna()]

		try:
			if mf == 'formData.gender':
				df = df[df[mf] != 'Other']
			elif mf == 'formData.smokingHabits':
				df[mf].replace("I've used to smoke", 'I used to smoke', inplace=True)
			elif mf == 'formData.age':
				df = df[(df[mf] > 0) & (df[mf] < 120)]
		except Exception as e:
			print('Error processing field', mf, 'on values', df[mf])
			raise e
	return df

def _find_similar_people_to_person(person_row, df, key_fields):
	# Setup a df to hold the differences between every person to THE person, and add an id.
	distances = df[['_id'] + key_fields].copy()

	# For every column we need to compare, if its numeric put the substraction, if not put 0 IF ITS THE SAME
	for f in key_fields:
		if type(person_row[f]) is int:
			distances[f] = abs(distances[f] - person_row[f])
		else:
			distances[f] = (distances[f] != person_row[f]).astype(int)
	
	# Sort by the fields important to as
	distances = distances.sort_values(by=key_fields)
	return list(distances['_id'])

def create_control_group(dataset_root, df_pos, df_neg, key_fields):
	control_group = pd.DataFrame(columns=df_pos.columns)

	# For every patient in the positive group, we need to find 
	for _, patient_data in df_pos.iterrows():
		# Ranks the ids of ALL the df by how much they are similar to the person
		most_similar_ids = _find_similar_people_to_person(patient_data, df_neg, key_fields)
		
		most_similar_person = None
		for id in most_similar_ids:
			# If the id we found is already in the control group, don't use it.
			if control_group['_id'].isin([id]).any():
				continue
			# Search for a series with the id and pick the first one
			most_similar_person = df_neg[df_neg['_id'] == id].iloc[0]
			# If we found a valid similar person, stop searching.
			is_valid, reason = _check_if_has_valid_recordings(dataset_root, most_similar_person)
			if is_valid:
				break
			else:
				print('[WARN] Person %s was rejected from control group because his recordings is not valid. (Reason: %s)' % (id, reason))
		
		control_group = control_group.append(most_similar_person)
	return control_group

def generate_dataset_for_model(args):
	
	# Reads the submissions.json file
	# 2 options: a path to the root of an extracted dataset-zip, or a path to dataset-zip
	dataset_root = args.dataset_root_path
	if dataset_root.endswith('.zip'):
		archive = zipfile.ZipFile(dataset_root, 'r')
		json_data = json.loads(archive.read('data/submissions.json'))
	else:
		with open(os.path.join(dataset_root, 'submissions.json'), 'r') as fileobj:
			json_data = json.load(fileobj)

	# 
	df = pd.json_normalize(json_data)

	print('Loaded submissions file, found %d records.' % len(df))
	print('Generating dataset for model by fields:', KEY_FIELDS)

	df_normalized = _filter_nan_people_and_normalize(df, KEY_FIELDS)

	covid19_pos_inds = df_normalized['formData.covid19.diagnosedCovid19'] == 'Yes'
	
	# Seperate dataset to positives and negatives
	df_pos = df_normalized[covid19_pos_inds]
	df_neg = df_normalized[~covid19_pos_inds]

	print('Generating positive people group (found %d)' % len(df_pos))
	for _, person in df_pos.iterrows():
		is_valid, reason = _check_if_has_valid_recordings(dataset_root, person)
		if not is_valid:
			print('[WARN] Person %s was rejected from positives because his recordings is not valid. (Reason: %s)' % (person._id, reason))
			df_pos = df_pos.drop(person.name)
	print('Found %d valid positive people.' % len(df_pos))

	# Creates a dataframe composed of chosen negatives, who are most similar to the positives.
	# (e.g. Say we have X positives, chooses X negatives who are the most similar to the corrosponding positives)
	print('Generating control group:')
	control_group = create_control_group(dataset_root, df_pos, df_neg, KEY_FIELDS)
	print('Done')

	print ('Positives:')
	for id in df_pos['_id']:
		print("\t%s" % id)

	print('Negatives:')
	for id in control_group['_id']:
		print("\t%s" % id)

	os.makedirs(OUTPUT_FOLDER, exist_ok=True)
	if CREATE_XLS_FILE:
		name = os.path.join(OUTPUT_FOLDER, 'submissions_output.xlsx')
		print ('Outputing summary to', name)
		with pd.ExcelWriter(name) as writer:
			df_pos.to_excel(writer, sheet_name='Positive')
			control_group.to_excel(writer, sheet_name='Control group')
	
	if CREATE_GROUP_JSONS:
		df_pos.to_json(os.path.join(OUTPUT_FOLDER, 'positives.json'), orient='records')
		control_group.to_json(os.path.join(OUTPUT_FOLDER, 'controlgroup.json'), orient='records')

	# Copy files to seperate dataset
	if COPY_FILES_TO_DEDICATED_FOLDER:
		src_root = os.path.join(dataset_root, 'data') if dataset_root.endswith('.zip') else dataset_root
		dst_root = OUTPUT_FOLDER
		# call copy_wav_and_change_rate with the sample-rate parameter set
		copy_function = partial(copy_wav_and_change_rate, target_sample_rate=(TARGET_SAMPLE_RATE if APPLY_VAD_AND_RESAMPLING_TO_OUTPUT else None))

		print('Copying files to %s' % dst_root)

		for session_id in df_pos['_id']:
			src = os.path.join(src_root, session_id)
			dst = os.path.join(dst_root, 'cov19_positive', session_id)
			os.makedirs(os.path.dirname(dst), exist_ok=True)
			copydir(src, dst, copy_function=copy_function)

		for session_id in control_group['_id']:
			src = os.path.join(src_root, session_id)
			dst = os.path.join(dst_root, 'control_group', session_id)
			os.makedirs(os.path.dirname(dst), exist_ok=True)
			copydir(src, dst, copy_function=copy_function)
		print('Done')

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('dataset_root_path', type=str.lower, help='Path to the main directory of the dataset OR path to the zip file')

	# If user didn't choose a command, print help
	if len(sys.argv) <= 1:
		sys.argv.append('--help')

	args = parser.parse_args()
	generate_dataset_for_model(args)

if __name__ == "__main__":
	main()