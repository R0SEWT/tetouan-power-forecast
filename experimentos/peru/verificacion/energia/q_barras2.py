import sys
import pandas as pd
sys.argv = sys.argv
from importlib import util
spec = util.spec_from_file_location("qb", sys.argv[1]); 
