import midi
import numpy as np
import os

lowerBound = 60   	# Lower bound for notes
upperBound = 72   	# Upper bound for notes
threshold = 0.5		# Statematrix activation threshold

midiFiles = "batch_test"

def midiToNoteStateMatrix(midifile):

	try:
		pattern = midi.read_midifile(midifile)  	# Load pattern from midi file
	except:
		return None

	timeleft = [track[0].tick for track in pattern] # Remaining time matrix for each track in the pattern

	posns = [0 for track in pattern]   

	statematrix = []    							# To be returned state matrix
	span = upperBound-lowerBound    				# The range of notes kept
	time = 0    

	state = [[0,0] for x in range(span)]   			# State for each note - first one is all null
	statematrix.append(state)

	while True:
		if time % (pattern.resolution / 4) == (pattern.resolution / 8): # New timestep detected (1/16 of a beat)
			# Crossed a note boundary. Create a new state, defaulting to holding notes
			oldstate = state                                        # Saved old state
			state = [[oldstate[x][0],0] for x in range(span)]       # New state = same as old state (holding note)
			statematrix.append(state)                               

		for i in range(len(timeleft)):  # For each track in pattern
			while timeleft[i] == 0:     # For this current track
				track = pattern[i]      # Retrieve actual track
				pos = posns[i]         

				evt = track[pos]        # Take an event from the current track
				if isinstance(evt, midi.NoteEvent): # If this events is a note activation
					if (evt.pitch < lowerBound) or (evt.pitch >= upperBound):   # Don't consider if note too high or too low
						pass
						# print "Note {} at time {} out of bounds (ignoring)".format(evt.pitch, time)
					else:
						if isinstance(evt, midi.NoteOffEvent) or evt.velocity == 0: # Consider note - Here is a note off
							state[evt.pitch-lowerBound] = [0, 0]    # No activation and scale to kept notes range
						else:
							state[evt.pitch-lowerBound] = [1, 1]    # Note just activated so vector [1,1]
				elif isinstance(evt, midi.TimeSignatureEvent):      # Time signature event
					if evt.numerator not in (2, 4): 				# Tempo modification
						# We don't want to worry about non-4 time signatures. Bail early!
						print "Found time signature event {}.".format(evt)
						if len(statematrix) < 17:
							return None
						return statematrix

				try:
					timeleft[i] = track[pos + 1].tick
					posns[i] += 1
				except IndexError:  # No more events?
					timeleft[i] = None

			if timeleft[i] is not None:
				timeleft[i] -= 1

		if all(t is None for t in timeleft):
			break

		time += 1
        
	return statematrix

def noteStateMatrixToMidi(statematrix, name="example"):
	print "Generating midi file for state matrix of shape", statematrix.shape
	statematrix = np.asarray(statematrix)		# Our statematrix
	pattern = midi.Pattern()					# Create a pattern (a song in midi)
	track = midi.Track()						# Create one track for the song
	pattern.append(track)						# Add track to pattern
    
	span = upperBound-lowerBound				# Note range
	tickscale = 55								## Speed
    
	lastcmdtime = 0
	prevstate = [[0,0] for x in range(span)]	# Previous state before the first state: all is off

	stateNb = 0
	for time, state in enumerate(statematrix + [prevstate[:]]): 
		stateNb += 1
		offNotes = []
		onNotes = []
		for i in range(span):					# For every note 
			n = state[i]						# Current activation
			p = prevstate[i]					# Previous activation
			if p[0] == 1:						# Previous note was activated
				if n[0] == 0:					# Current note is not activated
					offNotes.append(i)			# Add a note off
				elif n[1] == 1:					# Current note is activated again
					offNotes.append(i)			# Add a note off 
					onNotes.append(i)			# And reactivate the note
			elif n[0] == 1:						# Current note just activated
				onNotes.append(i)				# Activate it

		for note in offNotes:	# Add all of note events
			track.append(midi.NoteOffEvent(tick=(time-lastcmdtime)*tickscale, pitch=note+lowerBound))	
			lastcmdtime = time
			print "Note off", note+lowerBound, "State ", stateNb
		for note in onNotes:	# Add all on note events
			track.append(midi.NoteOnEvent(tick=(time-lastcmdtime)*tickscale, velocity=40, pitch=note+lowerBound))
			lastcmdtime = time
			print "Note On", note+lowerBound, "State ", stateNb
            
		prevstate = state
    
	eot = midi.EndOfTrackEvent(tick=1)			# Track finished
	track.append(eot)							# Add to track

	midi.write_midifile("{}.mid".format(name), pattern)	# Write song to bytes


