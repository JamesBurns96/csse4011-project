import csv
import numpy as np
import time

import RNN

SEQUENCE_START = -1000
SEQUENCE_STOP = -2000
NO_DATA = -3000
NUM_FEATURES = 36
NUM_DRIVERS = 2


def outer_join(alist, blist):
    result = []
    for a in alist:
        for b in blist:
            result.append((a, b))
    return result


def load_data(directory):
    data = dict()

    FILES_AND_PREFIXES = [('acc.csv', 'acc'), ('brake.csv', 'brk'),
                          ('clutch.csv', 'cl'), ('gear.csv', 'gr'),
                          ('rigid.csv', 'rgd'), ('steer.csv', 'st')]

    for (filename, prefix) in FILES_AND_PREFIXES:
        with open(directory + '/' + filename, 'r') as fl:
            for ln in csv.DictReader(fl):
                ts = float(ln['timeStamp']) + float(ln['sampleNumber'])/20.
                if not data.has_key(ts):
                    data[ts] = dict()

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
            assert(last_ts < ts)

        raw_line = []

        dat = data[ts]
        for (p, s) in outer_join([p[1] for p in FILES_AND_PREFIXES], SENSOR_SUFFIXES):
            raw_line.append(dat.get(p + '-' + s, NO_DATA))

        data_raw.append(raw_line)

    return np.asarray(data_raw)

data_james = load_data('data/james/')
print 'loaded james data. shape ', data_james.shape
assert(data_james.shape[1] == NUM_FEATURES)

data_dan = load_data('data/dan0/')
print 'loaded dan0 data. shape ', data_dan.shape
assert(data_dan.shape[1] == NUM_FEATURES)

model = RNN.RNN(NUM_FEATURES, NUM_DRIVERS)

print "Expected Loss for random predictions: %f" % np.log(NUM_DRIVERS)
# print "Actual loss: %f" % model.cost(X_train[:100], y_train[:100])
#
# t1 = time.time()
# # model.sgd_step(X_train[10], y_train[10], 0.005)
# t2 = time.time()
# print "STEP TIME: ", (t2-t1)*1000.0
#
# # model.sgd_train(X_train[:1000], y_train[:1000])
