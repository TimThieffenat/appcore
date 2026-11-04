# Sounds

Recorded sounds shared by every app of the base (`appcore/sounds/`). An app may
add its own in its `sounds/` folder (RiffFinder: the metronome clicks).

## Guitars (`guitar/*.snd` steel strings, `guitar_nylon/*.snd` nylon strings)

Steel-string and nylon-string acoustic guitars from the **FluidR3_GM** SoundFont by Frank Wen,
taken from the note-by-note version in
[midi-js-soundfonts](https://github.com/gleitz/midi-js-soundfonts) by
Benjamin Gleitzman, released under the
[Creative Commons Attribution 3.0 license](https://creativecommons.org/licenses/by/3.0/).
Every app that uses them must credit them (Settings page, `credits()`).

Changes made (`tools/build_sounds.py` in RiffFinder): each note is trimmed to its
attack, retuned exactly (the originals were a few cents off), resampled to
24 kHz, cut once it has died away and normalised. Exact tuning matters: PerfectPitch's
« Out of tune » mode detunes one note on purpose, all the others must be right.

## Soft keys

Synthesised by the base itself (`guitar_synth.keys_tone`): no file.

## File format

`.snd` = zlib( sample rate as little-endian uint32 + 16-bit little-endian mono PCM ).
