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

def extract_weightlifting_records_from_url(pdf_url):
    """
    Extracts weightlifting records from PDF, processing each weight class and its three lift rows.
    """
    records = []
    current_age_group = None

    try:
        response = requests.get(pdf_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        pdf_content = io.BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: {e}")
        return []

    reader = PdfReader(pdf_content)
    for page in reader.pages:
        text = page.extract_text()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        i = 0
        
        print(f"\nProcessing page with {len(lines)} lines")  # Debug output
        
        while i < len(lines):
            line = lines[i].strip()

            # Identify age groups
            if "Open Men American Records" in line:
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
                # Updated pattern to better handle +kg weight classes
                weight_class_match = re.search(r'(?:^|\s)(\d+(?:\+)?kg)(?:\s|$)', line)
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
                    else:
                        print(f"Warning: Only found {lifts_found} lifts for {weight_class}")  # Debug
            i += 1

    # Final validation
    age_groups = {}
    for record in records:
        group = record['age_group']
        age_groups[group] = age_groups.get(group, 0) + 1

    print("\nRecords per age group:")
    for group, count in age_groups.items():
        print(f"{group}: {count} weight classes")

    return records

if __name__ == "__main__":
    pdf_url = "https://assets.contentstack.io/v3/assets/blteb7d012fc7ebef7f/blt5a90ccbbc6d0a7c4/6759dfa9bbb2f6329539aa03/2024_American_records_121024.pdf"
    weightlifting_data = extract_weightlifting_records_from_url(pdf_url)

    for record in weightlifting_data:
        print(record)