from bs4 import BeautifulSoup
with open('encar_test2.html', 'r', encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'html.parser')

print("--- JS fnStats calls ---")
import re
# look for this.fnStats(key, value) or similar calls or data blocks
for line in html.split('\n'):
    if 'frontFender' in line or 'hood' in line or '002' in line or '003' in line:
        print(line.strip())

print("\n--- Table rows with 후드 / 휀더 ---")
for row in soup.select('table tr'):
    text = row.get_text(strip=True)
    if '후드' in text or '본넷' in text or '휀더' in text:
        print(text)
        
print("\n--- Any elements with class 'X', 'W', 'C', etc? ---")
# Encar typically represents damage as <span class="state X">교환</span> etc.
for tag in soup.select('.inspe'):
    print(tag.get_text()[:200])
