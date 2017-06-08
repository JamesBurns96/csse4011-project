import csv
import numpy as np

from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split, GridSearchCV


class DriverPredictor(object):
    def __init__(self):
        self.clf = None

    def train(self):
        all_x = []
        all_y = []
        for ln in open('processed/all.csv', 'r'):
            s = ln.split(',')
            r = [float(x) for x in s]
            all_x.append(r[:-1])
            all_y.append(r[-1])

        assert(len(all_x) == len(all_y))
        assert(len(all_x) > 0)

        X_test, X_train, y_test, y_train = train_test_split(all_x, all_y, test_size=0.8)

        self.clf = SVC(kernel='rbf', C=0.1)
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

        true_positives = float(true_positives) / (true_positives + false_positives)
        true_negatives = float(true_negatives) / (true_negatives + false_negatives)
        bad_positives = float(false_positives) / (true_positives + false_positives)
        bad_negatives = float(false_negatives) / (true_negatives + false_negatives)

        print 'true positives: ', true_positives
        print 'true negatives: ', true_negatives
        print 'bad positives: ', bad_positives
        print 'bad negatives: ', bad_negatives

    def predict(self, X):
        if self.clf is None:
            raise ValueError

        return self.clf.predict(X)


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
    pd = DriverPredictor()
    pd.train()
