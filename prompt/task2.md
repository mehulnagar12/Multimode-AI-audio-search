# Task 2 — Transcription and speaker alignment

Using the dataset/schema verified in Stage 1, implement transcription and speaker alignment.

Requirements:

1. Generate timestamped transcripts from the selected CALLHOME `.wav` files.
2. Transcription may be local or hosted, but transcripts must be persisted so audio is not retranscribed during search/tests.
3. Use the existing CALLHOME timestamp/speaker metadata as ground-truth speaker information if Stage 1 confirmed it provides speaker intervals.
4. Do NOT add a diarization model when speaker annotations already exist.
5. Align ASR timestamps to speaker intervals using temporal overlap.
6. For segments overlapping multiple speakers:

   * use maximum temporal overlap, or
   * split when reliable word timestamps make this possible.
     Keep the behavior deterministic.
7. Persist aligned transcript segments containing:

   * source_file
   * speaker_id
   * start_time
   * end_time
   * text

Add focused tests for:

* metadata parsing
* timestamp overlap
* boundary cases
* speaker assignment

Do not implement embeddings/search/database yet.

Do not fabricate transcripts.

Reuse existing repository structure where reasonable.

Run the tests and report:

* files changed
* alignment approach
* transcription approach
* test results
* any issues discovered
