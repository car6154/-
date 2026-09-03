import sys
import json
import urllib.parse
from scraper import HeydealerScraper

def test():
    cookie_str = "_gid=GA1.2.755115521.1788338631; ga_dsi=761016155b2a4d6ba8de945ab8a90e40; csrftoken=HhrPIhfQKdy7Jpx3BlRFIIZZ9EjtHDpK; sessionid=dco8yvy7elj0z2vwguf637ydj4bh0a3p; _gat_gtag_UA_65689834_14=1; _ga=GA1.1.2144284551.1785809103; _ga_D0D36Y0VSC=GS2.1.s1788421576$o48$g1$t1788428583$j2$l0$h0"
    try:
        session = HeydealerScraper.build_session(cookie_str)
        # GET /v2/dealers/web/price/cars/?page=1&model=4BMGPp&grade=67dANp&year=2025&year=2026&year=2027&max_mileage=30000&period=c&order=recent
        url = "https://api.heydealer.com/v2/dealers/web/price/cars/?page=1&model=4BMGPp&grade=67dANp&year=2025&year=2026&year=2027&max_mileage=30000&period=c&order=recent"
        
        HeydealerScraper._sync_csrf_header(session)
        resp = session.get(url, timeout=10)
        HeydealerScraper._sync_csrf_header(session)
        
        with open("scratch_market_price.json", "w", encoding="utf-8") as f:
            f.write(resp.text)
            
        print(f"Status: {resp.status_code}")
        print("Done")
    except Exception as e:
        print(f"Error: {e}")

test()
