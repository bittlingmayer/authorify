# Authorify - writing style transfer engine

In image processing, style transfer is a known and, in some sense, solved problem. A lot of tools allow a user to make their photos look like they were painted by Van Gogh and not just selfies. These fun tools are now used widely in consumer applications.

At the same time the style transfer of the text is in the darker side of the world. The recent paper from Juncen Li et altri (https://nlp.stanford.edu/pubs/li2018transfer.pdf) reports 34% accuracy for sentiment transfer. 

This begs the question: can we train a neural network to apply a famous author's style to arbitrary text input (sentence, paragraph, etc...)?

For example, could a neural network transform a user's homework into the style of Shakespeare, or a user's comment into the style of 50 Cent?

## Are authors differentiable?

To approach the problem we must first understand whether it possible at all. Concretely: are two text snippets classifiable according to author?

One can argue from intuition that it is possible.  Suppose we have learnt on two texts, one of which was written by Tolstoy, the other one by Dostoevskiy. Logically a human can make a good guess about long sections of the same corpus.

But it is less clear if it is possible to do so on only short text snippets like a paragraph or sentence.  To make sure that it was, we trained fastText to classify text snippets by author.

3 corpora were selected - *Idiot* by Dostoevsky, *War and peace* by Tolstoy, and the lyrics of a few songs by 50 Cent. All the sentences were separated and marked with fastext style labels (prefixed with __label__).  Each paragraph also was labeled with similar label.  (We assume that the size of sentances and paragraphs a particular author uses usually matters.)

The classifier trained on this data yielded 83% accuracy.  This made us more confident that each author is identifiable by small text snippets.  A proper experiment would use rows from separate corpora to prevent the classifier from learning specific named entities like the names of characters in a novel, but a cursory peek at the data and predictions showed the classifier to be doing more than this.

## Apply style of an author

The next step is to find an effective architecture for style transfer.

Here the plans are the following:  
As in case of image style reduction, we assume that the text style can also be seen in corellations in different layers outputs of the NN. At this point it is still unclear the right way of getting the corellation based loss function for textual data. This is a work in progress. 

One existing method of text style application is described below by Mukil Kesavan in https://github.com/mukilk7/word-rnn, a word-level RNN similar to Karpathy's char-rnn.  Trained on the author's text this will generate a text which is similar to the style in which the author writes.  More specifically it will consider word frequencies for the author.

This is not enough for transferring the style of the author to the text content of the user. To address this issue,
first of all, the text is parsed with spacy to get the parts of speach. Then the generator is fed with the user content. If the sequential word in the user text is a noun or pronoun it considered as a start of input for the RNN and it generates a word which will follow in the return text. The expectation here is that the way author uses adjectives will create a text which is close to author's style.

Results are not exciting at this point and there are multiple reasons for that:

#### Unknown words
The network does not know what to do about unseen words.  It can only error or default to identity.

#### Nonsense output
The generated text is usually grammatically or semantically invalid.  It does use the words which are typical of author, but the output does not have any real meaning, though even the user input words are preserved in the output.

Unknown words can be handled with more data.


## Further work

The further work will be defining a meaningfull corellation-based losses. The expectation is that meaningful corellation definition will reduce the need for large datasets.


## Usage

#### Train
1. Write text corpus written by particular author to the file data/traincorpus.txt.
2. Train a model with `main.py -c train --num-epochs=*num_epochs*`

#### Generate
3. Write the user's sentence in file [master.py](master.py), line 104
4. Apply the author's style to the user's sentence with `main.py -c generate --num-words=1`
