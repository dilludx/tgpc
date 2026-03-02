# Real test file with multiple syntax errors

def scrape_data()
    # Missing colon - should be caught
    print("This will cause syntax error")
    
def process_data(data)
    # Missing return statement
    processed = data.upper()
    # Oops, no return!

# Missing import - should be caught
result = json.dumps({"status": "success"})
