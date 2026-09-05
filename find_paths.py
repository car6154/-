import re, requests

resp = requests.get('https://dealer.heydealer.com/assets/index-Dn0N5zya.js')
text = resp.text

# Look for patterns like .get(`/cars/ or .get("/cars/ or .get(`/ or paths relative to baseURL
calls = set(re.findall(r'\.(?:get|post)\([`"\']([^`"\']*(?:car|auction|detail|bid)[^`"\']*)[`"\']', text))
print("Found calls:")
for c in sorted(calls):
    print(" ", c)

# Also let's search for "cars/"
cars_refs = set(re.findall(r'[`"\']([^`"\']*cars/[^`"\']*)[`"\']', text))
print("Found cars/ refs:")
for c in sorted(cars_refs):
    print(" ", c)
