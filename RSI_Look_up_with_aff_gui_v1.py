# -*- coding: utf-8 -*-
"""
Created on Mon Jul 28 18:55:04 2025

@author: Guns-NC
#need to run "pip install requests beautifulsoup4" in console before first time ever running this script
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import csv
import time
import re

class StarCitizenScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Star Citizen Organization Scraper")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Variables
        self.is_scraping = False
        self.scraping_thread = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Star Citizen Organization Scraper", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Organization SID input
        ttk.Label(main_frame, text="Organization SID:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.org_sid_var = tk.StringVar()
        org_sid_entry = ttk.Entry(main_frame, textvariable=self.org_sid_var, width=20)
        org_sid_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Help label for SID
        help_label = ttk.Label(main_frame, text="(e.g., TEST, CORP, etc.)", 
                              foreground="gray", font=('Arial', 8))
        help_label.grid(row=1, column=2, sticky=tk.W)
        
        # Delay input
        ttk.Label(main_frame, text="Delay (seconds):").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.delay_var = tk.StringVar(value="2.0")
        delay_entry = ttk.Entry(main_frame, textvariable=self.delay_var, width=10)
        delay_entry.grid(row=2, column=1, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        # Output file selection
        ttk.Label(main_frame, text="Output File:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        file_frame.columnconfigure(0, weight=1)
        
        self.output_file_var = tk.StringVar(value="org_members.csv")
        file_entry = ttk.Entry(file_frame, textvariable=self.output_file_var)
        file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        browse_button.grid(row=0, column=1)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 0))
        options_frame.columnconfigure(0, weight=1)
        
        self.save_debug_var = tk.BooleanVar(value=True)
        debug_check = ttk.Checkbutton(options_frame, text="Save debug pages", 
                                     variable=self.save_debug_var)
        debug_check.grid(row=0, column=0, sticky=tk.W)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.StringVar(value="Ready to scrape")
        progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        progress_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Control buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=(20, 0))
        
        self.start_button = ttk.Button(button_frame, text="Start Scraping", 
                                      command=self.start_scraping, style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stop", 
                                     command=self.stop_scraping, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_button = ttk.Button(button_frame, text="Clear Log", command=self.clear_log)
        clear_button.pack(side=tk.LEFT)
        
        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main_frame row weights
        main_frame.rowconfigure(7, weight=1)
        
    def browse_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialvalue=self.output_file_var.get()
        )
        if filename:
            self.output_file_var.set(filename)
    
    def log_message(self, message):
        """Thread-safe logging to the text widget"""
        def _log():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            self.root.update_idletasks()
        
        if threading.current_thread() == threading.main_thread():
            _log()
        else:
            self.root.after(0, _log)
    
    def update_progress(self, message):
        """Thread-safe progress update"""
        def _update():
            self.progress_var.set(message)
        
        if threading.current_thread() == threading.main_thread():
            _update()
        else:
            self.root.after(0, _update)
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def start_scraping(self):
        # Validate inputs
        if not self.org_sid_var.get().strip():
            messagebox.showerror("Error", "Please enter an organization SID")
            return
        
        try:
            delay = float(self.delay_var.get())
            if delay < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid delay (positive number)")
            return
        
        if not self.output_file_var.get().strip():
            messagebox.showerror("Error", "Please specify an output file")
            return
        
        # Start scraping in a separate thread
        self.is_scraping = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_bar.start()
        
        self.scraping_thread = threading.Thread(target=self.scrape_worker, daemon=True)
        self.scraping_thread.start()
    
    def stop_scraping(self):
        self.is_scraping = False
        self.log_message("Stopping scraper...")
        self.update_progress("Stopping...")
    
    def scraping_finished(self, success, message):
        """Called when scraping is complete"""
        def _finish():
            self.is_scraping = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress_bar.stop()
            
            if success:
                self.update_progress("Scraping completed successfully!")
                messagebox.showinfo("Success", message)
            else:
                self.update_progress("Scraping failed")
                messagebox.showerror("Error", message)
        
        self.root.after(0, _finish)
    
    def scrape_worker(self):
        """The main scraping logic running in a separate thread"""
        try:
            org_sid = self.org_sid_var.get().strip()
            delay = float(self.delay_var.get())
            output_file = self.output_file_var.get().strip()
            
            self.log_message(f"Starting to scrape organization: {org_sid}")
            self.log_message(f"Using delay: {delay} seconds between requests")
            self.update_progress(f"Scraping {org_sid}...")
            
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
                self.log_message(f"Connecting to {members_url}...")
                response = session.get(members_url)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                error_msg = f"Could not access organization page: {e}"
                self.log_message(f"Error: {error_msg}")
                self.scraping_finished(False, error_msg)
                return
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if org exists
            if "The page you were looking for doesn't exist" in response.text:
                error_msg = f"Organization '{org_sid}' not found."
                self.log_message(f"Error: {error_msg}")
                self.scraping_finished(False, error_msg)
                return
            
            # Try to get member count
            try:
                member_count_element = soup.select_one(".or-members-info")
                if member_count_element:
                    member_count_text = member_count_element.get_text().strip()
                    match = re.search(r'Members\s*\((\d+)\)', member_count_text)
                    if match:
                        member_count = int(match.group(1))
                        self.log_message(f"Found {member_count} members in organization.")
                    else:
                        self.log_message("Could not parse member count. Continuing anyway.")
                        member_count = None
                else:
                    self.log_message("Member count element not found. Continuing anyway.")
                    member_count = None
            except Exception as e:
                self.log_message(f"Error getting member count: {e}")
                member_count = None
            
            # Initialize list to store members
            all_members = []
            page = 1
            
            # Create debug directory if enabled
            if self.save_debug_var.get():
                debug_dir = "debug_pages"
                os.makedirs(debug_dir, exist_ok=True)
            
            # Loop through pages until no more members are found
            while self.is_scraping:
                self.log_message(f"Scraping page {page}...")
                self.update_progress(f"Scraping page {page}...")
                
                # Construct URL for current page
                page_url = f"{members_url}?page={page}"
                
                try:
                    # Get the page
                    response = session.get(page_url)
                    response.raise_for_status()
                    
                    # Save debug copy of the HTML if enabled
                    if self.save_debug_var.get():
                        with open(os.path.join(debug_dir, f"page_{page}.html"), "w", encoding="utf-8") as f:
                            f.write(response.text)
                    
                    # Parse the HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find all member items
                    member_elements = soup.select(".member-item")
                    
                    if not member_elements:
                        self.log_message(f"No members found on page {page}. Stopping.")
                        break
                    
                    self.log_message(f"Found {len(member_elements)} members on page {page}.")
                    
                    # Process each member
                    for i, member in enumerate(member_elements):
                        if not self.is_scraping:
                            break
                            
                        try:
                            # Extract member data
                            handle_elem = member.select_one(".nick")
                            rank_elem = member.select_one(".rank")
                            join_date_elem = member.select_one(".join-date")
                            
                            # Extract text content safely
                            handle = handle_elem.get_text().strip() if handle_elem else "Unknown"
                            rank = rank_elem.get_text().strip() if rank_elem else "Unknown"
                            join_date = join_date_elem.get_text().strip() if join_date_elem else "Unknown"
                            
                            # Get profile URL
                            profile_url = ""
                            profile_elem = member.select_one("a")
                            if profile_elem and profile_elem.has_attr('href'):
                                profile_url = "https://robertsspaceindustries.com" + profile_elem['href']
                                
                                # Extract handle from URL if possible
                                citizen_handle = handle  # Default to displayed handle
                                
                                # Try to extract handle from URL
                                url_parts = profile_url.split('/')
                                if len(url_parts) > 4 and url_parts[-2] == "citizens":
                                    citizen_handle = url_parts[-1]
                            
                            # Print progress
                            self.log_message(f"  {i+1}/{len(member_elements)}: {handle} ({rank})")
                            
                            # Now try to get affiliated orgs
                            affiliated_orgs = []
                            
                            if profile_url and self.is_scraping:
                                try:
                                    # Construct the correct URL for the organizations page
                                    orgs_url = f"https://robertsspaceindustries.com/en/citizens/{citizen_handle}/organizations"
                                    
                                    self.log_message(f"    Getting affiliations for {handle}...")
                                    
                                    # Visit organizations page
                                    orgs_response = session.get(orgs_url)
                                    orgs_response.raise_for_status()
                                    
                                    # Save debug copy if enabled
                                    if self.save_debug_var.get():
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
                                                
                                                # Also try to get org URL and extract SID from it
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
                                                self.log_message(f"    Error parsing affiliated org: {e}")
                                        
                                        self.log_message(f"    Found {len(affiliated_orgs)} affiliated orgs")
                                    else:
                                        self.log_message("    No organizations found or private profile")
                                    
                                except Exception as e:
                                    self.log_message(f"    Error getting affiliated orgs: {e}")
                            
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
                            if self.is_scraping:
                                time.sleep(delay)
                            
                        except Exception as e:
                            self.log_message(f"  Error processing member: {e}")
                    
                    if not self.is_scraping:
                        break
                    
                    # Go to next page
                    page += 1
                    
                    # Wait between page requests
                    time.sleep(delay)
                    
                except Exception as e:
                    self.log_message(f"Error scraping page {page}: {e}")
                    break
            
            # Save results if we have any members
            if all_members and self.is_scraping:
                self.log_message("Saving results to CSV...")
                self.update_progress("Saving results...")
                
                # Save to CSV with only SID data for affiliated organizations
                with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                    # Define column headers
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
                
                success_msg = f"Saved {len(all_members)} members to {output_file}"
                self.log_message(success_msg)
                self.log_message("Each row contains a member with up to 5 affiliated organization SIDs.")
                
                self.scraping_finished(True, success_msg)
            elif not self.is_scraping:
                self.log_message("Scraping was stopped by user.")
                self.scraping_finished(False, "Scraping was stopped by user.")
            else:
                error_msg = "No members found or error occurred."
                self.log_message(error_msg)
                self.scraping_finished(False, error_msg)
                
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log_message(f"Error: {error_msg}")
            self.scraping_finished(False, error_msg)

def main():
    root = tk.Tk()
    app = StarCitizenScraperGUI(root)
    
    # Handle window closing
    def on_closing():
        if app.is_scraping:
            if messagebox.askokcancel("Quit", "Scraping is in progress. Do you want to quit?"):
                app.stop_scraping()
                root.after(1000, root.destroy)  # Give time for cleanup
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()