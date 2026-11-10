import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

for p in (parent_dir, current_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app
