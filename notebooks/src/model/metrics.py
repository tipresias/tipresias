import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.metrics import make_scorer, mean_absolute_error, log_loss, accuracy_score

np.random.seed(42)

def regression_accuracy(y, y_pred, **kwargs):
    correct_preds = ((y >= 0) & (y_pred >= 0)) | ((y <= 0) & (y_pred <= 0))
    return np.mean(correct_preds.astype(int))

def measure_regressor(estimator, data, cv=5):
    # Data assumes we've used train_test_split outside of the function to guarantee
    # consistent data splits
    X_train, X_test, y_train, y_test = data
    estimator.fit(X_train, y_train)
    y_pred = estimator.predict(X_test)

    return (np.mean(cross_val_score(estimator, X_train, y_train, scoring=make_scorer(regression_accuracy), cv=cv)),
            np.mean(cross_val_score(estimator, X_train, y_train, scoring='neg_mean_absolute_error', cv=cv)) * -1,
            regression_accuracy(y_test, y_pred),
            mean_absolute_error(y_test, y_pred))

def measure_classifier(estimator, data, cv=5):
    # Data assumes we've used train_test_split outside of the function to guarantee
    # consistent data splits
    X_train, X_test, y_train, y_test = data
    estimator.fit(X_train, y_train)
    y_pred = estimator.predict(X_test)

    try:
        cv_error_score = np.mean(cross_val_score(estimator, X_train, y_train, scoring='neg_log_loss', cv=cv))
        test_error_score = log_loss(y_test, y_pred)
    except AttributeError:
        cv_error_score, test_error_score = 'NA', 'NA'

    return (np.mean(cross_val_score(estimator, X_train, y_train, scoring='accuracy', cv=cv)),
            cv_error_score,
            accuracy_score(y_test, y_pred),
            test_error_score)

def measure_estimators(estimators, data, model_type='regression', cv=5):
    if model_type not in ('regression', 'classification'):
        raise Exception(f'model_type must be "regression" or "classification", but {model_type} was given.')

    # Use standard scaler, because many of these estimators are sensitive to scale of different features
    scaler = StandardScaler()

    estimator_names = []
    cv_accuracies = []
    test_accuracies = []
    cv_errors = []
    test_errors = []

    for estimator in estimators:
        pipeline = make_pipeline(scaler, estimator)

        estimator_name = type(estimator).__name__
        if model_type == 'regression':
            cv_accuracy, cv_error, test_accuracy, test_error = measure_regressor(pipeline, data, cv=cv)
        else:
            cv_accuracy, cv_error, test_accuracy, test_error = measure_classifier(pipeline, data, cv=cv)

        print(f'\n\n{estimator_name}')
        print('Mean CV accuracy:', cv_accuracy)
        print('Test accuracy:', test_accuracy)


        print('\nMean CV negative error score:', cv_error)
        print('Test error score:', test_error)

        estimator_names.append(estimator_name)
        cv_accuracies.append(cv_accuracy)
        test_accuracies.append(test_accuracy)
        cv_errors.append(cv_error)
        test_errors.append(test_error)

    score_types = ['cv'] * len(estimator_names) + ['test'] * len(estimator_names)

    return pd.DataFrame({'estimator': estimator_names * 2,
                         'accuracy': cv_accuracies + test_accuracies,
                         'error': cv_errors + test_errors,
                         'score_type': score_types})
