# pylint: disable=missing-docstring

import os
import sys
import re


def test_lambda_version_compatibility():
    current_python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    with os.popen("npx serverless print") as serverless_config_output:
        serverless_config = serverless_config_output.read()

    if re.search(r"^Error", serverless_config) is not None:
        raise Exception(serverless_config)

    runtime_matches = re.search(r"runtime: (python\d+\.\d+)", serverless_config)
    lambda_python_version = runtime_matches[1]

    assert f"python{current_python_version}" in lambda_python_version
