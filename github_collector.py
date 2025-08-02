import requests
import json
import time
from datetime import datetime
import os

class GitHubDonationCollector:
    def __init__(self):
        # Use environment variable for API URL, fallback to localhost for local testing
        self.base_url = os.getenv('API_BASE_URL', 'http://localhost:5000')
        self.total_raised_file = "total_raised.json"
        self.donations_file = "donations.json"
        self.known_donation_ids = set()
        
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
            response = requests.get(f"{self.base_url}/total_raised", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching total raised: {e}")
            return None
    
    def get_donations(self):
        """Fetch donations list"""
        try:
            response = requests.get(f"{self.base_url}/donations", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching donations: {e}")
            return None
    
    def update_total_raised(self, total_data):
        """Update total raised file with current data"""
        if not total_data:
            return False
            
        amount = float(total_data.get("total_raised", 0))
        timestamp = int(time.time() * 1000)
        
        update_data = {
            "amount": amount,
            "timestamp": timestamp,
            "last_updated": datetime.utcnow().isoformat() + 'Z'
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
        
        # Keep only last 100 updates to prevent file from growing too large
        if len(updates) > 100:
            updates = updates[-100:]
        
        # Save back to file
        with open(self.total_raised_file, 'w') as f:
            json.dump(updates, f, indent=2)
        
        print(f"💰 Updated total raised: ${amount:,.2f}")
        return True
    
    def update_donations(self, donations_data):
        """Update donations file with new donations"""
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
                    "currency": donation.get("currency"),
                    "recorded_at": datetime.utcnow().isoformat() + 'Z'
                }
                
                new_donations.append(donation_record)
                existing_donations.append(donation_record)
                self.known_donation_ids.add(donation_id)
        
        if new_donations or not existing_donations:
            # Sort existing donations by completed_at (newest first)
            existing_donations.sort(key=lambda x: x.get('completed_at', ''), reverse=True)
            
            # Save updated donations list
            with open(self.donations_file, 'w') as f:
                json.dump(existing_donations, f, indent=2)
            
            if new_donations:
                print(f"🎉 Found {len(new_donations)} new donation(s)!")
                for donation in new_donations:
                    amount = donation.get('amount', 'Unknown')
                    donor = donation.get('donor_name', 'Anonymous')
                    print(f"  💝 ${amount} from {donor}")
                    if donation.get('donor_comment'):
                        comment = donation['donor_comment'][:100]
                        print(f"     💬 \"{comment}{'...' if len(donation.get('donor_comment', '')) > 100 else ''}\"")
            else:
                print("📊 Refreshed donations data (no new donations)")
            
            return True
        
        print("✅ No new donations found")
        return False
    
    def run_update(self):
        """Run a single update cycle - perfect for hourly GitHub Actions"""
        print(f"🚀 Starting donation data update at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"📊 API Base URL: {self.base_url}")
        print("-" * 60)
        
        has_changes = False
        
        try:
            # Fetch and update donations
            print("📥 Fetching donations...")
            donations_data = self.get_donations()
            if donations_data:
                if self.update_donations(donations_data):
                    has_changes = True
            else:
                print("❌ Failed to fetch donations")
                return False
            
            # Fetch and update total raised
            print("📥 Fetching total raised...")
            total_data = self.get_total_raised()
            if total_data:
                if self.update_total_raised(total_data):
                    has_changes = True
            else:
                print("❌ Failed to fetch total raised")
                return False
            
            print(f"✅ Update completed successfully!")
            print(f"📈 Tracking {len(self.known_donation_ids)} total donations")
            
            if has_changes:
                print("🔄 Changes detected - files will be committed to GitHub")
            else:
                print("📊 No changes detected - repository up to date")
            
            return True
            
        except Exception as e:
            print(f"💥 Error during update: {e}")
            return False

def main():
    collector = GitHubDonationCollector()
    
    # Test API connection first
    print("🔍 Testing API connection...")
    
    total = collector.get_total_raised()
    donations = collector.get_donations()
    
    if not total:
        print("❌ Cannot connect to total_raised API endpoint")
        exit(1)
    
    if not donations:
        print("❌ Cannot connect to donations API endpoint")
        exit(1)
    
    print(f"✅ API connection successful")
    print(f"   Current total: ${float(total.get('total_raised', 0)):,.2f}")
    print(f"   Recent donations: {len(donations)}")
    print()
    
    # Run the update
    success = collector.run_update()
    
    if not success:
        print("❌ Update failed")
        exit(1)
    
    print("\n🎯 Update completed - ready for GitHub commit!")

if __name__ == "__main__":
    main()