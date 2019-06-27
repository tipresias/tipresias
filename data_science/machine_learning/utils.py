from typing import List
from functools import reduce

from machine_learning.types import DataFrameTransformer


class DataTransformerMixin:
    """Mixin class for estimator and data classes that use data transformers"""

    @property
    def data_transformers(self) -> List[DataFrameTransformer]:
        """List of data transformer functions"""

        raise NotImplementedError("The data_transformers property must be defined.")

    @property
    def _compose_transformers(self) -> DataFrameTransformer:
        """Combine data transformation functions via composition"""

        # Need to reverse the transformation steps, because composition makes the output
        # of each new function the argument for the previous
        return reduce(
            self.__compose_two_transformers,
            reversed(self.data_transformers),
            lambda x: x,
        )

    @staticmethod
    def __compose_two_transformers(
        composed_func: DataFrameTransformer, func_element: DataFrameTransformer
    ) -> DataFrameTransformer:
        return lambda x: composed_func(func_element(x))
