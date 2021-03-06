# pylint: disable=missing-docstring

import os
import sys


def test_lambda_version_compatibility():
    current_python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    lambda_python_version = os.popen("npx serverless print | grep runtime:").read()

    assert f"python{current_python_version}" in lambda_python_version
