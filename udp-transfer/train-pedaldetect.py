import csv
import numpy as np

from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split, GridSearchCV

import random

SEQUENCE_START = -1000
SEQUENCE_STOP = -2000
NO_DATA = -3000
NUM_FEATURES = 12
NUM_DRIVERS = 2

FILES_AND_PREFIXES = [('steer.csv', 'acc'), ('button.csv', 'bt')]


def compute_accuracy(clf, data, target):
    y = clf.predict(data)
    score = accuracy_score(target, y)
    return score


def print_accuracy(clf, data1, target1, data2, target2):
    print "- Training set", compute_accuracy(clf, data1, target1)
    print "- Testing set", compute_accuracy(clf, data2, target2)


def outer_join(alist, blist):
    result = []
    for a in alist:
        for b in blist:
            result.append((a, b))
    return result


def load_data(directory):
    data = dict()

    for (filename, prefix) in FILES_AND_PREFIXES:
        with open(directory + '/' + filename, 'r') as fl:
            for ln in csv.DictReader(fl):
                ts = float(ln['timeStamp']) + float(ln['sampleNumber']) / 20.
                if not data.has_key(ts):
                    data[ts] = dict()

                print (fn, ln)

                data[ts][prefix + '-ax'] = float(ln['accX'])
                data[ts][prefix + '-ay'] = float(ln['accY'])
                data[ts][prefix + '-az'] = float(ln['accZ'])
                data[ts][prefix + '-gx'] = float(ln['gyrX'])
                data[ts][prefix + '-gy'] = float(ln['gyrY'])
                data[ts][prefix + '-gz'] = float(ln['gyrZ'])

    SENSOR_SUFFIXES = ['ax', 'ay', 'az', 'gx', 'gy', 'gz']

    data_raw = []
    last_ts = None
    for ts in data:
        if last_ts is not None:
            assert (last_ts < ts)
        raw_line = []
        dat = data[ts]

        for (p, s) in outer_join([p[1] for p in FILES_AND_PREFIXES], SENSOR_SUFFIXES):
            raw_line.append(dat.get(p + '-' + s, NO_DATA))

        data_raw.append(raw_line)
    return np.asarray(data_raw)

valid_indices = []
# for fn in 'acceleratorStationary'.split(','):
fn = 'clutchStationary'

data_james = load_data('pedaldetect-data/' + fn)
print 'loaded james data. shape ', data_james.shape
assert (data_james.shape[1] == NUM_FEATURES)

james_missing_count = 0
for (datum, index) in zip(data_james, range(len(data_james))):
    missing = False
    for component in datum:
        if component == -3000:
            missing = True
    if missing:
        james_missing_count += 1
    else:
        valid_indices.append(index)

print 'missed {0} of {2}\' packets. {1}%'. \
    format(james_missing_count, 100. * james_missing_count / data_james.shape[0], fn)

valid_data = [data_james[i] for i in valid_indices]

train_idx = [i for i in range(len(valid_data)) if random.uniform(0, 1) < 0.1]

print 'valid samples: ', len(valid_data)
print 'training samples: ', len(train_idx)

X = [[x[3], x[4], x[5]] for x in valid_data]
y = [x[9]/2. for x in valid_data]

X_test, X_train, y_test, y_train = train_test_split(X, y, test_size=0.9)

parameters = {
    'C': [0.01, 0.1, 1, 10, 100],
}

classifier = SVC(kernel='linear')
clf = GridSearchCV(classifier, parameters, verbose=3, n_jobs=-1)
clf.fit(X_train, y_train)

best_params = clf.best_estimator_.get_params()
for p in sorted(parameters):
    print "{0}: {1}".format(p, best_params[p])

print_accuracy(clf, X_train, y_train, X_test, y_test)



false_positives =
