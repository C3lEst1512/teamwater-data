import requests
import json
import time
from datetime import datetime
import os

class DonationMonitor:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.total_raised_file = "total_raised.json"
        self.donations_file = "donations.json"
        self.last_total = None
        self.known_donation_ids = set()
        self.last_check_time = None
        
        # Load existing data
        self.load_existing_data()
    
    def load_existing_data(self):
        """Load existing donation IDs to avoid duplicates"""
        if os.path.exists(self.donations_file):
            try:
                with open(self.donations_file, 'r') as f:
                    existing_donations = json.load(f)
                    self.known_donation_ids = {donation.get('id') for donation in existing_donations if 'id' in donation}
                    print(f"Loaded {len(self.known_donation_ids)} existing donation IDs")
            except (json.JSONDecodeError, FileNotFoundError):
                self.known_donation_ids = set()
    
    def get_total_raised(self):
        """Fetch total raised amount"""
        try:
            response = requests.get(f"{self.base_url}/total_raised", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching total raised: {e}")
            return None
    
    def get_donations(self):
        """Fetch donations list"""
        try:
            response = requests.get(f"{self.base_url}/donations", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching donations: {e}")
            return None
    
    def save_total_raised_update(self, total_data):
        """Save total raised update when there's a new donation"""
        amount = float(total_data.get("total_raised", 0))
        timestamp = int(time.time() * 1000)  # Current timestamp in milliseconds
        
        update_data = {
            "amount": amount,
            "timestamp": timestamp
        }
        
        # Load existing updates or create new list
        updates = []
        if os.path.exists(self.total_raised_file):
            try:
                with open(self.total_raised_file, 'r') as f:
                    updates = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                updates = []
        
        # Add new update
        updates.append(update_data)
        
        # Save back to file
        with open(self.total_raised_file, 'w') as f:
            json.dump(updates, f, indent=2)
        
        print(f"💰 Total raised update: ${amount:,.2f} at {datetime.fromtimestamp(timestamp/1000).strftime('%H:%M:%S')}")
    
    def save_new_donations(self, donations_data):
        """Save new donations to file"""
        if not donations_data:
            return False
        
        # Load existing donations
        existing_donations = []
        if os.path.exists(self.donations_file):
            try:
                with open(self.donations_file, 'r') as f:
                    existing_donations = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_donations = []
        
        new_donations = []
        for donation in donations_data:
            donation_id = donation.get('id')
            if donation_id and donation_id not in self.known_donation_ids:
                # Extract required fields
                donation_record = {
                    "id": donation_id,
                    "amount": donation.get("amount"),
                    "completed_at": donation.get("completed_at"),
                    "donor_name": donation.get("donor_name"),
                    "donor_comment": donation.get("donor_comment"),
                    "currency": donation.get("currency")
                }
                
                new_donations.append(donation_record)
                existing_donations.append(donation_record)
                self.known_donation_ids.add(donation_id)
        
        if new_donations:
            # Sort existing donations by completed_at (newest first)
            existing_donations.sort(key=lambda x: x.get('completed_at', ''), reverse=True)
            
            # Save updated donations list
            with open(self.donations_file, 'w') as f:
                json.dump(existing_donations, f, indent=2)
            
            print(f"🎉 Found {len(new_donations)} new donation(s)!")
            for donation in new_donations:
                completed_time = donation['completed_at']
                if completed_time:
                    # Parse and format the timestamp
                    try:
                        dt = datetime.fromisoformat(completed_time.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M:%S')
                    except:
                        time_str = completed_time
                else:
                    time_str = "Unknown time"
                
                print(f"  💝 ${donation['amount']} from {donation['donor_name']} at {time_str}")
                if donation.get('donor_comment'):
                    print(f"     💬 \"{donation['donor_comment'][:100]}{'...' if len(donation.get('donor_comment', '')) > 100 else ''}\"")
            
            return True
        return False
    
    def monitor(self, interval=1):
        """Main monitoring loop - now checking every second"""
        print("🚀 Starting high-frequency donation monitor...")
        print(f"⏱️  Checking every {interval} second(s) to catch all donations")
        print("📊 Monitoring endpoints:")
        print(f"   • Total raised: {self.base_url}/total_raised")
        print(f"   • Donations: {self.base_url}/donations")
        print("⚠️  Note: API returns only 10 most recent donations")
        print("🛑 Press Ctrl+C to stop")
        print("-" * 60)
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            while True:
                start_time = time.time()
                
                try:
                    # Check for new donations first
                    donations_data = self.get_donations()
                    new_donations_found = False
                    
                    if donations_data:
                        new_donations_found = self.save_new_donations(donations_data)
                        consecutive_errors = 0  # Reset error counter on success
                        
                        # Print current status every 10 seconds if no new donations
                        current_time = time.time()
                        if (self.last_check_time is None or 
                            current_time - self.last_check_time >= 10) and not new_donations_found:
                            print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Monitoring... (Tracking {len(self.known_donation_ids)} donations)")
                            self.last_check_time = current_time
                    
                    # Check total raised and save if there are new donations
                    total_data = self.get_total_raised()
                    if total_data and new_donations_found:
                        current_total = float(total_data.get("total_raised", 0))
                        if self.last_total is None or current_total != self.last_total:
                            self.save_total_raised_update(total_data)
                            self.last_total = current_total
                
                except Exception as e:
                    consecutive_errors += 1
                    print(f"❌ Error during check #{consecutive_errors}: {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"🚨 Too many consecutive errors ({max_consecutive_errors}). Pausing for 5 seconds...")
                        time.sleep(5)
                        consecutive_errors = 0
                
                # Calculate how long to sleep to maintain exact interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    print(f"⚠️  Warning: Check took {elapsed:.2f}s (longer than {interval}s interval)")
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            print(f"📈 Final stats: Tracked {len(self.known_donation_ids)} unique donations")
        except Exception as e:
            print(f"💥 Unexpected error: {e}")

def main():
    monitor = DonationMonitor()
    
    # Test connection first
    print("🔍 Testing API connection...")
    total = monitor.get_total_raised()
    donations = monitor.get_donations()
    
    if total:
        print(f"✅ Total raised API working: ${float(total.get('total_raised', 0)):,.2f}")
    else:
        print("❌ Total raised API not responding")
        return
    
    if donations:
        print(f"✅ Donations API working: Found {len(donations)} recent donations")
    else:
        print("❌ Donations API not responding")
        return
    
    print()
    
    # Start continuous monitoring with 1-second intervals
    monitor.monitor(interval=1)

if __name__ == "__main__":
    main()
