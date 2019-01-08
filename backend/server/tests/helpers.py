from typing import Union
import pandas as pd
import numpy as np


def regression_accuracy(
    y: Union[pd.DataFrame, np.ndarray], y_pred: Union[pd.DataFrame, np.ndarray]
) -> np.ndarray:
    try:
        correct_preds = ((y >= 0) & (y_pred > 0)) | ((y <= 0) & (y_pred < 0))
    except ValueError:
        reset_y = y.reset_index(drop=True)
        reset_y_pred = y_pred.reset_index(drop=True)
        correct_preds = ((reset_y >= 0) & (reset_y_pred > 0)) | (
            (reset_y <= 0) & (reset_y_pred < 0)
        )

    return np.mean(correct_preds.astype(int))
