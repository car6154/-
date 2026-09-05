import re, requests

resp = requests.get('https://dealer.heydealer.com/assets/index-Dn0N5zya.js')
text = resp.text

idx = text.find('apiBaseURL:')
snippet = text[max(0, idx-500):min(len(text), idx+2000)]
print(snippet)

# find where XVe({apiBaseURL: is called
m = re.findall(r'XVe\(\{apiBaseURL:[^}]+\}\)', text)
print("XVe calls:", m)

# find "apiBaseURL" definitions
m2 = re.findall(r'apiBaseURL\s*:\s*[^,}]+', text)
print("apiBaseURL values:", m2)
