import os
import numpy as np
import pandas as pd

import audio_utils
import utils
import opensmile

from voiceup import VoiceUp

# ----------- Configuration -----------


class Person:
	@property
	def _raw(self):
		return self._voiceup.df.iloc[0]

	def __init__(self, dataset_root_dir, id):
		self.id = id
		self.dataset_root = dataset_root_dir

		v = VoiceUp(self.dataset_root, ids=self.id)

		self._voiceup = v

		self._load_df_to_self()

	def _load_df_to_self(self):
		for key in self._raw.keys():
			name = key.replace('.', '_')
			val = self._raw[key]

			self.__setattr__(name, val)
		

	def load_recording(self, recording_type='cough'):
		self._voiceup.load_recordings_data(recording_type)
		self._voiceup.load_functionals(recording_type)
		self._load_df_to_self()

	def __getitem__(self, item):
         return  self.__getattribute__(item)