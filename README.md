# Voice Up
A small tool to generate trainning dataset from the "voca ai" dataset.

## Usage
python main.py <dataset_root_dir>
dataset_root_dir - where the submissions.json file is located (or the zip file of the dataset).

## Flow
1. Loads the 'submissions.json' file
2. Filters people with unvalid info / no recordings
3. Takes the "positive people" and match each person with the most similar person from the "negative people"
4. If configured as such, exports to Excel.
4. If configured as such, copies the groups to the output directory.
