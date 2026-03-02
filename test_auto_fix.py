# Test file with intentional errors for auto-fix testing

def get_test_data():
    # Missing return statement - auto-fix should catch this
    data = {"test": "data"}
    # Oops, forgot to return!

def another_function()
    # Missing colon - auto-fix should catch this
    print("This will cause syntax error")

# Missing import - auto-fix should catch this
result = json.dumps(data)
