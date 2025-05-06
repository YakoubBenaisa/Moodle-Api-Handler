
import requests
import json
from bs4 import BeautifulSoup
import re
import os


def get_courses(session, id):
    # Make the request to get the category page
    print(f"Fetching courses for category ID: {id}")
    response = session.get(f"https://elearning.univ-bba.dz/course/index.php?categoryid={id}")
    
    # Save the HTML for debugging
    with open("courses_debug.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    print(f"Response status code: {response.status_code}")
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find course items in this category
    courses_data = []
    
    # Print the title of the page to verify we're on the right page
    page_title = soup.find("title")
    if page_title:
        print(f"Page title: {page_title.text}")
    
    # Check if we're logged in by looking for user-specific elements
    user_menu = soup.find("div", {"class": "usermenu"})
    if user_menu:
        print("User appears to be logged in")
    else:
        print("WARNING: User might not be logged in")
    
    # Try different selectors to find course boxes
    course_boxes = soup.find_all("div", {"class": "coursebox"})
    print(f"Found {len(course_boxes)} course boxes with class 'coursebox'")
    
    if len(course_boxes) == 0:
        # Try alternative selectors
        course_boxes = soup.find_all("div", {"class": "course-info-container"})
        print(f"Found {len(course_boxes)} course boxes with class 'course-info-container'")
        
        if len(course_boxes) == 0:
            # Try another alternative
            course_boxes = soup.find_all("div", {"class": "card"})
            print(f"Found {len(course_boxes)} potential course boxes with class 'card'")
    
    for i, box in enumerate(course_boxes):
        print(f"Processing course box {i+1}")
        course_data = {}
        
        # Try different selectors for course name
        course_name_div = box.find("div", {"class": "coursename"})
        if not course_name_div:
            course_name_div = box.find("div", {"class": "course-name"})
        if not course_name_div:
            course_name_div = box.find("h3", {"class": "coursename"})
        
        if course_name_div:
            print(f"Found course name div: {course_name_div.text.strip()}")
            course_link = course_name_div.find("a")
            if course_link:
                course_data["name"] = course_link.text.strip()
                course_data["url"] = course_link.get("href")
                print(f"Course name: {course_data['name']}")
                print(f"Course URL: {course_data['url']}")
                
                # Extract course ID from URL
                course_id_match = re.search(r"id=(\d+)", course_link.get("href"))
                if course_id_match:
                    course_data["id"] = course_id_match.group(1)
                    print(f"Course ID: {course_data['id']}")
        else:
            # If we can't find the course name div, try to find any link that might be a course
            course_link = box.find("a")
            if course_link and "course/view.php" in course_link.get("href", ""):
                course_data["name"] = course_link.text.strip()
                course_data["url"] = course_link.get("href")
                print(f"Found course link directly: {course_data['name']}")
        
        # Only add courses that have at least a name
        if "name" in course_data:
            courses_data.append(course_data)
        else:
            print("No course name found in this box, skipping")
    
    print(f"Total courses found: {len(courses_data)}")
    
    # Convert to JSON
    courses_json = json.dumps(courses_data, indent=4, ensure_ascii=False)
    
    # Save to file
    with open(f"courses_category_{id}.json", "w", encoding="utf-8") as f:
        f.write(courses_json)
    
    return courses_data
