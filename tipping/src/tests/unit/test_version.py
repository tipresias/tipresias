# pylint: disable=missing-docstring

import os
import sys


def test_lambda_version_compatibility():
    current_python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    with os.popen("npx serverless print | grep runtime:") as version_output:
        lambda_python_version = version_output.read()

    assert f"python{current_python_version}" in lambda_python_version
