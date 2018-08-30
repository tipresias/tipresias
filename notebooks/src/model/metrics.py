import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.metrics import make_scorer, mean_absolute_error, log_loss, accuracy_score

np.random.seed(42)

def regression_accuracy(y, y_pred, **kwargs):
    correct_preds = ((y >= 0) & (y_pred >= 0)) | ((y <= 0) & (y_pred <= 0))
    return np.mean(correct_preds.astype(int))

def measure_regressor(estimator, data):
    # Data assumes we've used train_test_split outside of the function to guarantee
    # consistent data splits
    X_train, X_test, y_train, y_test = data
    estimator.fit(X_train, y_train)
    y_pred = estimator.predict(X_test)

    return (np.mean(cross_val_score(estimator, X_train, y_train, scoring=make_scorer(regression_accuracy), cv=5)),
            np.mean(cross_val_score(estimator, X_train, y_train, scoring='neg_mean_absolute_error', cv=5)),
            regression_accuracy(y_test, y_pred),
            mean_absolute_error(y_test, y_pred))

def measure_classifier(estimator, data):
    # Data assumes we've used train_test_split outside of the function to guarantee
    # consistent data splits
    X_train, X_test, y_train, y_test = data
    estimator.fit(X_train, y_train)
    y_pred = estimator.predict(X_test)

    try:
        cv_error_score = np.mean(cross_val_score(estimator, X_train, y_train, scoring='neg_log_loss', cv=5))
        test_error_score = log_loss(y_test, y_pred)
    except AttributeError:
        cv_error_score, test_error_score = 'NA', 'NA'

    return (np.mean(cross_val_score(estimator, X_train, y_train, scoring='accuracy', cv=5)),
            cv_error_score,
            accuracy_score(y_test, y_pred),
            test_error_score)

def measure_estimators(estimators, data, model_type='regression'):
    if model_type not in ('regression', 'classification'):
        raise Exception(f'model_type must be "regression" or "classification", but {model_type} was given.')

    # Use standard scaler, because many of these estimators are sensitive to scale of different features
    scaler = StandardScaler()

    for estimator in estimators:
        pipeline = make_pipeline(scaler, estimator)

        cv_accuracy, cv_error, test_accuracy, test_error = measure_regressor(pipeline, data) if model_type == 'regression' else measure_classifier(pipeline, data)

        print(f'\n\n{type(estimator).__name__}')
        print('Mean CV accuracy:', cv_accuracy)
        print('Test accuracy:', test_accuracy)


        print('\nMean CV negative error score:', cv_error)
        print('Test error score:', test_error)
