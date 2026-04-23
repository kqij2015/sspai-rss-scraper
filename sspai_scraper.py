import asyncio
from playwright.async_api import async_playwright
import xml.etree.ElementTree as ET
from datetime import datetime
import os

async def scrape_sspai():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://sspai.com/u/sa2syl7a/updates"
        print(f"Loading {url}...")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Error loading page: {e}")
            await browser.close()
            return []
        
        # Scroll down to ensure content is loaded
        print("Scrolling page...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)
        
        # Extract items
        print("Extracting items from page...")
        items = await page.evaluate("""() => {
            const results = [];
            // Try different selectors for sspai updates
            const cards = document.querySelectorAll('.user-update-item, .update-card, article, .article-card');
            
            cards.forEach(card => {
                const titleEl = card.querySelector('.title, h3, .article-title, .nickname, .content');
                const linkEl = card.querySelector('a[href*="/post/"], a[href*="/article/"]');
                const dateEl = card.querySelector('.time, .date, .created-at');
                
                if (titleEl && linkEl) {
                    results.push({
                        title: titleEl.innerText.trim().replace(/\\n/g, ' '),
                        link: linkEl.href,
                        date: dateEl ? dateEl.innerText.trim() : ''
                    });
                }
            });
            
            // Fallback: search for all links that look like posts
            if (results.length === 0) {
                document.querySelectorAll('a').forEach(link => {
                    const href = link.getAttribute('href') || '';
                    if (href.includes('/post/') || href.includes('/article/')) {
                        const title = link.innerText.trim();
                        if (title.length > 5) {
                            results.push({
                                title: title.replace(/\\n/g, ' '),
                                link: link.href,
                                date: ''
                            });
                        }
                    }
                });
            }
            return results;
        }""")
        
        print(f"Found {len(items)} raw items.")
        await browser.close()
        return items

def generate_rss(items):
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    
    title = ET.SubElement(channel, "title")
    title.text = "少数派更新 - sa2syl7a"
    
    link = ET.SubElement(channel, "link")
    link.text = "https://sspai.com/u/sa2syl7a/updates"
    
    description = ET.SubElement(channel, "description")
    description.text = "sa2syl7a 的少数派更新"
    
    for item_data in items:
        item = ET.SubElement(channel, "item")
        
        i_title = ET.SubElement(item, "title")
        i_title.text = item_data['title']
        
        i_link = ET.SubElement(item, "link")
        i_link.text = item_data['link']
        
        i_guid = ET.SubElement(item, "guid")
        i_guid.text = item_data['link']
        
        i_pubDate = ET.SubElement(item, "pubDate")
        i_pubDate.text = item_data['date']
        
    return ET.tostring(rss, encoding='unicode')

async def main():
    try:
        items = await scrape_sspai()
        if not items:
            print("No items found.")
            return
        
        # Remove duplicates
        seen_links = set()
        unique_items = []
        for item in items:
            if item['link'] not in seen_links:
                seen_links.add(item['link'])
                unique_items.append(item)
        
        print(f"Found {len(unique_items)} unique items.")
        for item in unique_items[:5]:
            print(f"- {item['title']} ({item['date']})")
        
        xml_content = generate_rss(unique_items)
        with open("sspai_updates.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
        print("XML saved to sspai_updates.xml")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
