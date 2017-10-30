"""Wrapper for loading data, training a model (possibly on specified folds),
and writing out predictions.
"""

import os, sys, yaml, pickle
import pandas as pd
import numpy as np
from sklearn import svm
from sklearn.ensemble import BaggingClassifier
from utils import datetime_for_filename
from estimators import NN, XGBoost, TestClassifier

# The model names and their definitions.
model_dict = {'nn':NN, 
              'xgb':(lambda **kwargs: XGBoost(stratify=False, **kwargs)),
              'xgbStratified':(lambda **kwargs: XGBoost(stratify=True, **kwargs)),
              'svm':(lambda **kwargs: svm.SVC(probability=True, **kwargs))}

tuned_parameters = {'xgb':{'min_child_weight': [3, 5, 7], 'max_depth': [5,  6,  7], 'gamma': [1.5, 2, 2.5] },
                    'svm':{'gamma': [1e1, 1e0, 1e-1, 1e-2, 1e-3, 1e-4, 1e-5], 'C': [00.1, 0.1, 1, 10, 100, 1000]}}


def main(config_file, model_name, fold):
    print('Config file: ' + config_file)
    print('Model: ' + model_name)
    print('Fold for which predictions will be added: ' + str(fold))

    with open(config_file, 'r') as f:
        config = yaml.load(f)
    with open(config['hyperparams_file'], 'r') as f:
        hyperparams = yaml.load(f)
        
    # Define model.
    print('Define model...')
    model = model_dict[model_name](**hyperparams[model_name])
    model_col_name = 'model_' + model_name
 
    # Load data.
    print('Loading data...')
    train_df = pd.read_csv('../generated-files/train.csv')
    test_df = pd.read_csv('../generated-files/test.csv')

    if fit_hyperparams:
        print('Finding hyperparameters...')
        clf = GridSearchCV(model, tuned_parameters, cv=5,
                    scoring=hyperparams[category_in_hyperparams_file]['scoring'])
        clf.fit(train_features, train_labels)
        print('Found best hyperparams:')
        print(clf.best_params_)

        # Put grid search best params in hyperparams dict.
        for key in clf.best_params_:
            hyperparams[category_in_hyperparams_file][key] = clf.best_params_[key]
        # Save hyperparams.
        with open(config['hyperparams_file'], 'w') as f:
            yaml.dump(hyperparams, f)
        print('Wrote best params to ' + str(config['hyperparams_file']))
    elif fold != None:
        print('Fitting...')
        model.fit(X=train_df.loc[train_df['fold'] != fold, [x for x in train_df.columns if x != 'target']], 
                  y=train_df.loc[train_df['fold'] != fold, 'target'])
        # Add predictions for fold.
        print("Predicting...")
        if not model_col_name in train_df:
            train_df = train_df.assign(model_col_name=np.nan)
        train_df.loc[train_df['fold'] == fold, model_col_name] = model.predict_proba(train_df.loc[train_df['fold'] == fold, :])[:,1]
        train_df.to_csv(config['train_set'], index=None)
        print('Added predictions for model ' + model_name + ', fold ' + str(fold) + ' to column ' + model_col_name + ' of ../generated-files/train.csv.')
    else:
        print('Fitting...')
        model.fit(X=train_df.loc[:, [x for x in train_df.columns if x != 'target']], 
                  y=train_df.loc[:, 'target'])
        # Add predictions for whole test set to test CSV.
        print("Predicting...")
        test_df.assign(model_col_name=model.predict_proba(test_df)[:,1])
        test_set.to_csv('../generated-files/test.csv', index=None)
        print('Added predictions for model ' + model_name + ' to column ' + model_col_name + ' of ../generated-files/test.csv.')

if __name__ == "__main__":
    if len(sys.argv) == 4:
        main(sys.argv[1], model_name=sys.argv[2], fold=int(sys.argv[3]))
    elif len(sys.argv) == 3:
        main(sys.argv[1], model_name=sys.argv[2], fold=None)
    else:
        print("First argument: config file; second argument: model name; third argument (optional): fold number.")
