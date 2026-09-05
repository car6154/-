import os
import re
from dotenv import load_dotenv
from scraper import HeydealerScraper

load_dotenv()
cookie = os.environ.get('HEYDEALER_COOKIE')
if not cookie:
    print("No cookie found")
else:
    s = HeydealerScraper.build_session(cookie)
    res = s.get('https://dealer.heydealer.com/cars/n1mpPLen/')
    
    print('encar.com in text:', 'encar.com' in res.text)
    
    match = re.search(r'https://www.encar.com/dc/dc_carsearchlist[^\'"]+', res.text)
    if match:
        print("MATCH:", match.group(0))
    else:
        print("NO MATCH")
