import re, requests

resp = requests.get('https://dealer.heydealer.com/assets/index-Dn0N5zya.js')
text = resp.text

idx = text.find('apiBaseURL:Dv')
snippet = text[max(0, idx-300):min(len(text), idx+200)]
print("Around Dv:")
print(snippet)

# find Dv definition
m = re.findall(r'(?:const|let|var)\s+Dv\s*=\s*([^;,]+)', text)
print("Dv definitions:", m)
