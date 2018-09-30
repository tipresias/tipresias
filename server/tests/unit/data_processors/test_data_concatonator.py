import os
import sys
from unittest import TestCase
import pandas as pd
import numpy as np
from faker import Faker

PROJECT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../../'))

if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from server.data_processors import DataConcatenator

FAKE = Faker()


class TestDataConcatenator(TestCase):
    def setUp(self):
        self.concatenator = DataConcatenator(drop_cols=[])

    def test_transform(self):
        jobs = [FAKE.job() for _ in range(10)]
        phone_numbers = [FAKE.phone_number() for _ in range(10)]

        data_frame_1 = pd.DataFrame({
            'name': [FAKE.name() for _ in range(10)],
            'job': jobs,
            'phone_number': phone_numbers,
            'address': [FAKE.address() for _ in range(10)]
        })
        data_frame_2 = pd.DataFrame({
            'employee': [FAKE.name() for _ in range(10)],
            'job': jobs,
            'phone_number': phone_numbers
        })
        data_frame_3 = pd.DataFrame({
            'company': [FAKE.company() for _ in range(10)],
            'employee': [FAKE.name() for _ in range(10)],
            'catch_phrase': [FAKE.catch_phrase() for _ in range(10)]
        })

        with self.subTest(data_frames=[data_frame_1, data_frame_2]):
            data_frame = (self.concatenator
                          .transform([data_frame_1, data_frame_2]))

            self.assertEqual((10, 5), data_frame.shape)
            self.assertFalse(data_frame.isna().any().any())

        with self.subTest(data_frames=[data_frame_1, data_frame_3]):
            with self.assertRaises(ValueError):
                self.concatenator.transform([data_frame_1, data_frame_3])
