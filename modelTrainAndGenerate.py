from keras.models import Sequential
from keras.layers import Activation, LSTM, Dropout, Dense
from keras.callbacks import ModelCheckpoint
from keras.optimizers import RMSprop
from statematrix import *

n_input = 12
n_timesteps = 32
n_epoch = 1000
batch_size = 128
composition_size = 256							# number of timesteps when generating
n_refresh = 10									# Refresh the training batch / test

getKeepActivated = False						# Type of input matrice

training_mode = False							# Training or generating mode

savingFileName = "./weights.2139-1.26.hdf5"		# Saved network loading file
output_file = "generated"


# Network definition
model = Sequential()

model.add(LSTM(return_sequences=True, output_dim=96, input_shape=(n_timesteps, n_input)))
model.add(Dropout(0.2))

model.add(LSTM(return_sequences=False, output_dim=96))
model.add(Dropout(0.2))

model.add(Dense(n_input,  init='uniform'))

model.compile(loss='binary_crossentropy', optimizer='rmsprop', metrics=['accuracy'])


# Training mode
if training_mode:

	model.load_weights(savingFileName)

	matrices = getStateMatrices(getKeepActivated)	# Input the dataset

	for i in range(n_refresh):
		print "Step i =", i
		x_train, y_train = getNextBatch(matrices, -1, n_timesteps)	# -1 to get the whole dataset

		checkpoint = ModelCheckpoint("./saved/weights."+str(i)+"{epoch:02d}-{val_loss:.2f}.hdf5", 
					verbose = 2, monitor='loss', save_best_only=False, mode='auto')

		model.fit(x_train, y_train, batch_size=batch_size, nb_epoch=n_epoch, validation_split=0.2, 
					verbose=2, shuffle='batch', callbacks=[checkpoint])

# Generation mode
else:
	model.load_weights(savingFileName)

	matrices = getStateMatrices(getKeepActivated)

	x_comp, y_comp = getNextBatch(matrices, 1, n_timesteps)	# x_comp is 1 x n_timesteps x n_input

	for i in x_comp[0]:
		print i
	print 

	composition = np.copy(x_comp[0])						# Composition is n_timesteps x n_input

	for i in range(composition_size):
		pred = model.predict_on_batch(x_comp)				# Predict takes a None x n_timesteps x n_input and returns a n_input
		pred = tresholdActivation(pred)
		composition = np.vstack((composition, pred))		# Composition becomes len(composition)+1 x n_input
		del x_comp
		x_comp = np.asarray([composition[-n_timesteps:]])	# Keep only the n_timesteps last


	composition = unflattenStateMatrix(composition[n_timesteps:], getKeepActivated)
	noteStateMatrixToMidi(composition, output_file)			# Reconstitute midi file
