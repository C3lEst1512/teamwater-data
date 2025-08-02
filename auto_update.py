import os
import time
import subprocess
import shutil
from datetime import datetime
import schedule

class AutoGitUpdater:
    def __init__(self):
        self.repo_url = "https://github.com/C3lest1512/teamwater-data.git"
        self.repo_name = "teamwater-data"
        self.collector_script = "github_collector.py"
        
    def run_command(self, command, cwd=None):
        """Run a command and return success/failure"""
        try:
            result = subprocess.run(command, shell=True, cwd=cwd, 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"✅ Success: {command}")
                return True
            else:
                print(f"❌ Error: {command}")
                print(f"   Output: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout: {command}")
            return False
        except Exception as e:
            print(f"💥 Exception: {command} - {e}")
            return False
    
    def cleanup_existing_repo(self):
        """Remove existing repo folder if it exists"""
        if os.path.exists(self.repo_name):
            try:
                shutil.rmtree(self.repo_name)
                print(f"🧹 Cleaned up existing {self.repo_name} folder")
            except Exception as e:
                print(f"⚠️  Warning: Could not remove {self.repo_name}: {e}")
    
    def update_data(self):
        """Main update function that runs every hour"""
        print("\n" + "="*60)
        print(f"🚀 Starting update at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        try:
            # Step 1: Clean up any existing repo
            self.cleanup_existing_repo()
            
            # Step 2: Clone the repository
            print("📥 Cloning repository...")
            if not self.run_command(f"git clone {self.repo_url}"):
                print("❌ Failed to clone repository")
                return False
            
            # Step 3: Run the collector script
            print("🔄 Running donation collector...")
            if not self.run_command(f"python ../{self.collector_script}", cwd=self.repo_name):
                print("❌ Failed to run collector script")
                return False
            
            # Step 4: Add all changes
            print("📝 Adding changes to git...")
            if not self.run_command("git add .", cwd=self.repo_name):
                print("❌ Failed to add changes")
                return False
            
            # Step 5: Check if there are changes to commit
            result = subprocess.run("git diff --staged --quiet", shell=True, cwd=self.repo_name)
            if result.returncode == 0:
                print("📊 No changes detected - repository is up to date")
                self.cleanup_existing_repo()
                return True
            
            # Step 6: Commit changes
            commit_msg = f"Auto-update donations: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            print(f"💾 Committing changes: {commit_msg}")
            if not self.run_command(f'git commit -m "{commit_msg}"', cwd=self.repo_name):
                print("❌ Failed to commit changes")
                return False
            
            # Step 7: Push to GitHub
            print("🚀 Pushing to GitHub...")
            if not self.run_command("git push", cwd=self.repo_name):
                print("❌ Failed to push to GitHub")
                return False
            
            print("🎉 Update completed successfully!")
            
            # Step 8: Cleanup
            self.cleanup_existing_repo()
            return True
            
        except Exception as e:
            print(f"💥 Unexpected error: {e}")
            self.cleanup_existing_repo()
            return False
    
    def run_scheduler(self):
        """Run the hourly scheduler"""
        print("🕐 Starting hourly donation update scheduler...")
        print("⏱️  Updates will run every hour at minute 0")
        print("🛑 Press Ctrl+C to stop")
        print(f"📁 Make sure {self.collector_script} is in the same folder as this script")
        print("-" * 60)
        
        # Check if collector script exists
        if not os.path.exists(self.collector_script):
            print(f"❌ Error: {self.collector_script} not found in current directory")
            print("📁 Please place the collector script in the same folder and try again")
            return
        
        # Schedule the job to run every hour
        schedule.every().hour.at(":00").do(self.update_data)
        
        # Also run immediately for testing
        print("🧪 Running initial update for testing...")
        self.update_data()
        
        # Main scheduler loop
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped by user")
        except Exception as e:
            print(f"\n💥 Scheduler error: {e}")

def main():
    # Check if git is available
    try:
        subprocess.run("git --version", shell=True, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("❌ Git is not installed or not available in PATH")
        print("📥 Please install Git first: https://git-scm.com/downloads")
        return
    
    # Check if Python requests is available
    try:
        import requests
    except ImportError:
        print("❌ 'requests' library not found")
        print("📦 Please install it: pip install requests")
        return
    
    updater = AutoGitUpdater()
    updater.run_scheduler()

if __name__ == "__main__":
    main()
