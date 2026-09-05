import os, requests
from dotenv import load_dotenv
load_dotenv()

cookie = os.getenv('HEYDEALER_COOKIE')
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Cookie': cookie,
    'App-Os': 'web',
    'App-Type': 'dealer',
    'App-Version': '1.0.0',
    'Referer': 'https://dealer.heydealer.com/'
}

# In index-Dn0N5zya.js:
# uze, dze, fze: let's check what App-Os, App-Type, App-Version are!
# And let's test fetching https://api.heydealer.com/v2/dealers/web/cars/yeXf4nN/
# Wait, let's test different headers or check what car_id "yeXf4nN" is!
resp = requests.get('https://api.heydealer.com/v2/dealers/web/cars/yeXf4nN/', headers=headers)
print("With headers:", resp.status_code)
if resp.status_code != 200:
    print(resp.text[:300])
