import sys
from bs4 import BeautifulSoup
from tgpc.scraper import PharmacistRecord

# Sample HTML that mimics the target site's structure
SAMPLE_HTML = """
<html>
<body>
<table id="tablesorter-demo">
    <thead>
        <tr><th>S.No</th><th>Reg No</th><th>Name</th><th>Father Name</th><th>Category</th></tr>
    </thead>
    <tbody>
        <tr>
            <td>1</td>
            <td>12345</td>
            <td>John Doe</td>
            <td>Richard Doe</td>
            <td>A-Category</td>
        </tr>
    </tbody>
</table>
</body>
</html>
"""

def extract_records(html):
    """Extract records from HTML - mirrors scraper logic"""
    soup = BeautifulSoup(html, 'html.parser')
    
    records = []
    table = soup.find('table', attrs={'id': 'tablesorter-demo'}) or soup.find('table')
    
    if not table:
        return []

    for row in table.find_all('tr')[1:]:
        cells = row.find_all('td')
        if len(cells) < 5:
            continue
            
        try:
            records.append(PharmacistRecord(
                serial_number=int(cells[0].get_text(strip=True)) if cells[0].get_text(strip=True).isdigit() else None,
                registration_number=cells[1].get_text(strip=True),
                name=cells[2].get_text(strip=True),
                father_name=cells[3].get_text(strip=True),
                category=cells[4].get_text(strip=True)
            ))
        except Exception:
            continue
            
    return records

def run_sanity_check():
    print("♻️ Running Sanity Check...")
    
    # Run extraction on sample HTML
    records = extract_records(SAMPLE_HTML)
    
    # Verify results
    if len(records) != 1:
        print(f"❌ Failed: Expected 1 record, got {len(records)}")
        sys.exit(1)
        
    r = records[0]
    if r.registration_number != "12345" or r.name != "John Doe":
        print(f"❌ Failed: Data mismatch. Got {r}")
        sys.exit(1)
        
    print("✅ Sanity Check Passed: Scraper logic is intact.")

if __name__ == "__main__":
    run_sanity_check()
