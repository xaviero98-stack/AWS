import argparse
import os
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import callbacks

# Defining the model
def model(X_train, y_train, epochs, batch_size, early_stop_patient):
    """Generates the model instanciating the LSTMStockPredictor and makes it read
    for use"""
    model = keras.models.Sequential([
        keras.layers.LSTM(units = 264, return_sequences = True, input_shape= (X_train.shape[1], 1)),
        keras.layers.Dropout(0.2),
        keras.layers.LSTM(units = 128, return_sequences = True),
        keras.layers.Dropout(0.2),
        keras.layers.LSTM(units = 64, return_sequences = False), # These are the core LSTM layers, they contain the neurons that adjust themselves.
        keras.layers.Flatten(), # We convert multidimensional output of the LSTM layers into a one dimensional output so we can pass the results to the next dense layer
        keras.layers.Dropout(0.2),
        keras.layers.Dense(units = 32), # The regular fully collected layer with 32 neurons
        keras.layers.Dropout(0.2), # We use 4 dropout layers that consist of layers that block the backpropagation process of a random subset of 20% neurons each batch, it's a regularization technique that helps with overfitting so the neural network doesn't relies too heavily on asubset of neurons. 
        keras.layers.Dense(units = 1)]) # The last result is a layer that contains a single units which will try to return a value that matches the loss function as close as possible and which will be compared with the value expected by the loss function

    model.compile(optimizer = 'adam', # we use Adaptative Moment for gradient descent 
                 loss = 'mse') # And the mean squared error metric as the loss function

    early_stop = keras.callbacks.EarlyStopping(monitor = "loss", # We monitor the loss function
                                               patience = early_stop_patient, # we use the set value early_stop_patient
                                               restore_best_weights = True) # we use the weights that gave us the better results on the training process

    model.fit(X_train, y_train, # We ask to train the model the fit predict the argument y_train using the argument X_train
             epochs = epochs, # Also determined by the epoch value passed to the model function
             batch_size = batch_size, # Same as above
             callbacks = [early_stop]) # We use the defined early_stop variable with paramters from passed to the this model() function 

    return model


def _data_transformation(adjclose_array, window = 30):
    """Cut the adjclose column in n columns to be feeded to the model."""
    # This process is the exact same we follow on the notebook when we prepare data to be used for predicitons with the endpoint, it is detailed on the notebook:
    X_data = []
    y_data = [] # Price on next day
    window = window
    num_shape = len(adjclose_array)

    for i in range(window, num_shape):
        X_data_reshaped = np.reshape(adjclose_array[i-window:i], (window, 1))
        X_data.append(X_data_reshaped)
    X_data = np.stack(X_data)
    y_data = np.stack(adjclose_array)[window:]
    return X_data, y_data


def _load_training_data(base_dir): # Here we find the data we stored in the notebook as train_jaji.csv in S3, put it inside a dataframe and extract a numpy array with its values. This array is then transformed with the previous shaping function _data_transformation.
    """Load the training data from S3."""
    train_data = pd.read_csv(os.path.join(base_dir, "train_jaji.csv")).adjclose.values
    return _data_transformation(train_data)

def _load_testing_data(base_dir): # Not sure why the lab creates this function if we don't use it in futher steps
    """Load the test data from S3."""
    test_data = pd.read_csv(os.path.join(base_dir, "test_jaji.csv")).adjclose.values
    return _data_transformation(test_data)

def _parse_args(): # We create an argument parser that contains all the variable we will pass to the functions above defined
    parser = argparse.ArgumentParser()

    parser.add_argument('--batch-size', type = int, default = 32)
    parser.add_argument('--epochs', type = int, default = 1)
    parser.add_argument('--early-stop', type = int, default = 10)

    # Environment variables given by the training image 
    parser.add_argument('--model-dir', type = str, default = os.environ['SM_MODEL_DIR'])
    parser.add_argument('--train', type = str, default = os.environ['SM_CHANNEL_TRAINING'])
    parser.add_argument('--current-host', type = str, default = os.environ['SM_CURRENT_HOST'])
    parser.add_argument('--hosts', type = list, default = json.loads(os.environ['SM_HOSTS']))

    return parser.parse_args()


if __name__ == "__main__": # We create the data we need with the required shape. We use _load_training_data to retrieve and create well shaped X_train and y_train, we then pass it to the model, and we finally save it on the 
    args = _parse_args()

    X_train, y_train = _load_training_data(args.train)
    stock_predictor = model(X_train, y_train, 
                             args.epochs, 
                             args.batch_size, 
                             args.early_stop)
    
    # Save the model using the arg.model_dir that contains the S3 address drawn from the environment variables of the image and the directory doesn't exist inside the bucket we create it and save the model there.
    version = '00000000'
    ckpt_dir = os.path.join(args.model_dir, version)
    if not os.path.exists(ckpt_dir):
        os.makedirs(ckpt_dir)
    stock_predictor.save(ckpt_dir)
