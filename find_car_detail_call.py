import re, requests

resp = requests.get('https://dealer.heydealer.com/assets/index-Dn0N5zya.js')
text = resp.text

# find where /cars/${ is used
for m in re.finditer(r'(/cars/\$\{[^}]+\}[^`"\']*)', text):
    snippet = text[max(0, m.start()-100):min(len(text), m.end()+100)]
    print("---")
    print(snippet)
