import os, re, glob

print("Scanning /jayproject_original for Encar code...")
for path in glob.glob('/jayproject_original/**/*.py', recursive=True):
    with open(path) as f:
        code = f.read()
    if 'encar' in code.lower():
        print(f"File: {path}")
        for match in re.findall(r'https?://[a-zA-Z0-9\.\_\/\?\=\&\%\-]+encar[a-zA-Z0-9\.\_\/\?\=\&\%\-]+', code):
            print("  Endpoint:", match)
