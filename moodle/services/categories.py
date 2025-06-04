

def get_categories(session):
    import requests
    import json
    from bs4 import BeautifulSoup
    import os


    # Otherwise fetch it from the website
    response = session.get("https://elearning.univ-bba.dz/course/index.php")
    html_content = response.text
    # Save for future reference
    #with open("courses.html", "w", encoding="utf-8") as f:
     #   f.write(html_content)
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Find the course categories from the dropdown select
    categories_data = []
    select_element = soup.find("select", {"name": "jump"})
    
    if select_element:
        options = select_element.find_all("option")
        
        for option in options:
            category_url = option.get("value")
            category_name = option.text.strip()
            
            # Skip if not a valid category URL
            if not category_url or "categoryid" not in category_url:
                continue
                
            # Extract category ID from URL
            category_id = None
            if "categoryid=" in category_url:
                category_id = category_url.split("categoryid=")[1].split("&")[0]
            
            # Get subcategories by visiting the category page
            subcategories = []
            try:
                cat_response = session.get(category_url)
                cat_soup = BeautifulSoup(cat_response.text, "html.parser")
                
                # Find course items in this category
                course_items = cat_soup.find_all("div", {"class": "coursebox"})
                
                for item in course_items:
                    course_name_div = item.find("div", {"class": "coursename"})
                    if course_name_div:
                        course_link = course_name_div.find("a")
                        if course_link:
                            subcategories.append({
                                "name": course_link.text.strip(),
                                "url": course_link.get("href")
                            })
            except Exception as e:
                print(f"Error fetching subcategories for {category_name}: {str(e)}")
            
            categories_data.append({
                "id": category_id,
                "name": category_name,
                "url": category_url
        })
    
    # Convert to JSON
    categories_json = json.dumps(categories_data, indent=4, ensure_ascii=False)
    
    # Save to file
    with open("courses.json", "w", encoding="utf-8") as f:
        f.write(categories_json)
        
    return categories_data
