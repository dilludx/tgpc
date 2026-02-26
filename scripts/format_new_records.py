#!/usr/bin/env python3
"""
Format new records for email notification.
Reads JSON from stdin and formats for display.
"""

import json
import sys
from typing import List, Dict, Any

def format_records(records: List[Dict[str, Any]]) -> str:
    """Format records for email display."""
    if not records:
        return "No new records to display."
    
    formatted = []
    for i, record in enumerate(records, 1):
        reg_no = record.get('registration_number', 'N/A')
        name = record.get('name', 'N/A')
        category = record.get('category', 'N/A')
        father_name = record.get('father_name', 'N/A')
        
        formatted_line = f"{i}. {reg_no} - {name} ({category})"
        if father_name != 'N/A':
            formatted_line += f"\n   Father: {father_name}"
        
        formatted.append(formatted_line)
    
    return "\n".join(formatted)

def main():
    try:
        # Read from stdin
        input_data = sys.stdin.read()
        if not input_data.strip():
            print("No new records to display.")
            return
        
        records = json.loads(input_data)
        output = format_records(records)
        print(output)
        
    except json.JSONDecodeError as e:
        print(f"Error parsing records: {e}")
        print("Raw input:", input_data[:200] + "..." if len(input_data) > 200 else input_data)
    except Exception as e:
        print(f"Error formatting records: {e}")

if __name__ == "__main__":
    main()
