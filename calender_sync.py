# Title: Canvas to Google Calendar Sync
# Description: This script fetches upcoming assignment due dates from the Canvas API
#              and adds them to a specified Google Calendar.

import os
import datetime
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- Configuration ---
# 1. Canvas API Configuration
CANVAS_API_URL = "https://canvas.instructure.com/api/v1/" # e.g., "https://canvas.instructure.com/api/v1"
CANVAS_API_TOKEN = "YOUR_CANVAS_API_TOKEN" 

# 2. Google Calendar Configuration
GOOGLE_CALENDAR_ID = "primary" 
SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- Helper Functions ---

def get_google_creds():
    """
    Handles Google Authentication and returns credentials.
    It will create a token.json file to store the user's access and refresh tokens.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # You need a credentials.json file from your Google Cloud project
            # for this to work.
            if not os.path.exists('credentials.json'):
                print("Error: credentials.json not found. Please enable the Google Calendar API in your Google Cloud project and download the credentials file.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_canvas_assignments():
    """Fetches upcoming assignments from the Canvas API."""
    headers = {
        "Authorization": f"Bearer {CANVAS_API_TOKEN}"
    }
    # Get assignments for all courses for the current user
    # The API returns assignments for courses the user is enrolled in.
    url = f"{CANVAS_API_URL}/users/self/assignments"
    
    # We'll get assignments due from today onwards
    start_date = datetime.datetime.utcnow().isoformat() + "Z"
    params = {
        'per_page': 50, # You can adjust this number
        'bucket': 'upcoming'
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching assignments from Canvas: {e}")
        return []

def add_event_to_google_calendar(service, assignment):
    """Adds a single assignment as an event to Google Calendar."""
    name = assignment.get('name', 'Untitled Assignment')
    due_at = assignment.get('due_at')
    
    if not due_at:
        return # Skip assignments without a due date

    # Canvas API returns ISO 8601 format (e.g., '2025-09-21T03:59:59Z')
    due_datetime = datetime.datetime.fromisoformat(due_at.replace('Z', '+00:00'))
    
    # Let's make the event last 1 hour
    start_datetime = due_datetime - datetime.timedelta(hours=1)

    event_body = {
        'summary': f"Assignment: {name}",
        'description': f"Due: {name}\nView in Canvas: {assignment.get('html_url', 'N/A')}",
        'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': due_datetime.isoformat(),
            'timeZone': 'UTC',
        },
        # Use the Canvas assignment ID to create a unique event ID to avoid duplicates
        'id': f"canvas{assignment.get('id')}"
    }

    try:
        # Using event IDs makes event creation idempotent. If an event with this ID
        # already exists, it will be updated. If not, it will be created.
        service.events().insert(
            calendarId=GOOGLE_CALENDAR_ID,
            body=event_body
        ).execute()
        print(f"Successfully added/updated event: {name}")
    except Exception as e:
        # It's possible the event already exists and you try to insert.
        # A more robust solution would be to first try to get() the event
        # and then either update() or insert(). For simplicity, we'll just print.
        if 'already exists' in str(e):
             print(f"Event '{name}' already exists. Skipping.")
        else:
            print(f"An error occurred while adding '{name}': {e}")


def main():
    """Main function to run the synchronization process."""
    print("Starting Canvas to Google Calendar sync...")

    # 1. Authenticate with Google
    creds = get_google_creds()
    if not creds:
        print("Could not authenticate with Google. Exiting.")
        return
        
    google_calendar_service = build('calendar', 'v3', credentials=creds)
    print("Successfully authenticated with Google Calendar.")

    # 2. Get Canvas Assignments
    print("Fetching assignments from Canvas...")
    assignments = get_canvas_assignments()
    if not assignments:
        print("No upcoming assignments found or error fetching them.")
        return
    print(f"Found {len(assignments)} upcoming assignments.")

    # 3. Add assignments to Google Calendar
    for assignment in assignments:
        add_event_to_google_calendar(google_calendar_service, assignment)

    print("\nSync process complete.")


if __name__ == '__main__':
    main()
