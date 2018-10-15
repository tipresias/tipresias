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


def measure_regressor(estimator, data, cv=5, n_jobs=-1):
    # Data assumes we've used train_test_split outside of the function to guarantee
    # consistent data splits
    X_train, X_test, y_train, y_test = data
    estimator.fit(X_train, y_train)
    y_pred = estimator.predict(X_test)

    return (cross_val_score(estimator,
                            X_train,
                            y_train,
                            scoring=make_scorer(regression_accuracy),
                            cv=cv,
                            n_jobs=n_jobs),
            cross_val_score(estimator,
                            X_train,
                            y_train,
                            scoring='neg_mean_absolute_error',
                            cv=cv,
                            n_jobs=n_jobs) * -1,
            regression_accuracy(y_test, y_pred),
            mean_absolute_error(y_test, y_pred))


def measure_classifier(estimator, data, cv=5):
    # Data assumes we've used train_test_split outside of the function to guarantee
    # consistent data splits
    X_train, X_test, y_train, y_test = data
    estimator.fit(X_train, y_train)
    y_pred = estimator.predict(X_test)

    try:
        cv_error_score = cross_val_score(
            estimator, X_train, y_train, scoring='neg_log_loss', cv=cv)
        test_error_score = log_loss(y_test, y_pred)
    except AttributeError:
        cv_error_score, test_error_score = 0, 0

    return (cross_val_score(estimator, X_train, y_train, scoring='accuracy', cv=cv),
            cv_error_score,
            accuracy_score(y_test, y_pred),
            test_error_score)


def measure_estimators(estimators, data, model_type='regression', cv=5, n_jobs=-1):
    if model_type not in ('regression', 'classification'):
        raise Exception(
            f'model_type must be "regression" or "classification", but {model_type} was given.')

    # Use standard scaler, because many of these estimators are sensitive to scale of different features
    scaler = StandardScaler()

    estimator_names = []
    mean_cv_accuracies = []
    test_accuracies = []
    mean_cv_errors = []
    test_errors = []
    std_cv_accuracies = []
    std_cv_errors = []

    for estimator in estimators:
        pipeline = make_pipeline(scaler, estimator)

        estimator_name = type(estimator).__name__
        print(f'Training {estimator_name}')

        if model_type == 'regression':
            cv_accuracies, cv_errors, test_accuracy, test_error = measure_regressor(
                pipeline, data, cv=cv, n_jobs=n_jobs)
        else:
            cv_accuracies, cv_errors, test_accuracy, test_error = measure_classifier(
                pipeline, data, cv=cv, n_jobs=n_jobs)

        mean_cv_accuracy = np.mean(cv_accuracies)
        mean_cv_error = np.mean(cv_errors)
        std_cv_accuracy = np.std(cv_accuracies)
        std_cv_error = np.std(cv_errors)

        estimator_names.append(estimator_name)
        mean_cv_accuracies.append(mean_cv_accuracy)
        std_cv_accuracies.append(std_cv_accuracy)
        test_accuracies.append(test_accuracy)
        mean_cv_errors.append(mean_cv_error)
        std_cv_errors.append(std_cv_error)
        test_errors.append(test_error)

    score_types = ['cv'] * len(estimator_names) + \
        ['test'] * len(estimator_names)

    return pd.DataFrame({'estimator': estimator_names * 2,
                         'accuracy': mean_cv_accuracies + test_accuracies,
                         'error': mean_cv_errors + test_errors,
                         'std_accuracy': std_cv_accuracies + [np.nan] * len(test_accuracies),
                         'std_error': std_cv_errors + [np.nan] * len(test_errors),
                         'score_type': score_types})
