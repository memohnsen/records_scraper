"""
cd /Users/maddisenmohnsen/Desktop/records_scraper
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python records_scraper.py
"""

import io
from PyPDF2 import PdfReader  # Changed from pypdf to PyPDF2
import re
import requests

def parse_lift_line(line):
    """Parse a single lift line to extract lift name and weight."""
    # More flexible pattern matching for lift lines
    pattern = r'(Snatch|C&J(?:erk)?|Total).*?(\d+(?:\.\d+)?kg)'
    match = re.search(pattern, line, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    return None, None

def kg_to_number(kg_string):
    """Convert kg string to number"""
    return int(float(kg_string.replace('kg', '')))

def format_weight_class(weight_class):
    """Convert weight class format from '109kg+' to '+109kg'"""
    if '+' in weight_class:
        number = weight_class.replace('kg+', '')
        return f"+{number}kg"
    return weight_class

def weight_class_sort_key(key):
    """Helper function to sort weight classes numerically"""
    gender, weight = key.split(' ')
    # Handle plus weight classes (they should be last in their gender group)
    if '+' in weight:
        number = int(weight.replace('+', '').replace('kg', ''))
        # Add a large number to make plus classes sort last
        number += 1000
    else:
        number = int(weight.replace('kg', ''))
    return (gender, number)

def normalize_age_group(age_group):
    """Normalize age group strings to match mapping keys"""
    age_group = ' '.join(age_group.split())  # Normalize whitespace
    if "Youth" in age_group:
        if "13" in age_group and "Under" in age_group:
            return "Youth Men (13 and Under)" if "Men" in age_group else "Youth Women (13 and Under)"
        elif "14-15" in age_group or "14 and 15" in age_group:
            return "Youth Men (14-15)" if "Men" in age_group else "Youth Women (14-15)"
        elif "16-17" in age_group or "16 and 17" in age_group:
            return "Youth Men (16-17)" if "Men" in age_group else "Youth Women (16-17)"
    return age_group

def format_for_typescript(records):
    """Format records into TypeScript structure"""
    seen_records = {}  # Initialize seen_records at the start
    
    # Initialize structure
    result = {
        "senior": {},
        "junior": {},
        "collegiate": {},
        "U13": {},
        "U15": {},
        "U17": {}
    }
    
    # Simplified age group mapping
    age_group_mapping = {
        "Open Men": ("senior", "Male"),
        "Open Women": ("senior", "Female"),
        "Junior Men": ("junior", "Male"),
        "Junior Women": ("junior", "Female"),
        "Collegiate Men": ("collegiate", "Male"),
        "Collegiate Women": ("collegiate", "Female"),
        "Youth Men (13 and Under)": ("U13", "Male"),
        "Youth Men (14-15)": ("U15", "Male"),
        "Youth Men (16-17)": ("U17", "Male"),
        "Youth Women (13 and Under)": ("U13", "Female"),
        "Youth Women (14-15)": ("U15", "Female"),
        "Youth Women (16-17)": ("U17", "Female")
    }
    
    for record in records:
        # Normalize the age group string
        age_group = normalize_age_group(record['age_group'])
        if age_group not in age_group_mapping:
            print(f"Skipping unknown age group: {age_group} (original: {record['age_group']})")
            continue
            
        category, gender = age_group_mapping[age_group]
        weight_class = format_weight_class(record['weight_class'])
        key = f"{gender} {weight_class}"
        
        # Track unique key per category/weight class combination
        track_key = (category, key)
        record_total = kg_to_number(record.get('total', '0kg'))
        
        if track_key in seen_records and kg_to_number(seen_records[track_key].get('total', '0kg')) >= record_total:
            continue
            
        seen_records[track_key] = record
        if key not in result[category]:
            result[category][key] = {}
            
        result[category][key] = {
            "americanRecords": {
                "snatch": kg_to_number(record.get('snatch', '0kg')),
                "cleanAndJerk": kg_to_number(record.get('clean_and_jerk', '0kg')),
                "total": record_total
            }
        }
        print(f"Added record for {category} - {key}")
    
    # Restructure for final output
    final_result = {
        "senior": result["senior"],
        "junior": result["junior"],
        "collegiate": result["collegiate"],
        "youth": {
            "U13": result["U13"],
            "U15": result["U15"],
            "U17": result["U17"]
        }
    }
    
    return final_result

def extract_weightlifting_records_from_url(pdf_url):
    records = []
    current_age_group = None
    pending_record = None
    last_weight_class = None

    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        pdf_content = io.BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: {e}")
        return []

    reader = PdfReader(pdf_content)
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        i = 0

        # Check for age group changes at start of page
        for line in lines[:5]:
            # More specific youth age group detection
            if any(x in line for x in ["13 years old and Under", "14-15", "16-17"]):
                current_age_group = line.strip()
                last_weight_class = None
                break
            elif "American Records" in line:
                current_age_group = line.strip()
                last_weight_class = None
                break

        # Regular page processing
        while i < len(lines):
            line = lines[i].strip()

            # More specific youth age group detection
            if "13 years old and Under" in line:
                current_age_group = line.strip()
            elif "14-15" in line and "Youth" in line:
                current_age_group = line.strip()
            elif "16-17" in line and "Youth" in line:
                current_age_group = line.strip()
            # Regular age group detection
            elif "Open Men American Records" in line:
                current_age_group = "Open Men"
            elif "Junior Men American Records" in line:
                current_age_group = "Junior Men"
            elif "Open Women American Records" in line:
                current_age_group = "Open Women"
            elif "Junior Women American Records" in line:
                current_age_group = "Junior Women"
            elif "Collegiate Men American Records" in line:
                current_age_group = "Collegiate Men"
            elif "Collegiate Women American Records" in line:
                current_age_group = "Collegiate Women"
            elif "Youth Men American Records: 13 years old and Under" in line:
                current_age_group = "Youth Men (13 and Under)"
            elif "Youth Men American Records: 14-15 year old" in line:
                current_age_group = "Youth Men (14-15)"
            elif "Youth Men American Records: 16-17 year old" in line:
                current_age_group = "Youth Men (16-17)"
            elif "Youth Women American Records: 13 years old and Under" in line:
                current_age_group = "Youth Women (13 and Under)"
            elif "Youth Women American Records: 14 and 15 Years old" in line:
                current_age_group = "Youth Women (14-15)"
            elif "Youth Women American Records: 16 and 17 years old" in line:
                current_age_group = "Youth Women (16-17)"

            # Look for weight class line
            if current_age_group:
                # Updated pattern to catch both "55kg" and "109kg+" formats
                weight_class_match = re.search(r'(?:^|\s)(\d+kg\+|\d+kg)(?:\s|$)', line)
                if weight_class_match and not any(lift in line.lower() for lift in ['snatch', 'c&j', 'total']):
                    weight_class = weight_class_match.group(1)
                    print(f"\nFound weight class: {weight_class} in {current_age_group}")  # Debug
                    
                    record_data = {
                        'age_group': current_age_group,
                        'weight_class': weight_class,
                        'lifts': []
                    }

                    # Look ahead for lift records
                    lifts_found = 0
                    next_lines = lines[i+1:i+5]  # Look at more lines to ensure we don't miss any
                    
                    for next_line in next_lines:
                        lift_name, weight = parse_lift_line(next_line)
                        if lift_name and weight:
                            lifts_found += 1
                            if lift_name.lower() == 'snatch':
                                record_data['snatch'] = weight
                            elif 'c&j' in lift_name.lower():
                                record_data['clean_and_jerk'] = weight
                            elif lift_name.lower() == 'total':
                                record_data['total'] = weight
                            
                            if lifts_found == 3:  # Found all lifts
                                break

                    if lifts_found == 3:
                        records.append(record_data)
                        print(f"Added record: {record_data}")  # Debug
                        i += lifts_found  # Skip the lift lines we processed
                    elif lifts_found > 0:  # Partial record found, might continue on next page
                        pending_record = {
                            'data': record_data,
                            'lifts_found': lifts_found
                        }
                        print(f"Pending record for next page: {record_data}")
                    else:
                        print(f"Warning: Only found {lifts_found} lifts for {weight_class}")  # Debug
            last_weight_class = weight_class if 'weight_class' in locals() else None
            i += 1

    return records

def format_as_typescript(records_data):
    """Convert the records data into properly formatted TypeScript"""
    lines = ['export const recordsAndStandards = {']
    
    # Sort categories
    categories = sorted(records_data.keys())
    
    for category in categories:
        if records_data[category]:  # Only include non-empty categories
            lines.append(f'  {category}: {{')
            
            if category == 'youth':
                # Handle youth subcategories
                for youth_cat in ['U13', 'U15', 'U17']:
                    if youth_cat in records_data[category]:
                        lines.append(f'    {youth_cat}: {{')
                        # Sort records within youth category
                        sorted_keys = sorted(records_data[category][youth_cat].keys(), key=weight_class_sort_key)
                        for key in sorted_keys:
                            record = records_data[category][youth_cat][key]
                            lines.append(f'      "{key}": {{')
                            lines.append('        americanRecords: {')
                            lines.append(f'          snatch: {record["americanRecords"]["snatch"]},')
                            lines.append(f'          cleanAndJerk: {record["americanRecords"]["cleanAndJerk"]},')
                            lines.append(f'          total: {record["americanRecords"]["total"]}')
                            lines.append('        }')
                            lines.append('      },')
                        if lines[-1].endswith(','):
                            lines[-1] = lines[-1][:-1]
                        lines.append('    },')
                if lines[-1].endswith(','):
                    lines[-1] = lines[-1][:-1]
            else:
                # Handle regular categories
                sorted_keys = sorted(records_data[category].keys(), key=weight_class_sort_key)
                for key in sorted_keys:
                    record = records_data[category][key]
                    lines.append(f'    "{key}": {{')
                    lines.append('      americanRecords: {')
                    lines.append(f'        snatch: {record["americanRecords"]["snatch"]},')
                    lines.append(f'        cleanAndJerk: {record["americanRecords"]["cleanAndJerk"]},')
                    lines.append(f'        total: {record["americanRecords"]["total"]}')
                    lines.append('      }')
                    lines.append('    },')
                if lines[-1].endswith(','):
                    lines[-1] = lines[-1][:-1]
            
            lines.append('  },')
    
    # Remove trailing comma from last category
    if lines[-1].endswith(','):
        lines[-1] = lines[-1][:-1]
    
    lines.append('};')
    return '\n'.join(lines)

if __name__ == "__main__":
    pdf_url = "https://assets.contentstack.io/v3/assets/blteb7d012fc7ebef7f/blt5a90ccbbc6d0a7c4/6759dfa9bbb2f6329539aa03/2024_American_records_121024.pdf"
    weightlifting_data = extract_weightlifting_records_from_url(pdf_url)
    
    # Format data for TypeScript
    records_data = format_for_typescript(weightlifting_data)
    typescript_formatted = format_as_typescript(records_data)
    
    # Print to console
    print(typescript_formatted)
    
    # Write to TypeScript file
    with open('weightlifting_records.ts', 'w') as f:
        f.write(typescript_formatted)