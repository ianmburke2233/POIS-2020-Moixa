import pandas as pd
import time
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, AdaBoostClassifier
from sklearn import metrics
from sklearn.model_selection import cross_validate, train_test_split

fname = 'Data/multiclass.csv'
dev_fname = 'Data/multiclassDev.csv'
outname = '2020-10-30 ADA (Full Pop, Combo)'
# model = RandomForestClassifier(n_estimators=200, max_depth=50, min_samples_leaf=2, min_samples_split=2)
# model = GradientBoostingClassifier()
model = AdaBoostClassifier()
population = 1  # 1 - Full Population, 2 - Protected Group Only, 3 - Non-Protected Group Only
target = 2  # 1 - Hybrid Target, 2 - High Performer, 3 - Retained, 4 - Real High Performer, 5 - HP & Retained
weighted = 1
print_results = 1

df = pd.read_csv(fname)

if population == 2:
    df = df[df['Protected_Group'] == 1]
if population == 3:
    df = df[df['Protected_Group'] == 0]

dev_df = pd.read_csv(dev_fname)

ids = dev_df['UNIQUE_ID']

features = list(df.columns)[10:-3]
if target == 4:
    df = df[df['hasPerf'] == 1]
features.remove('hasPerf')

if target == 1:
    target_np = df['target'].to_numpy()
if target == 2 or target == 4:
    target_np = df['Filled_High_Performer'].to_numpy()
if target == 3:
    target_np = df['Retained'].to_numpy()
if target == 5:
    df['combo'] = ((df['Retained'] + df['Filled_High_Performer'])/2.0).apply(np.floor)
    target_np = df['Retained'].to_numpy()


if weighted == 1:
    df['weights'] = df.hasPerf * 9 + 1
    features.append('weights')

data_np = df[features].to_numpy()

print('--ML Model Output--', '\n')

# Test/Train split
data_train, data_test, target_train, target_test = train_test_split(data_np, target_np, test_size=0.35)
weights_train = data_train[:, features.index('weights')]
data_train = data_train[:, :features.index('weights')]
data_test = data_test[:, :features.index('weights')]
features.remove('weights')
#
scorers = {'Accuracy': 'accuracy'}
#
# SciKit SVM - Cross Val
start_ts = time.time()
clf = model
scores = cross_validate(estimator=clf, X=data_train, y=target_train, scoring=scorers,
                        cv=5, fit_params={'sample_weight': weights_train})

scores_Acc = scores['test_Accuracy']
print("SVM Acc: %0.2f (+/- %0.2f)" % (scores_Acc.mean(), scores_Acc.std() * 2))
# scores_AUC = scores['test_roc_auc']
# print("AUC: %0.2f (+/- %0.2f)" % (scores_AUC.mean(), scores_AUC.std() * 2))
print("CV Runtime:", time.time() - start_ts, '\n')

if weighted == 1:
    clf.fit(data_train, target_train, sample_weight=weights_train)
else:
    clf.fit(data_train, target_train)
pred = clf.predict(data_test)
data_dev = dev_df[features]
dev_pred = clf.predict(data_dev)
dev_pred_prob = clf.predict_proba(data_dev)

print(metrics.confusion_matrix(target_test, pred, normalize='true'))
print(metrics.confusion_matrix(target_test, pred))
#
dev_predicted_class = pd.DataFrame(dev_pred, columns=['Predicted Class'])

if target != 1:
    results = dev_predicted_class.join(pd.DataFrame(dev_pred_prob, columns=['Class 1 Prob', 'Class 2 Prob']))
    results = results.join(ids).sort_values(by='Class 2 Prob')
else:
    results = dev_predicted_class.join(pd.DataFrame(dev_pred_prob, columns=['Class 1 Prob', 'Class 2 Prob',
                                                                            'Class 3 Prob']))
    results = results.join(ids).sort_values(by='Class 3 Prob')


def hire(mid, x):
    if x > mid:
        decision = 1
    else:
        decision = 0
    return decision


if target != 1:
    median = results['Class 2 Prob'].median()
    results['Hire'] = results['Class 2 Prob'].apply(lambda x: hire(median, x))
    selection = results[['UNIQUE_ID', 'Class 2 Prob', 'Hire']]
else:
    median = results['Class 3 Prob'].median()
    results['Hire'] = results['Class 3 Prob'].apply(lambda x: hire(median, x))
    selection = results[['UNIQUE_ID', 'Hire']]

if print_results == 1:
    selection.to_csv('Selections/{}.csv'.format(outname), index=False)
