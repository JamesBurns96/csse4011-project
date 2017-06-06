import nltk
import csv
import itertools
import numpy as np
import time

import RNN

num_tags = 6
unknown_token = "UNKNOWN_TOKEN"





#X_train = np.asarray([[word_to_index[w] for w in sent[:-1]] for sent in tokenized_sentences])
#y_train = np.asarray([[word_to_index[w] for w in sent[1:]] for sent in tokenized_sentences])


xrows = [(",".join((str(x) for x in y))) for y in X_train]
yrows = [(",".join((str(x) for x in y))) for y in y_train]

with open('x.csv', 'w') as f:
    for row in xrows:
        f.write(row)
        f.write('\n')

with open('y.csv', 'w') as f:
    for row in yrows:
        f.write(row)
        f.write('\n')

model = RNN.RNN(vocabulary_size)

print "Expected Loss for random predictions: %f" % np.log(vocabulary_size)
print "Actual loss: %f" % model.cost(X_train[:100], y_train[:100])

t1 = time.time()
model.sgd_step(X_train[10], y_train[10], 0.005)
t2 = time.time()
print "STEP TIME: ", (t2-t1)*1000.0

model.sgd_train(X_train[:1000], y_train[:1000])
