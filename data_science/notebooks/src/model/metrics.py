from functools import partial
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import cross_val_score
from sklearn.metrics import make_scorer, mean_absolute_error, log_loss, accuracy_score

# from sklearn.externals.joblib import Parallel, delayed
from dask import compute, delayed

np.random.seed(42)


def regression_accuracy(y, y_pred, **kwargs):  # pylint: disable=W0613
    try:
        correct_preds = ((y >= 0) & (y_pred >= 0)) | ((y <= 0) & (y_pred <= 0))
    except ValueError:
        reset_y = y.reset_index(drop=True)
        reset_y_pred = y_pred.reset_index(drop=True)
        correct_preds = ((reset_y >= 0) & (reset_y_pred >= 0)) | (
            (reset_y <= 0) & (reset_y_pred <= 0)
        )

    return np.mean(correct_preds.astype(int))


def measure_regressor(estimator, data, accuracy=True, **cv_kwargs):
    # Data assumes we've used train_test_split outside of the function to guarantee
    # consistent data splits
    X_train, X_test, y_train, y_test = data
    estimator.fit(X_train, y_train)
    y_pred = estimator.predict(X_test)

    if accuracy:
        cv_accuracy = cross_val_score(
            estimator,
            X_train,
            y_train,
            scoring=make_scorer(regression_accuracy),
            **cv_kwargs,
        )
        test_accuracy = regression_accuracy(y_test, y_pred)
    else:
        cv_accuracy = 0
        test_accuracy = 0

    return (
        cv_accuracy,
        cross_val_score(
            estimator, X_train, y_train, scoring="neg_mean_absolute_error", **cv_kwargs
        )
        * -1,
        test_accuracy,
        mean_absolute_error(y_test, y_pred),
    )


def measure_classifier(estimator, data, **cv_kwargs):
    # Data assumes we've used train_test_split outside of the function to guarantee
    # consistent data splits
    X_train, X_test, y_train, y_test = data
    estimator.fit(X_train, y_train)
    y_pred = estimator.predict(X_test)

    try:
        cv_error_score = cross_val_score(
            estimator, X_train, y_train, scoring="neg_log_loss", **cv_kwargs
        )
        test_error_score = log_loss(y_test, y_pred)
    except AttributeError:
        cv_error_score, test_error_score = 0, 0

    return (
        cross_val_score(estimator, X_train, y_train, scoring="accuracy", **cv_kwargs),
        cv_error_score,
        accuracy_score(y_test, y_pred),
        test_error_score,
    )


def measure_estimators(
    estimators,
    data,
    model_type="regression",
    accuracy=True,
    cv=5,
    n_jobs=-1,
    **cv_kwargs,
):
    if model_type not in ("regression", "classification"):
        raise Exception(
            f'model_type must be "regression" or "classification", but {model_type} was given.'
        )

    estimator_names = []
    mean_cv_accuracies = []
    test_accuracies = []
    mean_cv_errors = []
    test_errors = []
    std_cv_accuracies = []
    std_cv_errors = []

    for estimator_name, estimator, est_kwargs in estimators:
        print(f"Training {estimator_name}")

        if model_type == "regression":
            cv_accuracies, cv_errors, test_accuracy, test_error = measure_regressor(
                estimator, data, accuracy=accuracy, cv=cv, n_jobs=n_jobs, **cv_kwargs
            )
        else:
            cv_accuracies, cv_errors, test_accuracy, test_error = measure_classifier(
                estimator, data, cv=cv, n_jobs=n_jobs, **cv_kwargs, **est_kwargs
            )

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

        print(f"{estimator_name} done")

    score_types = ["cv"] * len(estimator_names) + ["test"] * len(estimator_names)

    return pd.DataFrame(
        {
            "model": estimator_names * 2,
            "accuracy": mean_cv_accuracies + test_accuracies,
            "error": mean_cv_errors + test_errors,
            "std_accuracy": std_cv_accuracies + [np.nan] * len(test_accuracies),
            "std_error": std_cv_errors + [np.nan] * len(test_errors),
            "score_type": score_types,
        }
    )


def _estimator_score(year, data, estimator_params):
    X_train, X_test, y_train, y_test = data
    estimator_name, root_estimator, estimator_kwargs = estimator_params
    estimator = clone(root_estimator)

    print(f"\tGetting scores for {estimator_name}")

    estimator.fit(X_train, y_train, **estimator_kwargs)

    y_pred = estimator.predict(X_test)

    if isinstance(y_pred, np.ndarray):
        y_pred = y_pred.reshape((-1,))

    return {
        "year": year,
        "model": estimator_name,
        "error": mean_absolute_error(y_test, y_pred),
        "accuracy": regression_accuracy(y_test, y_pred),
    }


def _yearly_performance_score(estimators, features, labels, data_frame, year):
    print(f"Getting scores for {year}")

    X_train = features[features["year"] < year]
    X_test = features[features["year"] == year]

    y_train = labels.loc[X_train.index]
    y_test = labels.loc[X_test.index]

    if not data_frame:
        X_train = X_train.values
        X_test = X_test.values

        y_train = y_train.values
        y_test = y_test.values

    estimator_score = partial(
        _estimator_score, year, (X_train, X_test, y_train, y_test)
    )

    scores = [estimator_score(estimator) for estimator in estimators]

    return scores


def yearly_performance_scores(
    estimators, features, labels, parallel=True, data_frame=False
):
    yearly_performance_score = partial(
        _yearly_performance_score, estimators, features, labels, data_frame
    )

    if parallel:
        scores = [delayed(yearly_performance_score)(year) for year in range(2011, 2017)]
        results = compute(scores, scheduler="processes")
    else:
        results = [yearly_performance_score(year) for year in range(2011, 2017)]

    return pd.DataFrame(list(np.array(results).flatten()))
