import subprocess

with open('output.txt', 'w') as f:
    p1 = subprocess.run('git log index.html', shell=True, stdout=f, text=True)
    
    diff = subprocess.run('git diff f432123 h43432 index.html', shell=True, stdout=f, text=True)