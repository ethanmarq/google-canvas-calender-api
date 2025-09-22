# Title: Canvas to Google Calendar Sync
# Description: This script fetches upcoming assignment due dates from the Canvas API
#              and adds them to a specified Google Calendar.

import os
import sys
import datetime
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
# 1. Canvas API Configuration
CANVAS_API_URL = "https://canvas.instructure.com/api/v1/" # e.g., "https://canvas.instructure.com/api/v1"
CANVAS_API_TOKEN = os.environ.get('CANVAS_API_TOKEN')

# 2. Google Calendar Configuration
GOOGLE_CALENDAR_ID = "primary" 
SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- Helper Functions ---


def get_google_creds():
    """Gets valid user credentials from storage or initiates OAuth2 flow."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_canvas_assignments(api_url, api_token):
    """Fetches upcoming assignments from the Canvas API."""
    headers = {'Authorization': f'Bearer {api_token}'}
    # This endpoint gets upcoming assignments for the user
    assignments_url = f'{api_url}/api/v1/users/self/upcoming_events'
    try:
        response = requests.get(assignments_url, headers=headers)
        response.raise_for_status()  # Raises an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from Canvas API: {e}", file=sys.stderr)
        return []

def create_google_calendar_event(service, assignment):
    """Creates a Google Calendar event for a given Canvas assignment."""
    due_at_str = assignment.get('end_at')
    if not due_at_str:
        return # Skip assignments with no due date

    # Canvas dates are in ISO 8601 format (UTC)
    due_at = datetime.datetime.fromisoformat(due_at_str.replace('Z', '+00:00'))
    
    # Google Calendar API works well with RFC3339 format
    start_time = (due_at - datetime.timedelta(hours=1)).isoformat()
    end_time = due_at.isoformat()

    # Use a unique ID to prevent duplicate events on subsequent runs
    event_id = f"canvas{assignment.get('id')}".replace('-', '').lower()

    event = {
        'id': event_id,
        'summary': assignment.get('title', 'Untitled Assignment'),
        'description': f"Due: {assignment.get('title')}\nCourse: {assignment.get('context_name')}\nLink: {assignment.get('html_url')}",
        'start': {
            'dateTime': start_time,
        },
        'end': {
            'dateTime': end_time,
        },
    }

    try:
        # Use insert with the event ID. If it exists, it fails, so we update it.
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"Created event: {event['summary']}")
    except HttpError as error:
        if error.resp.status == 409: # 409 is the status code for "Conflict" (duplicate ID)
            try:
                service.events().update(calendarId=CALENDAR_ID, eventId=event_id, body=event).execute()
                print(f"Updated event: {event['summary']}")
            except HttpError as update_error:
                print(f"Failed to update event '{event['summary']}': {update_error}", file=sys.stderr)
        else:
            print(f"An error occurred creating event '{event['summary']}': {error}", file=sys.stderr)

def main():
    """Main function to run the sync process."""
    # Gracefully exit if the API token is not set
    if not CANVAS_API_TOKEN:
        print("Error: The CANVAS_API_TOKEN environment variable is not set.", file=sys.stderr)
        print("Please create a .env file (and add it to .gitignore) with the line:", file=sys.stderr)
        print("export CANVAS_API_TOKEN='your_token_here'", file=sys.stderr)
        sys.exit(1)

    creds = get_google_creds()
    try:
        service = build('calendar', 'v3', credentials=creds)
        print("Successfully connected to Google Calendar.")

        assignments = get_canvas_assignments(CANVAS_API_URL, CANVAS_API_TOKEN)
        if not assignments:
            print("No upcoming assignments found or failed to fetch from Canvas.")
            return

        print(f"Found {len(assignments)} upcoming assignments. Syncing to Google Calendar...")
        for assignment in assignments:
            create_google_calendar_event(service, assignment)
        print("Sync complete.")

    except HttpError as error:
        print(f'An error occurred with the Google API: {error}', file=sys.stderr)
    except Exception as e:
        print(f'An unexpected error occurred: {e}', file=sys.stderr)

if __name__ == '__main__':
    main()

