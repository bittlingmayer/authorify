from __future__ import print_function

"""
This file includes functions for training and then using the
trained model do: prediction, text generation and computing
average line loss.
"""

__author__ = "Mukil Kesavan"

import os
import pickle
import logging
import numpy as np
import tensorflow as tf
from nltk.tokenize import word_tokenize
from common.constants import *
import common.utils as utils
from wordrnn.data_processor import LocalDataProcessor
from wordrnn.model import WordRNN
import spacy
import en_core_web_sm
from wordrnn.configs import ModelParams

def train(data_processor, model, num_epochs, verbose=True, save=True, isInFit=False):
    """ Trains the given model and optionally saves it to disk.

        params:
            data_processor: the processor of data
            model: the tensorflow computational graph model
            num_epochs: number of training epochs
            backprob_lenth: the number of backprop steps
            batch_size: size of a batch of input (or sequence length)
            verbose: if true prints intermediate losses during training
            save: if true saves the trained model

        returns:
            list of losses over each training epoch
    """
    logger = logging.getLogger(DEFAULT_LOGGER)
    logger.info("Training...")
    tf.set_random_seed(1142)

    with tf.Session() as sess:
        # Resume Model Training if Possible
        ckpt = tf.train.get_checkpoint_state(os.path.dirname(TRAINED_MODEL_NAME))
        if ckpt and ckpt.model_checkpoint_path:
            logger.debug("Loading existing model & resuming training...")
            model['saver'].restore(sess, ckpt.model_checkpoint_path)
        # Tensorboard summary
        merged = tf.summary.merge_all()
        train_writer = tf.summary.FileWriter(DEFAULT_TENSORBOARD_LOG_DIR, sess.graph)        
        sess.run(tf.global_variables_initializer())
        # initialize word embedding if required
        if model['embedding_init_op'] is not None:
            embed_matrix = utils.create_embeddings_matrix(data_processor.vocab_to_idx)
            sess.run(model['embedding_init_op'], feed_dict={model['embed_placeholder']: embed_matrix})
        training_losses = []
        for epoch_idx, epoch_data in enumerate(data_processor.gen_epoch_data(num_epochs)):
            training_loss = 0
            steps = 0
            training_state = None
            for X, Y in epoch_data:
                steps += 1
                feed_dict = {model['x']: X, model['y']: Y}
                if training_state is not None:
                    feed_dict[model['init_state']] = training_state
                summary, batch_loss, training_state, _ = sess.run([merged,
                                                                   model['total_loss'],
                                                                   model['final_state'],
                                                                   model['train_step']],
                                                                  feed_dict)
                training_loss += batch_loss
            training_losses.append(training_loss / steps)
            train_writer.add_summary(summary, epoch_idx)
            if save:
                logger.debug("Saving model checkpoint for epoch %s", epoch_idx)
                model['params']['trained_epochs'] = model['params']['trained_epochs'] + 1
                model['saver'].save(sess, TRAINED_MODEL_NAME, global_step=model['params']['trained_epochs'])
                with open(TRAINED_MODEL_CONFIGS, "wb") as f:
                    pickle.dump(model['params'], f)
                    pickle.dump(data_processor.vocab_to_idx, f)
                    pickle.dump(data_processor.idx_to_vocab, f)
                    pickle.dump(data_processor.num_classes, f)
            if verbose:
                logger.debug("Avg. Training Loss for Epoch %s: %s", model['params']['trained_epochs'],
                             training_loss / steps)
    train_writer.close()
    if not isInFit:
        return training_losses
    else:
        return

def generate_text_from_model(textlen = 1):
    """
        Generates text using our trained RNN model. The "feel" of this
        text should resemble the style of the original corpus.

        params:
            textlen: number of words to generate
    """
    logger = logging.getLogger(DEFAULT_LOGGER)
    logger.debug("Loading saved model configs...")
    saved_params, vocab_to_idx, idx_to_vocab, num_classes = utils.load_saved_model_params()
    logger.debug("Generating text (num_words = %s)...", textlen)
    input_txt = "That was an interesting book"

    en_mod = en_core_web_sm.load()
    input_parsed = en_mod(input_txt)
    words = []
    for word in input_parsed:
        words.append(word.text)
        if word.pos_ is "NOUN" or word.pos_ is "PRON":
            input_x = [vocab_to_idx[i] for i in words]
            logger.debug(input_x)
            predict_idx = predict(saved_params, num_classes, vocab_to_idx, input_x, textlen=textlen)
#            if idx_to_vocab[min(predict_idx[0], num_classes)] is "ADJ":
            words.append(idx_to_vocab[min(predict_idx[0], num_classes)])

    #    starting_words = word_tokenize("take my hand away:")
#    input_x = [vocab_to_idx[i] for i in starting_words]
#    logger.debug(input_x)
#    predict_idx = predict(saved_params, num_classes, vocab_to_idx, input_x, textlen = textlen)
    return " ".join(words)


