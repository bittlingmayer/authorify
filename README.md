# Authorify - writing style transfer engine

In image processing techniques style transfer is a known and, in some sense, solved problem. A lot of tools allow one to make his photo look like it was done by Van Gogh and is not just a selfie. This fun tools are used widely nowadays. At the same time the style transfer of the text is in the darker side of the world. The recent paper from Juncen Li at all (https://nlp.stanford.edu/pubs/li2018transfer.pdf) states 34% accuracy in sentiment transfer. 
This brings us to the following idea:
Can we have a smart net which provided any text snippet (sentence, paragraph, etc...) will apply a famous authors style to it.
For example one would like to apply Shekspire style to his words, another one will prefer 50Cents style.

## Are authors differentiable?

To solve stated problem, first of all we needed to understand is it possible at all. More specificlly are 2 text snippets identifyable from authors perspective. One can argue that the answer is "yes" and there is nothing to understand. But suppose we are looking into 2 texts one of which was written by Tolstoy, the other one by Dostoevskiy. For sure if a human reads whole writing more or less familiar reader will identify the author. But is it possiible to do from short text snippets like sentence or paragraph. Are authors identifiable by only short snippets. To make sure that it can be done a simple test was done.
Facebooks fasText was used to classify text snippets by authors. 3 authors was selected - Dostoevskiy with his "Idiot", Tolstoy with his "War and peace", and 50Cent with few of his songs. All the sentences were separated and marked with fastext style labels (__label__). Each paragraph also was labed with similar label (we assume that the size of sentances and paragraphs a particular author uses usually matters). Classifier was trained on this data and it show 83% accuracy. This made us more confident that each autor is identifiable by small text snippets. For sure one can argue that because there are a lot of sentences there names of writing persons are used, city, country names are used, etc. this increased the accuracy of classifier, and the argument is right. But this was more like qualitive anlisys and not quantitive and having 60% accuracy would saticfy our needs too.

## Apply style of an author

The next step is to use algorithm for style transfer. Here the plans are the following:
As in case of image style reduction, we assume that the text style can also be seen in corellations in different layers outputs of the NN. At this point it is still unclear the right way of getting the corellation based loss function for textual data. This is a work in process. 
One other way of text style  application is described below. 
Mukil Kesavan in his work here: https://github.com/mukilk7/word-rnn described a word rnn similar to Karpathys char-rnn.
Trained on the proper authors text this will allow to generate a text which is similar to the style in which the author writes. More specifically it will consider word statistics common for the author.
This is not enough for transferring the style of the author to the text content of the user. To address this issue,
first of all, the text is parsed with spacy to get the parts of speach. Then the generator is fed with the user content. If the sequential word in the user text is a noun or pronoun it considered as a start of input for the RNN and it generates a word which will follow in the return text. The expectation here is that the way author uses adjectives will create a text which is close to author's style.
Results are not exciting at this point and there are multiple reasons for that: If the new word comes in the Net does not know how to treat it and just returns with error. The large training data will partially solve this problem but it is better to have a more clever way of acting. The generated text is usually nonsensical. Yes it uses the words which are common for author, but the output does not have any real meaning, though even the user input words are kept in output. Large dataset may also work in this case. 

## Further work

The further work will be defining a meaningfull corellation based losses. Expectation is that meaningfull corellation definition may decrease a need in a huge dataset for getting dolid results.


## Usage

1. To train the model fill text written by particular author into the file data/traincorpus.txt.
2. Train model with : 'main.py -c train --num-epochs=*num_epochs*'
3. Write the users sentence in file master.py line 104
4. Generate text with authors style with 'main.py -c generate --num-words=1'
