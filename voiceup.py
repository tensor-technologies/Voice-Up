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

import audio_utils
import utils
import opensmile
import swifter

# ----------- Configuration -----------


class VoiceUp:
	def __init__(self, dataset_root_dir, ids=None, limit_rows=None):
		self.dataset_root = dataset_root_dir

		self.files = glob(os.path.join(self.dataset_root, '**', '*.wav'))

		self._load_metadata_from_submissions(ids, limit_rows)
		self._normalize_metadata()
	
	def _load_metadata_from_submissions(self, ids=None, limit_rows=None):
		with open(os.path.join(self.dataset_root, 'submissions.json'), 'r') as fileobj:
			json_data = json.load(fileobj)
		self.df = pd.json_normalize(json_data)
		if ids:
			if type(ids) != list:
				ids = [ ids ]
			self.df = self.df[self.df['_id'].isin(ids)] 
		elif limit_rows:
			self.df = self.df.head(limit_rows)
	
	def _normalize_metadata(self):
		# Normalize recordings columns (Puts the full local path of the recordings or NAN if not exists)
		recordings_cols = [ c for c in self.df.columns if c.startswith('recordings.') ]
		for col in recordings_cols:
			recording_name = '%s.wav' % col.partition('.')[-1]
			self.df[col] = self.df.apply(lambda row: self._get_recording_of_person(row['_id'], recording_name), axis=1)
	
	def _get_recording_of_person(self, id, recording_name):
		recording_path = os.path.join(self.dataset_root, id, recording_name)
		if recording_path in self.files:
			return recording_path
		return np.nan

	def load_recordings_data(self, recording_name):
		col_name = 'recordings.%s' % recording_name
		assert col_name in self.df.columns, "Column %s not in df" % col_name

		counter = utils.Counter(len(self.df))
		def do_apply(row):
			counter.increment()
			return audio_utils.load_recording_if_valid(os.path.join(self.dataset_root, row['_id'], '%s.wav' % recording_name))
		
		# Create 2 new columns for recording type (e.g 'recordings.cough.data', 'recordings.cough.rate')
		self.df[col_name + '.data'], self.df[col_name + '.rate'] = zip(*self.df.apply(do_apply, axis=1))
	
	def load_functionals(self, recording_name):
		col_name = 'recordings.%s' % recording_name
		assert col_name in self.df.columns, "Column %s not in df" % col_name

		# counter = utils.Counter(len(self.df[col_name].dropna()))
		def do_apply(wavfile):
			# counter.increment()
			return opensmile.opensmile.get_functionals(wavfile)

		functionals_df = self.df[col_name].dropna().swifter.apply(do_apply)

		# A trick to add functionals_df to main df (or update the values)
		self.df[functionals_df.columns] = functionals_df


		