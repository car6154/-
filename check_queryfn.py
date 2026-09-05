import requests, re

resp = requests.get('https://dealer.heydealer.com/assets/index-Dn0N5zya.js')
text = resp.text

idx = text.find('queryFn:b$e(e)')
snippet = text[max(0, idx-500):min(len(text), idx+1000)]
print("Snippet around queryFn:b$e(e):")
print(snippet)

# What is b$e(e)?
# Notice: b$e = e => async () => (await ft.get(`/cars/${e}/`)).data
# When called as b$e(e), it returns async () => (await ft.get(`/cars/${e}/`)).data !
# So ft.get('/cars/' + e + '/') is called!
# And ft has baseURL: https://api.heydealer.com/v2/dealers/web/
# So the full URL is: https://api.heydealer.com/v2/dealers/web/cars/{e}/
