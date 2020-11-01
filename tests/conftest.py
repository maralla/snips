import sys
import pytest
import os

DIR = os.path.abspath(os.path.dirname(__name__))

# Make the pythonx directory importable
sys.path.append(os.path.join(DIR, 'pythonx'))


@pytest.fixture(scope='session')
def current_dir():
    return os.path.join(DIR, 'tests')
