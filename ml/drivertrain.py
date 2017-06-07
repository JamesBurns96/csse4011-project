import csv
import numpy as np

SEQUENCE_START = -1000
SEQUENCE_STOP = -2000
NO_DATA = -3000
NUM_FEATURES = 30
NUM_DRIVERS = 2


def outer_join(alist, blist):
    result = []
    for a in alist:
        for b in blist:
            result.append((a, b))
    return result


def load_data(directory):
    data = dict()

    FILES_AND_PREFIXES = [('acc.csv', 'acc'), #('brake.csv', 'brk'),
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

for fn in 'james,dan0,dan1'.split(','):
    data_james = load_data('data/' + fn)
    print 'loaded james data. shape ', data_james.shape
    assert(data_james.shape[1] == NUM_FEATURES)

    james_missing_count = 0
    for datum in data_james:
        missing = False
        for component in datum:
            if component == -3000:
                missing = True
        if missing:
            james_missing_count += 1

    print 'missed {0} of {2}\' packets. {1}%'.\
        format(james_missing_count, 100.*james_missing_count/data_james.shape[0], fn)
