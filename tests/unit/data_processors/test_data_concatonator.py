import os
import sys
from unittest import TestCase
import pandas as pd
import numpy as np
from faker import Faker

project_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../'))

if project_path not in sys.path:
    sys.path.append(project_path)

from app.data_processors import DataConcatenator

np.random.seed(42)

fake = Faker()


class TestDataConcatenator(TestCase):
    def setUp(self):
        self.concatenator = DataConcatenator(drop_cols=[])

    def test_transform(self):
        jobs = [fake.job() for _ in range(10)]
        phone_numbers = [fake.phone_number() for _ in range(10)]

        data_frame_1 = pd.DataFrame({
            'name': [fake.name() for _ in range(10)],
            'job': jobs,
            'phone_number': phone_numbers,
            'address': [fake.address() for _ in range(10)]
        })
        data_frame_2 = pd.DataFrame({
            'employee': [fake.name() for _ in range(10)],
            'job': jobs,
            'phone_number': phone_numbers
        })
        data_frame_3 = pd.DataFrame({
            'company': [fake.company() for _ in range(10)],
            'employee': [fake.name() for _ in range(10)],
            'catch_phrase': [fake.catch_phrase() for _ in range(10)]
        })

        with self.subTest(data_frames=[data_frame_1, data_frame_2]):
            df = self.concatenator.transform([data_frame_1, data_frame_2])

            self.assertEqual((10, 5), df.shape)
            self.assertFalse(df.isna().any().any())

        with self.subTest(data_frames=[data_frame_1, data_frame_3]):
            with self.assertRaises(ValueError):
                self.concatenator.transform([data_frame_1, data_frame_3])
