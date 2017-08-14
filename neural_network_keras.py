import sys, os
from keras.models import Sequential, load_model
from keras.layers import Dense, Dropout
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
from random import random
from sklearn.metrics import roc_curve, auc
from graph_tool.all import *

import prep_input
import scenario_info
import create_graph
from metrics import *

"""
Vertex features - all 12 of these are calculated using graph-tool's functions:
["Out-degree", "In-degree", "# of in-neighbors", "# of out-neighbors", 
 "Page Rank", "Betweenness", "Closeness", "Eigenvector", "Katz",
 "Authority centrality", "Hub centrality", "Clustering coefficient"]
The above features will be normalized and placed in a vector for each vertex
in each time interval
"""

VECTOR_SIZE = 12 # number of vertex characteristics in the vector

# Disable print statements
def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# Enable print stements
def enablePrint():
    sys.stdout = sys.__stdout__

'''
Trains the model
Parameters:
x_train - numpy array for x training set
y_train - numpy array for y training set
pcap_duration - pcap duration (seconds) - available on CTU website
step_length - step duration (seconds)
save_model - True if model is saved in an h5 file
savefile - name of file that the model is saved to
'''
def create_model(x_train, y_train, pcap_duration, step_length, \
	save_model=True, savefile="model.h5"):
	print "Starting the creation of the model"
	model = Sequential()
	# Input arrays of shape (num_vertices, 12) and
	# output arrays of shape (num_vertices, 1)
	model.add(Dense(15, input_dim=12, activation='relu'))
	# Dropout: Randomly set half (arbitrarily fraction) of the input units
	# to 0 at each update during training, which helps prevent overfitting.
	# Perhaps lower the rate if accuracy on the training or validation set
	# is low and increase if training set worked well but test set did not
	model.add(Dropout(0.5))
	#model.add(Dense(15, activation='relu'))
	#model.add(Dropout(0.5))
	#model.add(Dense(15, activation='relu'))
	#model.add(Dropout(0.5))
	model.add(Dense(1, activation='sigmoid'))
	model.compile(optimizer='rmsprop', loss='mean_squared_error', \
		metrics=['accuracy', true_positives, true_negatives, \
		false_positives, false_negatives, true_positive_rate, \
		true_negative_rate, false_positive_rate, false_negative_rate])
	model.fit(x_train, y_train, epochs=2000, \
		batch_size=int(pcap_duration/(step_length * 2)))
		#sample_weight = weights)
		# class_weight = {0.: 1., 1.: 25000})  --> doesn't do anything??
	# for scenario 12, I think there are 187 1 outputs and 466294 total outputs
	# - hence the 1:2500 class weight
	if save_model == True:
		try:
			model.save(savefile)
			print "Saved model as " + str(savefile)
		except:
			print "Couldn't save the model"
	return model

'''
Evaluates the model given x_test and y_test
Parameters:
model - model generated by create_model or loaded from h5 file
x_test - numpy array for x test set
y_test - numpy array for y test set
pcap_duration - pcap duration (seconds) - available on CTU website
step_length - step duration (seconds)
'''
def evaluate_model(model, x_test, y_test, pcap_duration, step_length):
	score = model.evaluate(x_test, y_test, \
		batch_size=int(pcap_duration/(step_length * 2)))
	loss, accuracy, true_positives, true_negatives, false_positives, \
		false_negatives, true_positive_rate, true_negative_rate, \
		false_positive_rate, false_negative_rate = score
	print "\n"
	print "Loss: " + str(loss)
	print "Accuracy: " + str(accuracy * 100) + "%"
	print "True positives: " + str(true_positives)
	print "True positive rate: " + str(true_positive_rate * 100) + "%"
	print "True negatives: " + str(true_negatives)
	print "True negative rate: " + str(true_negative_rate * 100) + "%"
	print "False positives: " + str(false_positives)
	print "False positive rate: " + str(false_positive_rate * 100) + "%"
	print "False negatives: " + str(false_negatives)
	print "False negative rate: " + str(false_negative_rate * 100) + "%"

