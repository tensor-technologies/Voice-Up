# Voice Up
A small tool to generate dataset from the "voca ai" dataset.

## Usage
`python main.py <dataset_root_dir>`
* dataset_root_dir - where the submissions.json file is located (or the zip file of the dataset).

## Flow
1. Loads the 'submissions.json' file
2. Filters people with invalid info / no recordings
3. Takes the "positive people" and matchs each person with the most similar person from the "negative people".
4. If configured as such, exports to Excel.
5. If configured as such, copies the groups to the output directory.

* "If configured"
