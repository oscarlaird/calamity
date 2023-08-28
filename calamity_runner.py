import sys
import subprocess

if __name__=="__main__":
    subprocess.run([sys.executable, '-m', 'calamity'] + sys.argv[1:])