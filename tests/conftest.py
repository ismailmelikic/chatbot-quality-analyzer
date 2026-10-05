import os
import sys

# Testler proje kokundeki modulleri dogrudan import eder
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
os.chdir(KOK)
