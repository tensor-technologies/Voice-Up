# Voice Up
A small tool to generate a balanced and meta-data matched training dataset from the "voca ai" dataset.

## Usage
`python main.py <dataset_root_dir>`
* dataset_root_dir - where the submissions.json file is located (or the zip file of the dataset).

## Flow
1. Loads the 'submissions.json' file
2. Filters people with invalid / no recordings
3. Takes the "positive covid19 people" and matches each person with the most similar person from the "negative covid19 people". The similarity is measured according to: gender, smoking habits, country, age (in that order)
4. If configured as such, exports to Excel (the default)
5. If configured as such, copies the groups to the output directory (the default)

* "If configured"