def predict(saved_params, num_classes, vocab_to_idx, input_x, textlen=100, isEstimator=False, predict_configs=None):
    def sampleWordFromPrediction(preds):
        """
        Samples a word based on prediction.
        """
        exp = np.exp(preds - np.max(preds))
        probs = exp / np.sum(exp)
        csum = np.cumsum(probs)
        r = np.random.random()
        return np.argmax(csum >= r)

    def pickRandomTopNWordFromPrediction(preds, topn, vocabsz):
        """
        Picks one of the topn words predicted,
        uniformly randomly.
        """
        preds = np.squeeze(preds)
        # set all non-topn probs to zero
        preds[np.argsort(preds)[:-topn]] = 0
        # renormalize probs
        preds = preds / np.sum(preds)
        return np.random.choice(vocabsz, 1, p=preds)[0]

    predict_idx = []
    saved_params.set_params(batch_size=1, num_steps=1, model_drop_out_rate=0)

    model = WordRNN(num_classes, saved_params).build_computation_graph()

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        # initialize word embedding if required
        if model['embedding_init_op'] is not None:
            embed_matrix = utils.create_embeddings_matrix(vocab_to_idx)
            sess.run(model['embedding_init_op'], feed_dict={model['embed_placeholder']: embed_matrix})
        model_directory = TRAINED_MODEL_NAME[:TRAINED_MODEL_NAME.rfind("/")]
        model['saver'].restore(sess, tf.train.latest_checkpoint(model_directory))
        predictions = tf.nn.softmax(model['logits'])
        init_state = None

        # Warm up our model with the seed words
        for w in input_x:
            x = np.array([[w]])
            if init_state is not None:
                feed_dict = {model['x']: x, model['init_state']: init_state}
            else:
                feed_dict = {model['x']: x}
            preds, init_state = sess.run([predictions, model['final_state']], feed_dict)
        lastgenword = pickRandomTopNWordFromPrediction(preds, 5, num_classes)

        if isEstimator: #TODO: check again -- compatibility
            textlen = len(input_x)

        # Let the text generation begin!
        for i in range(textlen):
            x = np.array([[lastgenword]])
            feed_dict = {model['x']: x, model['init_state']: init_state}
            preds, init_state = sess.run([predictions, model['final_state']], feed_dict)
            lastgenword = sampleWordFromPrediction(preds)
            #lastgenword = pickRandomTopNWordFromPrediction(preds, 5, num_classes)
            predict_idx.append(lastgenword)
    return predict_idx


def _get_specific_file_lines(local_filename, line_indices):
    sel_lines = []
    logger = logging.getLogger(DEFAULT_LOGGER)
    logger.debug("retrieving anomaly lines")
    with open(local_filename, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i in line_indices:
                sel_lines.append(line)
    logger.debug("returning anomaly lines - size = %s", len(sel_lines))
    return sel_lines


def compute_average_line_loss(local_filename, anomaly_percentile=95, input_url=None):
    """
    Computes the average line loss for each input line and returns those lines whose loss
    are above the specified percentile threshold. The loss in prediction per
    word is summed up and divided by the number of word to compute the
    final average loss value.

    params:
        local_filename: the test filename on the local filesystem
        anomaly_percentile: the percentile threshold for anomalous line detection (0-100)
        input_url: if the file needs to be downloaded first, then the url

    returns:
        list of lines with loss greater than anomaly_percentile will be returned
    """
    logger = logging.getLogger(DEFAULT_LOGGER)

    logger.debug("Loading saved model configs...")
    saved_params, vocab_to_idx, _, num_classes = utils.load_saved_model_params()
    saved_params.set_params(batch_size=1, num_steps=1, model_drop_out_rate=0)
    test_dp = LocalDataProcessor(saved_params, input_url=input_url,
                                 local_filename=local_filename,
                                 num_classes=num_classes)
    linebreak_indices = [i for i, v in enumerate(test_dp.corpus) if v == test_dp.vocab_to_idx['\n']]
    linebreak_indices.append(len(test_dp.corpus))
    logger.debug("Num lines in test data file = %s", len(linebreak_indices))

    model = WordRNN(num_classes, saved_params).build_computation_graph()
    avglinelosses = []

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        # initialize word embedding if required
        if model['embedding_init_op'] is not None:
            embed_matrix = utils.create_embeddings_matrix(vocab_to_idx)
            sess.run(model['embedding_init_op'], feed_dict={model['embed_placeholder']: embed_matrix})
        model_directory = TRAINED_MODEL_NAME[:TRAINED_MODEL_NAME.rfind("/")]
        model['saver'].restore(sess, tf.train.latest_checkpoint(model_directory))
        init_state = None
        #Go thro' line by line
        prev_lbi = 0
        ind = 0
        for lbi in linebreak_indices:
            lineloss = 0
            ind += 1
            #Go thro' each word of each line
            line_words = word_tokenize(test_dp.corpus[prev_lbi: min(lbi, len(test_dp.corpus))])
            #skip extremely small lines
            if len(line_words) < 2:
                prev_lbi = lbi
                continue
            for wi in range(len(line_words) - 1):
                x = np.array([[line_words.corpus[wi]]])
                y = np.array([[line_words.corpus[wi + 1]]])
                if init_state is not None:
                    feed_dict = {model['x']: x, model['y']: y, model['init_state']: init_state}
                else:
                    feed_dict = {model['x']: x, model['y']: y}
                loss, init_state = sess.run([model['total_loss'],
                                             model['final_state']], feed_dict)
                lineloss += loss
            linelen = lbi - prev_lbi
            avglineloss = lineloss / float(linelen)
            prev_lbi = lbi
            avglinelosses.append(avglineloss)
            if ind % 1000 == 0:
                logger.debug("Average Line Len = %s Loss = %s", linelen, avglineloss)


    ap = np.percentile(avglinelosses, anomaly_percentile)
    logger.debug("%s Percentile Average Line Loss Value = %s", anomaly_percentile, ap)
    line_indices = [i for i, l in enumerate(avglinelosses) if l >= ap]

    return _get_specific_file_lines(local_filename, line_indices)
