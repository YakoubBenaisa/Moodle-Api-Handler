import requests
from bs4 import BeautifulSoup

def get_resource(session, resource_id):
    """
    Fetches a resource (like PDF) from Moodle
    
    Args:
        session: The requests session with authentication cookies
        resource_id: The ID of the resource to fetch
        
    Returns:
        dict: Contains content, content_type, and filename if successful
              or error message if failed
    """
   
    url = f"https://elearning.univ-bba.dz/mod/resource/view.php?id={resource_id}"
    response = session.get(url, stream=True, allow_redirects=True)
    
    if response.url.endswith('.pdf'):
        return {
            'content': response.content,
            'content_type': 'application/pdf',
            'filename': f"resource_{resource_id}.pdf"
        }
    
    soup = BeautifulSoup(response.text, "html.parser")
    resource_link = soup.find("a", {"class": "resourcelinkdetails"})
    
    if resource_link and resource_link.get("href"):
        file_url = resource_link.get("href")
        file_response = session.get(file_url, stream=True)
        
        content_disposition = file_response.headers.get('Content-Disposition', '')
        filename = f"resource_{resource_id}"
        if 'filename=' in content_disposition:
            try:
                filename = content_disposition.split('filename=')[1].strip('"\'')
            except:
                pass
        
        return {
            'content': file_response.content,
            'content_type': file_response.headers.get('Content-Type', 'application/pdf'),
            'filename': filename
        }
    
    return {'error': 'Could not retrieve the resource'}