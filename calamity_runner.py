import sys
import subprocess

def main():
    subprocess.run([sys.executable, '-m', 'calamity_calendar'] + sys.argv[1:])