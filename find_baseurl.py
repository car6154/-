import re, requests

resp = requests.get('https://dealer.heydealer.com/assets/index-Dn0N5zya.js')
text = resp.text

idx = text.find('apiBaseURL')
snippet = text[max(0, idx-200):min(len(text), idx+1000)]
print("Around apiBaseURL:")
print(snippet)
