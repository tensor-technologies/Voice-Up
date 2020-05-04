import os
import numpy as np
import pandas as pd

import audio_utils
import utils
from opensmile import opensmile

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
			val = self._raw[key]

			self.__setattr__(key, val)
		

	def load_recording(self, recording_name='cough', vad_and_normalization=True):
		"""
		Loads recording data & functionals to the current object
		Can be accessed as normal attributes. e.g person.F0_sma_de_linregc1
		"""
		self._voiceup.load_recordings_data(recording_name, vad_and_normalization)
		self._voiceup.load_functionals(recording_name)
		self._load_df_to_self()

	def get_lld(self, recording_name='cough'):
		col_name = 'recordings_%s' % recording_name
		assert col_name in self._raw.keys(), "Column %s not in df" % col_name

		return opensmile.get_lld(self._raw[col_name])

	def __getitem__(self, item):
         return  self.__getattribute__(item)