# LSTMMusicGeneration
Basic neural network generating music from MIDI files using LSTM

## Features
Using a corpus of .MIDI file, extracts the melody from them and trains a two LSTM layer neural network. Then, given a sufficient amount of first notes from a melody (default is 16), outputs the following notes, one at a time. Then, reassembles a midi file from the generated melody

## Use
In order to use this little soft, you need:
* a set of MIDI files
* keras installed on your machine (therefore, either tensorflow or theanos is needed)
Then, do the following:
1. Set the `training_mode` variable to `true`
2. Run the program with python. This will create checkpoints files in `.hdf5` 
3. Set the `savingFileName` variable to the best checkpoint file (or whichever one you want to use instead), that is the one with the smallest lost value (last number of the filename is its loss value)
4. Set the `training_mode` variable to `false`
5. Run again. This will create a `.MIDI` file with generated melody from 16 notes randomly chosen from your corpus of midi files. Run again to get different results