# Returns a scaled state with a range of 1 octave (12) instead of the whole span
def minimizeState(state):
	"""
		minimizeState
		@input state, a flat state of arbitrary size
		\output minimizedState, the same state projected onto a size 12 vector (octave)
	"""
	minimizedState = [0 for i in range(12)]
	for i in range(len(state)):
		minimizedState[i%12] += state[i]
	maxState = max(minimizedState)
	for i in range(len(minimizedState)):
		if maxState != 0:
			minimizedState[i] = float(minimizedState[i]) / maxState

	return minimizedState


# Returns a flattened state matrix (size 2* span)
def flatStateMatrix(statematrix, getKeepActivated):
	flatStateMatrix = []
	for state in statematrix:
		flatActivate = []
		flatKeepActivated = []
		for note in state:
			flatActivate.append(max(note))
			if getKeepActivated:
				flatKeepActivated.append(note[1])
		if getKeepActivated:
			flatStateMatrix.append(flatActivate + flatKeepActivated)
		else:
			flatStateMatrix.append(flatActivate)
	reducedStateMatrix = []
	for matrix in flatStateMatrix:
		reducedStateMatrix.append(minimizeState(matrix))
	return np.asarray(reducedStateMatrix)

# Flat state matrix to two states 
def unflattenStateMatrix(flatStateMatrix, getKeepActivated):
	statematrix = []
	if getKeepActivated:
		offset = len(flatStateMatrix[0])/2
	else:
		offset = len(flatStateMatrix[0])
	for state in flatStateMatrix:
		newState = []
		for i in range(offset):
			if getKeepActivated:
				newState.append([state[i], state[i+offset]])
			else:
				newState.append([state[i], 0])
		statematrix.append(newState)
	return np.asarray(statematrix)

# Activates notes given treshold
def tresholdActivation(statematrix):
	activatedSm = []
	for state in statematrix:
		activatedState = []
		for note in state:
			if note >= threshold:
				activatedState.append(1)
			else:
				activatedState.append(0)
		activatedSm.append(activatedState)
	return np.asarray(activatedSm)

# Retrieves state matrices from midi files
def getStateMatrices(getKeepActivated):

	stateMatrices = []
	for file in os.listdir(os.path.abspath(midiFiles)):
		matrix = midiToNoteStateMatrix("./"+midiFiles+"/"+file)
		if matrix is not None:
			stateMatrices.append(flatStateMatrix(matrix, getKeepActivated))
		else:
			os.remove("./"+midiFiles+"/"+file);
	print "Number of files processed: ", len(stateMatrices)
	print "Total number of states: ", sum(len(mat) for mat in stateMatrices)
	return np.asarray(stateMatrices)

# Gets a random batch
def getNextBatch(stateMatrices, batchSize, notesNb):
	batch_xs = []
	batch_ys = []

	if batchSize > 0:
		for i in np.random.randint(0, len(stateMatrices), batchSize):
			while(len(stateMatrices[i]) <= notesNb+1):
				print "Number of states too small for stateMatrices[", i, "]"
				i += 1
			sampleStartPoint = np.random.randint(1, len(stateMatrices[i])-notesNb, 1)[0]
			batch_xs.append(stateMatrices[i][sampleStartPoint-1:sampleStartPoint-1+notesNb])
			batch_ys.append(stateMatrices[i][sampleStartPoint-1+notesNb])

		print "Total training data of size", len(batch_xs), "generated"
		return np.asarray(batch_xs), np.asarray(batch_ys)

	else:
		for matrix in stateMatrices:
			if(len(matrix) <= notesNb+1 ):
				print "Number of states too small for stateMatrices[", i, "]"
				continue
			for i in range(0, len(matrix)-notesNb, 1):
				batch_xs.append(matrix[i:i+notesNb])
				batch_ys.append(matrix[i+notesNb])
		print "Total training data of size", len(batch_xs), "generated"
		return np.asarray(batch_xs), np.asarray(batch_ys)