'''
Displays the Receiver Operator Characteristic (ROC) curve with the area
under its curve given the parameter model and x and y data arrays
'''
def generate_roc_curve(model, x_test, y_test, data_scenario, model_scenario):
	# Get array of probabilities of that the y result is a 1
	y_score = model.predict_proba(x_test)
	# Compute ROC curve and ROC area for each class
	fpr, tpr, _ = roc_curve(y_test, y_score)
	roc_auc = auc(fpr, tpr)
	plt.figure()
	plt.plot(fpr, tpr, color='darkorange',
	         lw=2, label='ROC curve (area = %0.2f)' % roc_auc)
	plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
	plt.xlim([0.0, 1.0])
	plt.ylim([0.0, 1.05])
	plt.xlabel('False Positive Rate')
	plt.ylabel('True Positive Rate')
	plt.title('Receiver operating characteristic of scenario ' \
		+ str(model_scenario) + '\'s model on scenario ' \
		+ str(data_scenario) + '\'s data')
	plt.legend(loc="lower right")
	plt.savefig("roc_curves/hidden_layers_3/model_" + str(model_scenario) + "_data_" + \
		str(data_scenario) + "_hidden_layers_3.png")
	#plt.show()

def main():
	step_length = 60
	interval_length = 120
	
	model_scenario = 9
	data_scenario = 9 # scenario 9's data has good results for several models

	#pcap_file = sys.argv[1]
	# Dictionary of malicious IP addresses with start timestamp as its value
	botnet_nodes = scenario_info.get_botnet_nodes(data_scenario)
	pcap_duration = scenario_info.get_pcap_duration(data_scenario) # * 0.1

	savefile_x = 'Scenario_' + str(data_scenario) + '_model/' + \
		'x_scenario_' + str(data_scenario) + '.txt'
	savefile_y = 'Scenario_' + str(data_scenario) + '_model/' + \
		'y_scenario_' + str(data_scenario) + '.txt'
	model_savefile = 'Scenario_' + str(model_scenario) + '_model/' + \
		'model_scenario_' + str(model_scenario) + '_hidden_layers_3.h5'
	
	'''
	x, y = prep_input.generate_input_arrays(pcap_file, botnet_nodes, pcap_duration, \
		step_length = step_length, interval_length = interval_length, \
		do_save=True, savefile_x=savefile_x, savefile_y=savefile_y, verbose = True)
	'''
	x, y = prep_input.load_input_arrays(filename_x=savefile_x, filename_y=savefile_y)
	
	'''
	x_train, y_train, x_test, y_test = prep_input.separate_into_sets(x, y, \
		training_proportion = 0.7)
	'''
	balanced_savefile_x, balanced_savefile_y = \
		prep_input.balance_data(savefile_x, savefile_y)
	balanced_x, balanced_y = prep_input.load_input_arrays(filename_x=balanced_savefile_x, \
		filename_y=balanced_savefile_y)
	# Note that the test set contains all the data so obviously it includes the
	# training data...since the training data is so limited, it likely will have
	# little effect on the outcome though
	_, _, x_test, y_test = prep_input.separate_into_sets(x, y, training_proportion = 0)
	x_train, y_train, _, _ = \
		prep_input.separate_into_sets(balanced_x, balanced_y, training_proportion = 0.7)

	weighted_y_train = np.copy(y_train)
	weighted_y_train[weighted_y_train == 1] = 3.5
	weighted_y_test = np.copy(y_test)
	weighted_y_test[weighted_y_test == 1] = 3.5
	# TEMPORARY: I AM APPLYING MY WEIGHTS HERE INSTEAD OF IN A CUSTOM LOSS FUNCTION
	# (WHICH IS PROBABLY MORE CORRECT); CHANGE THIS LATER

	"""
	model = create_model(x_train, weighted_y_train, pcap_duration, step_length, \
	 	save_model=True, savefile=model_savefile)
	"""
	model = load_model(model_savefile, custom_objects = \
		{'true_positives': true_positives, 'false_positives': false_positives, \
		 'true_negatives': true_negatives, 'false_negatives': false_negatives, \
		 'true_positive_rate': true_positive_rate, \
		 'false_positive_rate': false_positive_rate, \
		 'true_negative_rate': true_negative_rate, \
		 'false_negative_rate': false_negative_rate})
	evaluate_model(model, x_test, y_test, pcap_duration, step_length)
	generate_roc_curve(model, x_test, y_test, data_scenario, model_scenario)

main()