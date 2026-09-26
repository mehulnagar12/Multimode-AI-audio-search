# Task 1 — Dataset inspection

We are building a local hybrid search PoC over a two-speaker audio dataset.

Do NOT write implementation code yet.

The dataset is already downloaded locally from the TalkBank two-speaker audio
dataset source:
https://huggingface.co/datasets/talkbank/callhome

There are 10 `.wav` files with associated metadata JSON.

Known metadata fields include:

* `source_file`: string
* `timestamps_start`: array
* `timestamps_end`: array
* `speakers`: array

Task:

1. Inspect the existing repository.
2. Locate all audio and metadata files.
3. Inspect representative JSON files and verify the actual schema.
4. Verify:

   * relationship between timestamps_start, timestamps_end and speakers
   * timestamp units
   * speaker identifier format
   * relationship between source_file and wav filename
   * number of speakers per file
   * audio duration of each file
   * metadata array length consistency
5. Identify any existing useful code/dependencies.
6. Recommend 5–6 files satisfying the assignment requirement of ~8–10 minute,
   two-speaker conversations. Record that this recommendation is an
   assignment subset; later pipeline runs may process all 10 available files.

Do not guess metadata semantics.

Do not download anything.

Do not modify the dataset.

Return only:

* dataset structure
* verified metadata semantics
* table of file / duration / speaker count
* recommended 5–6 files
* relevant existing code
* blockers or inconsistencies

Keep the response concise.
