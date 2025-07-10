# startup.py - WebExtract Pro Complete System Startup (Fixed for webapp.py)
import subprocess
import time
import os
import sys
import threading
from pathlib import Path

def print_banner():
    """Print startup banner"""
    print("=" * 60)
    print("🚀 WEBEXTRACT PRO - PROFESSIONAL WEB SCRAPING PLATFORM")
    print("=" * 60)
    print("📊 Main Dashboard: http://127.0.0.1:8000")
    print("🛒 Kilimall Worker: http://127.0.0.1:5001") 
    print("🛍️ Jumia Worker: http://127.0.0.1:5000")
    print("👤 Admin Login: admin@webextract-pro.com / admin123")
    print("=" * 60)
    print()

def check_dependencies():
    """Check if required files exist"""
    required_files = [
        'shared_db.py',
        'webapp.py',  # Changed from parent_app.py to webapp.py
        'workers/kilimall/kilimall_worker.py',
        'workers/jumia/jumia_worker.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nPlease ensure all files are in the correct directories.")
        return False
    
    return True

def start_service(service_name, script_path, port, cwd=None):
    """Start a service in a separate process"""
    try:
        print(f"🚀 Starting {service_name}...")
        
        # Use sys.executable to get the current Python interpreter
        process = subprocess.Popen(
            [sys.executable, script_path],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Give service time to start
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            print(f"✅ {service_name} started successfully on port {port}")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ {service_name} failed to start:")
            print(f"   stdout: {stdout}")
            print(f"   stderr: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting {service_name}: {str(e)}")
        return None

def monitor_services(processes):
    """Monitor running services"""
    print("\n🔍 Monitoring services... (Press Ctrl+C to stop all)")
    
    try:
        while True:
            time.sleep(10)
            
            # Check if any process has died
            for name, process in processes.items():
                if process and process.poll() is not None:
                    print(f"⚠️ {name} has stopped unexpectedly")
                    
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
        
        for name, process in processes.items():
            if process and process.poll() is None:
                print(f"🔄 Stopping {name}...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                    print(f"✅ {name} stopped successfully")
                except subprocess.TimeoutExpired:
                    print(f"⚠️ Force killing {name}...")
                    process.kill()
        
        print("✅ All services stopped")

def main():
    """Main startup function"""
    print_banner()
    
    # Check if we're in the right directory
    if not Path('shared_db.py').exists():
        print("❌ Please run this script from the WebExtract Pro root directory")
        print("   (where shared_db.py is located)")
        return
    
    # Check dependencies
    if not check_dependencies():
        return
    
    print("🔧 Starting WebExtract Pro services...\n")
    
    # Store process references
    processes = {}
    
    # Start main webapp (changed from parent_app.py to webapp.py)
    processes['WebApp (Dashboard)'] = start_service(
        "WebApp (Dashboard)", 
        "webapp.py", 
        8000
    )
    
    # Start Kilimall worker
    processes['Kilimall Worker'] = start_service(
        "Kilimall Worker",
        "kilimall_worker.py",
        5001,
        cwd="workers/kilimall"
    )
    
    # Start Jumia worker  
    processes['Jumia Worker'] = start_service(
        "Jumia Worker",
        "jumia_worker.py", 
        5000,
        cwd="workers/jumia"
    )
    
    # Check if all services started
    failed_services = [name for name, process in processes.items() if process is None]
    
    if failed_services:
        print(f"\n❌ Failed to start: {', '.join(failed_services)}")
        print("Please check the error messages above and fix any issues.")
        
        # Stop any services that did start
        for name, process in processes.items():
            if process and process.poll() is None:
                process.terminate()
        return
    
    print("\n✅ All services started successfully!")
    print("\n🌐 Access WebExtract Pro:")
    print("   1. Open http://127.0.0.1:8000 in your browser")
    print("   2. Sign up or use admin@webextract-pro.com / admin123")
    print("   3. Click 'Open Scraper' to use Kilimall or Jumia workers")
    print("   4. Start scraping and monitor progress in real-time!")
    
    # Monitor services
    monitor_services(processes)

if __name__ == '__main__':
    main()