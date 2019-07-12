import os
import sys

PATH = os.path.abspath(os.path.join(os.path.dirname(__file__)))

if PATH not in sys.path:
    sys.path.append(PATH)
