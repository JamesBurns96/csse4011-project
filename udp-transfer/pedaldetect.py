import csv
import numpy as np

from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split, GridSearchCV

NO_DATA = None

def load_data(directory):
    data = dict()

    def outer_join(alist, blist):
        result = []
        for a in alist:
            for b in blist:
                result.append((a, b))
        return result

    FILES_AND_PREFIXES = [('steer.csv', 'acc'), ('button.csv', 'bt')]

    for (filename, prefix) in FILES_AND_PREFIXES:
        with open(directory + '/' + filename, 'r') as fl:
            for ln in csv.DictReader(fl):
                ts = float(ln['timeStamp']) + float(ln['sampleNumber']) / 20.
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
            assert (last_ts < ts)
        raw_line = []
        dat = data[ts]

        for (p, s) in outer_join([p[1] for p in FILES_AND_PREFIXES], SENSOR_SUFFIXES):
            raw_line.append(dat.get(p + '-' + s, NO_DATA))

        data_raw.append(raw_line)

    return np.asarray(data_raw)


class PedalDetector(object):
    def __init__(self):
        self.clf = None

    def train(self):
        data = load_data('pedaldetect-data/clutchStationary')

        valid_indices = []
        missing_count = 0
        for (datum, index) in zip(data, range(len(data))):
            missing = False
            for component in datum:
                if component == NO_DATA:
                    missing = True
            if missing:
                missing_count += 1
            else:
                valid_indices.append(index)

        print 'missed {0} packets. ({1}%)'. \
            format(missing_count, 100. * missing_count / data.shape[0])

        valid_data = [data[i] for i in valid_indices]

        X = [[x[3], x[4], x[5]] for x in valid_data]
        y = [x[9] / 2. for x in valid_data]

        X_test, X_train, y_test, y_train = train_test_split(X, y, test_size=0.9)


        with open('interpreted.csv', 'w') as f:
            f.writelines([','.join([str(x[0]), str(x[1]), str(x[2]), str(y)])+'\n' for (x, y) in zip(X, y)])


        self.clf = SVC(kernel='linear', C=0.01)
        self.clf.fit(X_train, y_train)

        def compute_accuracy(data, target):
            y = self.clf.predict(data)
            score = accuracy_score(target, y)
            return score

        print "- Training set", compute_accuracy(X_train, y_train)
        print "- Testing set", compute_accuracy(X_test, y_test)

        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0
        for (r, p) in zip(y_test, self.predict(X_test)):
            if (r, p) == (0, 0):
                true_negatives += 1
            elif (r, p) == (1, 1):
                true_positives += 1
            elif (r, p) == (0, 1):
                false_positives += 1
            elif (r, p) == (1, 0):
                false_negatives += 1

        # bad_positives = float(false_positives) / (true_positives + false_positives)
        bad_negatives = float(false_negatives) / (true_negatives + false_negatives)

        # print 'bad positives: ', bad_positives
        print 'bad negatives: ', bad_negatives

    def predict(self, X):
        if self.clf is None:
            raise ValueError

        pred = []
        for x in X:
            if np.sum(x) > 50:
                pred.append(1)
            elif np.sum(x) < -50:
                pred.append(-1)
            else:
                pred.append(0)

        return pred
        # return np.sign(X) * (np.abs(np.sum(X)) > 100)
        # return self.clf.predict(X)
        # return X


def predict_from_threshold(X, t_low, t_high):
    pred = []
    for x in X:
        if np.sum(x) > t_high:
            pred.append(1)
        elif np.sum(x) < t_low:
            pred.append(-1)
        else:
            pred.append(0)

    return pred


if __name__ == '__main__':
    pd = PedalDetector()
    pd.train()
