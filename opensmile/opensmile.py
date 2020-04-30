import os
import tempfile
import subprocess
from io import BytesIO
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import arff

from . import HTK
dirname = os.path.dirname(__file__)

# Hack to allow arff to be able to read unknown attribute
arff.ARFF_TYPES['unknown'] = str

DEBUG = False
OPENSMILE_EXE = os.path.join(dirname, 'SMILExtract_Release.exe')


def _run_opensmile(conf_file, input_file, lld_output=False):
	# TODO change temp method to a more robust one. 
	# output_file = tempfile.mktemp()
	output_file = os.path.join(dirname, 'output.csv')
	lld_output_file = os.path.join(dirname, 'output_lld.csv')

	args = [ OPENSMILE_EXE, '-C', os.path.join(dirname, conf_file), '-csvoutput', output_file, '-I', input_file ] #, '--lldhtkoutput', 'test.htk'
	if lld_output:
		args.extend(['--lldcsvoutput', lld_output_file])

	res = subprocess.call(
		args,
		stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
		)
	assert res == 0

	output = ''
	with open(output_file, 'rb') as fileobj:
		output = fileobj.read()
	return output

def _csv_to_array(csv_data):
	return np.array([ np.array(line.split(';'), dtype=float) for line in csv_data.decode('ascii').splitlines() ])

def _csv_to_df(csv_file,  sep=';'):
	return pd.read_csv(csv_file, sep=sep)

def get_chroma(wavfile):
	res = _run_opensmile('config\\chroma_fft.conf', wavfile)
	return _csv_to_array(res)

def get_mfcc(wavfile):
	res = _run_opensmile('config\\MFCC12_0_D_A.conf', wavfile)
	htk = HTK.HTKFile()
	htk.load(BytesIO(res))
	return np.array(htk.data)

def get_lld(wavfile):
	_run_opensmile('config\\avec2013.conf', wavfile, lld_output=True)
	lld_output_file = os.path.join(dirname, 'output_lld.csv')
	return _csv_to_df(lld_output_file)

def get_functionals(wavfile):
	res = _run_opensmile('config\\emobase.conf', wavfile)
	
	df = _csv_to_df(BytesIO(res))
	df = df.drop(['name','frameTime'], axis=1)
	return df.iloc[0]

def main():
	_run_opensmile('emobase.conf', 'laugh.wav')

if __name__ == "__main__":
	main()