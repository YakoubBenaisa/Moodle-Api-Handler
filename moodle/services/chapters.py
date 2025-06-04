

import requests
import json
from bs4 import BeautifulSoup
import re
import os


def get_chapters(session, id, university_name):
    response = session.get(f"https://elearning.univ-{university_name}.dz/course/view.php?id={id}")
    
 
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Get course title
    course_title = ""
    title_element = soup.find("h1", {"class": "h2"})
    if title_element:
        course_title = title_element.text.strip()
    
    # Find all sections
    sections = soup.find_all("li", {"class": "section", "data-for": "section"})
    
    chapters_data = []
    
    for section in sections:
        section_data = {}
        
        # Get section ID and number
        section_id = section.get("data-id")
        section_number = section.get("data-number")
        
        # Get section name
        section_name = ""
        section_title = section.find("h3", {"class": "sectionname"})
        if section_title:
            section_name = section_title.text.strip()
        
        section_data = {
            "id": section_id,
            "number": section_number,
            "name": section_name,
            "activities": []
        }
        
        # Get section summary
        summary_div = section.find("div", {"class": "summarytext"})
        if summary_div:
            section_data["summary"] = summary_div.text.strip()
        
        # Find all activities in this section
        activities = section.find_all("li", {"class": "activity"})
        
        for activity in activities:
            activity_data = {}
            
            # Get activity name
            activity_name_element = activity.get("data-activityname")
            if not activity_name_element:
                activity_name_div = activity.find("div", {"data-region": "activity-information"})
                if activity_name_div:
                    activity_name_element = activity_name_div.get("data-activityname")
            
            if not activity_name_element:
                activity_name_span = activity.find("span", {"class": "instancename"})
                if activity_name_span:
                    activity_name_element = activity_name_span.text.strip()
            
            if activity_name_element:
                activity_data["name"] = activity_name_element
            
            # Get activity link
            activity_link = activity.find("a", {"class": "aalink"})
            if activity_link:
                activity_data["url"] = activity_link.get("href")
                
                # Extract activity ID from URL
                activity_id_match = re.search(r"id=(\d+)", activity_link.get("href"))
                if activity_id_match:
                    activity_data["id"] = activity_id_match.group(1)
            
            # Get activity type
            activity_type = None
            activity_classes = activity.get("class", [])
            for cls in activity_classes:
                if cls.startswith("modtype_"):
                    activity_type = cls.replace("modtype_", "")
                    break
            
            if activity_type:
                activity_data["type"] = activity_type
            
            # Only add activities that have at least a name or URL
            if "name" in activity_data or "url" in activity_data:
                section_data["activities"].append(activity_data)
        
        chapters_data.append(section_data)
    
    # Create the final data structure
    result = {
        "course_id": id,
        "course_title": course_title,
        "sections": chapters_data
    }
    
    
    
    return result
