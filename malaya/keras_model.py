import keras
import numpy as np
import tensorflow as tf
from keras.models import Model, Input
from keras.layers import LSTM, Embedding, Dense, TimeDistributed, Dropout, Bidirectional, Reshape, Concatenate, Lambda
from keras_contrib.layers import CRF
from keras import backend as K
from keras.backend.tensorflow_backend import set_session
from .utils import str_idx, generate_char_seq
from .text_functions import entities_textcleaning
set_session(tf.InteractiveSession())

class Concat_Model:
    def __init__(self, model, settings):
        self._model = model
        self._settings = settings
    def predict(self, string):
        assert (isinstance(string, str)), "input must be a string"
        string = entities_textcleaning(string.lower())
        batch_x = str_idx([string],self._settings['word2idx'],2)
        batch_x_char = generate_char_seq(batch_x,self._settings['idx2word'],self._settings['char2idx'])
        results = np.argmax(self._model.predict([batch_x, batch_x_char])[0],1)
        return [(string[no],self._settings['idx2tag'][str(i)]) for no, i in enumerate(results)]

class Word_Model:
    def __init__(self, model, settings):
        self._model = model
        self._settings = settings
    def predict(self, string):
        assert (isinstance(string, str)), "input must be a string"
        string = entities_textcleaning(string.lower())
        batch_x = str_idx([string],self._settings['word2idx'],2)
        results = np.argmax(self._model.predict(batch_x)[0],1)
        return [(string[no],self._settings['idx2tag'][str(i)]) for no, i in enumerate(results)]

class Char_Model:
    def __init__(self, model, settings):
        self._model = model
        self._settings = settings
    def predict(self, string):
        assert (isinstance(string, str)), "input must be a string"
        string = entities_textcleaning(string.lower())
        batch_x = str_idx(string,self._settings['char2idx'],0)
        results = np.argmax(self._model.predict(batch_x),1)
        return [(string[no],self._settings['idx2tag'][str(i)]) for no, i in enumerate(results)]

def get_char_bidirectional(char2idx,tag2idx):
    input_word = Input(shape=(None,))
    model = Embedding(input_dim=len(char2idx) + 1, output_dim=128, mask_zero=True)(input_word)
    model = Bidirectional(LSTM(units=128, return_sequences=False, recurrent_dropout=0.1))(model)
    out = Dense(len(tag2idx),activation='softmax')(model)
    model = Model(input_word, out)
    return model

def get_crf_lstm_bidirectional(word2idx,tag2idx):
    input_word = Input(shape=(None,))
    model = Embedding(input_dim=len(word2idx) + 1, output_dim=128, mask_zero=True)(input_word)
    model = Bidirectional(LSTM(units=64, return_sequences=True, recurrent_dropout=0.1))(model)
    model = TimeDistributed(Dense(50, activation="relu"))(model)
    crf = CRF(len(tag2idx))
    out = crf(model)
    model = Model(input_word, out)
    return model

def get_crf_lstm_concat_bidirectional(char2idx,word2idx,tag2idx):
    input_word = Input(shape=(None,))
    input_char = Input(shape=(None,None,))
    model_char = Embedding(input_dim=len(char2idx) + 1, output_dim=128)(input_char)
    s = K.shape(model_char)
    def backend_reshape(x):
        return K.reshape(x, (s[0]*s[1],s[2],128))
    model_char = Lambda(backend_reshape)(model_char)
    model_char = Bidirectional(LSTM(units=50, return_sequences=True, recurrent_dropout=0.1))(model_char)
    def sliced(x):
        return x[:,-1]
    model_char = Lambda(sliced)(model_char)
    def backend_reshape(x):
        return K.reshape(x, (s[0],s[1],100))
    model_char = Lambda(backend_reshape)(model_char)
    model_word = Embedding(input_dim=len(word2idx) + 1, output_dim=64, mask_zero=True)(input_word)
    concated_word_char = Concatenate(-1)([model_char,model_word])
    model = Bidirectional(LSTM(units=50, return_sequences=True, recurrent_dropout=0.1))(concated_word_char)
    model = TimeDistributed(Dense(50, activation="relu"))(model)
    crf = CRF(len(tag2idx))
    output = crf(model)
    model = Model(inputs=[input_word, input_char], outputs=output)
    return model
