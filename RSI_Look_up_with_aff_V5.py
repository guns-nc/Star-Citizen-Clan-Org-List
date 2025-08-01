# -*- coding: utf-8 -*-
"""
Created on Sat Apr 19 19:03:13 2025

@author: Guns-NC
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import sys
import os

def scrape_org_members(org_sid, delay=2.0, output_file="org_members.csv"):
    """
    A robust function to scrape Star Citizen org members
    with correct URL handling for organization affiliations.
    All affiliations for a member are stored in a single row.
    """
    print(f"Starting to scrape organization: {org_sid}")
    print(f"Using delay: {delay} seconds between requests")
    
    # Set up session with headers to mimic a browser
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    
    # Base URL for the organization
    base_url = f"https://robertsspaceindustries.com/orgs/{org_sid}"
    members_url = f"{base_url}/members"
    
    # Try to access the org page first
    try:
        print(f"Connecting to {members_url}...")
        response = session.get(members_url)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not access organization page: {e}")
        return False
    
    # Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check if org exists
    if "The page you were looking for doesn't exist" in response.text:
        print(f"Error: Organization '{org_sid}' not found.")
        return False
    
    # Try to get member count
    try:
        # Get the member count from the page
        member_count_element = soup.select_one(".or-members-info")
        if member_count_element:
            member_count_text = member_count_element.get_text().strip()
            import re
            match = re.search(r'Members\s*\((\d+)\)', member_count_text)
            if match:
                member_count = int(match.group(1))
                print(f"Found {member_count} members in organization.")
            else:
                print("Could not parse member count. Continuing anyway.")
                member_count = None
        else:
            print("Member count element not found. Continuing anyway.")
            member_count = None
    except Exception as e:
        print(f"Error getting member count: {e}")
        member_count = None
    
    # Initialize list to store members
    all_members = []
    page = 1
    
    # Create debug directory
    debug_dir = "debug_pages"
    os.makedirs(debug_dir, exist_ok=True)
    
    # Loop through pages until no more members are found
    while True:
        print(f"Scraping page {page}...")
        
        # Construct URL for current page
        page_url = f"{members_url}?page={page}"
        
        try:
            # Get the page
            response = session.get(page_url)
            response.raise_for_status()
            
            # Save debug copy of the HTML
            with open(os.path.join(debug_dir, f"page_{page}.html"), "w", encoding="utf-8") as f:
                f.write(response.text)
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all member items
            member_elements = soup.select(".member-item")
            
            if not member_elements:
                print(f"No members found on page {page}. Stopping.")
                break
            
            print(f"Found {len(member_elements)} members on page {page}.")
            
            # Process each member
            for i, member in enumerate(member_elements):
                try:
                    # Extract member data
                    handle_elem = member.select_one(".nick")
                    rank_elem = member.select_one(".rank")
                    join_date_elem = member.select_one(".join-date")
                    
                    # Extract text content safely
                    handle = handle_elem.get_text().strip() if handle_elem else "Unknown"
                    rank = rank_elem.get_text().strip() if rank_elem else "Unknown"
                    join_date = join_date_elem.get_text().strip() if join_date_elem else "Unknown"
                    
                    # Get profile URL (we'll extract the handle from this for organizations URL)
                    profile_url = ""
                    profile_elem = member.select_one("a")
                    if profile_elem and profile_elem.has_attr('href'):
                        profile_url = "https://robertsspaceindustries.com" + profile_elem['href']
                        
                        # Extract handle from URL if possible
                        # The handle is needed for the organizations URL
                        citizen_handle = handle  # Default to displayed handle
                        
                        # Try to extract handle from URL which may be in format like /citizens/USERNAME
                        url_parts = profile_url.split('/')
                        if len(url_parts) > 4 and url_parts[-2] == "citizens":
                            citizen_handle = url_parts[-1]
                    
                    # Print progress
                    print(f"  {i+1}/{len(member_elements)}: {handle} ({rank})")
                    
                    # Now try to get affiliated orgs using the correct URL format
                    affiliated_orgs = []
                    
                    if profile_url:
                        try:
                            # Construct the correct URL for the organizations page
                            orgs_url = f"https://robertsspaceindustries.com/en/citizens/{citizen_handle}/organizations"
                            
                            print(f"    Getting affiliations for {handle} from {orgs_url}...")
                            
                            # Visit organizations page
                            orgs_response = session.get(orgs_url)
                            orgs_response.raise_for_status()
                            
                            # Save debug copy
                            with open(os.path.join(debug_dir, f"orgs_{handle}.html"), "w", encoding="utf-8") as f:
                                f.write(orgs_response.text)
                            
                            orgs_soup = BeautifulSoup(orgs_response.text, 'html.parser')
                            
                            # Find organization elements
                            org_elements = orgs_soup.select(".orgs-content .org, .organization-item, .org-item, .organization")
                            
                            if org_elements:
                                for org in org_elements:
                                    try:
                                        # Extract organization SID from various sources
                                        org_sid_found = "Unknown"
                                        
                                        # Try to find SID through a selector
                                        org_sid_elem = org.select_one(".sid, .org-sid")
                                        if org_sid_elem:
                                            org_sid_found = org_sid_elem.get_text().strip()
                                        
                                        # Also try to get org URL if available and extract SID from it
                                        org_url = ""
                                        org_link = org.select_one("a")
                                        if org_link and org_link.has_attr('href'):
                                            org_url = org_link['href']
                                            if not org_url.startswith('http'):
                                                org_url = "https://robertsspaceindustries.com" + org_url
                                            # Try to extract SID from URL
                                            if "/orgs/" in org_url:
                                                org_sid_found = org_url.split('/')[-1]
                                        
                                        # Only add SID to the list
                                        affiliated_orgs.append({
                                            "org_sid": org_sid_found
                                        })
                                    except Exception as e:
                                        print(f"    Error parsing affiliated org: {e}")
                                
                                print(f"    Found {len(affiliated_orgs)} affiliated orgs")
                            else:
                                print("    No organizations found or private profile")
                            
                        except Exception as e:
                            print(f"    Error getting affiliated orgs: {e}")
                    
                    # Add member to list
                    member_data = {
                        "handle": handle,
                        "rank": rank,
                        "join_date": join_date,
                        "profile_url": profile_url,
                        "affiliated_orgs": affiliated_orgs
                    }
                    all_members.append(member_data)
                    
                    # Wait between profile requests
                    time.sleep(delay)
                    
                except Exception as e:
                    print(f"  Error processing member: {e}")
            
            # Go to next page
            page += 1
            
            # Wait between page requests
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error scraping page {page}: {e}")
            break
    
    # Done scraping, save results
    if all_members:
        # Save to CSV with only SID data for affiliated organizations
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            # Define column headers: basic member info + up to 5 affiliated org SIDs
            fieldnames = ["handle", "rank", "join_date", "profile_url"]
            
            # Add fields for up to 5 affiliated org SIDs only
            for i in range(1, 6):
                fieldnames.append(f"org_{i}_sid")
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for member in all_members:
                # Create a row for this member
                row = {
                    "handle": member["handle"],
                    "rank": member["rank"],
                    "join_date": member["join_date"],
                    "profile_url": member["profile_url"]
                }
                
                # Initialize all org SID fields with empty strings
                for i in range(1, 6):
                    row[f"org_{i}_sid"] = ""
                
                # Add up to 5 affiliated org SIDs
                for i, org in enumerate(member["affiliated_orgs"][:5], 1):
                    row[f"org_{i}_sid"] = org["org_sid"]
                
                writer.writerow(row)
        
        print(f"Saved {len(all_members)} members to {output_file}")
        print(f"Each row contains a member with up to 5 affiliated organization SIDs.")
        
        return True
    else:
        print("No members found or error occurred.")
        return False

def main():
    print("Star Citizen Organization Member & Affiliations Scraper (SID only)")
    print("-----------------------------------------------------")
    
    # Get org SID from command line argument or prompt
    if len(sys.argv) > 1:
        org_sid = sys.argv[1]
    else:
        org_sid = input("Enter organization SID (the short name that appears in the URL, e.g., TEST): ").strip()
    
    # Get delay from user or use default
    delay_str = input("Enter delay between requests in seconds (default is 2.0): ").strip()
    delay = float(delay_str) if delay_str else 2.0
    
    # Get output filename or use default
    output_file = input("Enter output CSV filename (default is org_members.csv): ").strip()
    if not output_file:
        output_file = "org_members.csv"
    
    print("\nStarting scraper...")
    print("NOTE: This will save debugging data in a 'debug_pages' folder")
    print("which may help diagnose any issues.\n")
    
    # Run the scraper
    success = scrape_org_members(org_sid, delay, output_file)
    
    if success:
        print("\nScraping completed successfully!")
        print("Each member row now includes up to 5 affiliated organization SIDs.")
    else:
        print("\nScraping failed or no members were found.")
    
    print("\nIf you have issues, please check the 'debug_pages' folder for the HTML content")
    print("that was downloaded, which may help diagnose what went wrong.")

if __name__ == "__main__":
    main()