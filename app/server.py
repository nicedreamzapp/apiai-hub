from fastapi import FastAPI, Header, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
import os, datetime, subprocess, psutil, pathlib, asyncio, json, glob
from pathlib import Path

# ---- config / env ----
ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

load_dotenv(ROOT / ".env")
API_KEY = os.getenv("MINI_API_KEY", "")

def is_loopback(request: Request) -> bool:
    """Check if request is from localhost"""
    host = request.client.host if request and request.client else ""
    return host in ("127.0.0.1", "::1")

def guard(x_api_key: str | None, request: Request):
    """Auth guard that allows localhost without API key"""
    if is_loopback(request):
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

def get_available_projects():
    """Dynamically find all Xcode projects in Documents"""
    projects = []
    project_files = glob.glob("/Users/matthewmacosko/Documents/**/*.xcodeproj", recursive=True)
    for proj_file in project_files:
        project_dir = str(Path(proj_file).parent)
        project_name = Path(proj_file).stem
        projects.append({"name": project_name, "path": project_dir})
    return projects

# Current project state
current_project = "/Users/matthewmacosko/Documents/project 601"

# Dynamic Project Configuration Classes
class ProjectConfig:
    def __init__(self, project_path):
        self.project_path = project_path
        self.project_name = os.path.basename(project_path)
        self._xcodeproj_path = None
        self._scheme = None
        self._bundle_id = None
        self._target = None
        
    @property
    def xcodeproj_path(self):
        if self._xcodeproj_path is None:
            self._xcodeproj_path = self._find_xcodeproj()
        return self._xcodeproj_path
    
    @property
    def xcodeproj_name(self):
        if self.xcodeproj_path:
            return os.path.basename(self.xcodeproj_path)
        return None
    
    @property
    def scheme(self):
        if self._scheme is None:
            self._scheme = self._get_default_scheme()
        return self._scheme
    
    @property
    def target(self):
        if self._target is None:
            self._target = self._get_main_target()
        return self._target
    
    @property
    def bundle_id(self):
        if self._bundle_id is None:
            self._bundle_id = self._get_bundle_id()
        return self._bundle_id
    
    def _find_xcodeproj(self):
        """Find the .xcodeproj file in the project directory"""
        try:
            for item in os.listdir(self.project_path):
                if item.endswith('.xcodeproj'):
                    return os.path.join(self.project_path, item)
        except OSError:
            pass
        return None
    
    def _get_default_scheme(self):
        """Get the default scheme for the project"""
        if not self.xcodeproj_path:
            return None
        
        try:
            result = subprocess.run([
                'xcodebuild', '-list', '-project', self.xcodeproj_path
            ], capture_output=True, text=True, cwd=self.project_path)
            
            print(f"DEBUG: Scheme detection - return code: {result.returncode}")
            print(f"DEBUG: Full xcodebuild output for scheme:")
            print(f"'{result.stdout}'")
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                in_schemes = False
                for i, line in enumerate(lines):
                    print(f"Line {i}: '{line}' (stripped: '{line.strip()}')")
                    if line.strip() == "Schemes:":
                        in_schemes = True
                        print(f"Found Schemes section at line {i}")
                        continue
                    elif in_schemes and line.strip():
                        # If line starts with spaces, it's likely a scheme name
                        if line.startswith('        ') or line.startswith('\t'):
                            scheme_name = line.strip()
                            print(f"Found scheme: '{scheme_name}'")
                            return scheme_name
                        else:
                            # We've left the schemes section
                            break
                            
        except Exception as e:
            print(f"Error getting scheme: {e}")
        
        # Fallback: if this is the RealTime Ai Cam project, we know the scheme
        if "project 601" in self.project_path:
            print("Using hardcoded scheme for project 601")
            return "project 601"
        elif "Vision Builder" in self.project_path:
            print("Using hardcoded scheme for Vision Builder")
            return "Vision Builder"
        
        return None
    
    def _get_main_target(self):
        """Get the main app target (not test targets)"""
        if not self.xcodeproj_path:
            return None
        
        try:
            result = subprocess.run([
                'xcodebuild', '-list', '-project', self.xcodeproj_path
            ], capture_output=True, text=True, cwd=self.project_path)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                in_targets = False
                for line in lines:
                    line = line.strip()
                    if line == "Targets:":
                        in_targets = True
                        continue
                    elif in_targets and line and not line.startswith(' '):
                        break
                    elif in_targets and line:
                        # Return first target that doesn't end with "Tests"
                        if not line.endswith('Tests') and not line.endswith('UITests'):
                            return line
        except Exception as e:
            print(f"Error getting target: {e}")
        
        return None
    
    def _get_bundle_id(self):
        """Get the bundle identifier for the project - FIXED VERSION"""
        if not self.xcodeproj_path or not self.scheme:
            print("No xcodeproj_path or scheme for bundle ID detection")
            return self._get_fallback_bundle_id()
        
        try:
            print(f"DEBUG: Detecting bundle ID for scheme '{self.scheme}' in project '{self.xcodeproj_path}'")
            
            result = subprocess.run([
                'xcodebuild', '-showBuildSettings',
                '-project', self.xcodeproj_path,
                '-scheme', self.scheme
            ], capture_output=True, text=True, cwd=self.project_path)
            
            print(f"DEBUG: Bundle ID detection - return code: {result.returncode}")
            
            if result.returncode == 0:
                print("DEBUG: Searching for PRODUCT_BUNDLE_IDENTIFIER in build settings...")
                
                # Split output into lines and look for the exact pattern
                lines = result.stdout.split('\n')
                found_bundle_ids = []
                
                for i, line in enumerate(lines):
                    # Look for lines that contain PRODUCT_BUNDLE_IDENTIFIER and =
                    if 'PRODUCT_BUNDLE_IDENTIFIER' in line and '=' in line:
                        # Skip the DERIVE_MACCATALYST lines that cause the "NO" issue
                        if 'DERIVE_MACCATALYST_PRODUCT_BUNDLE_IDENTIFIER' in line:
                            print(f"DEBUG: Skipping DERIVE_MACCATALYST line {i}: {line.strip()}")
                            continue
                        
                        # Extract the bundle ID from the line
                        bundle_id_part = line.split('=', 1)[1].strip()
                        print(f"DEBUG: Found PRODUCT_BUNDLE_IDENTIFIER line {i}: {line.strip()}")
                        print(f"DEBUG: Extracted bundle ID: '{bundle_id_part}'")
                        
                        if bundle_id_part and bundle_id_part != "NO":
                            found_bundle_ids.append(bundle_id_part)
                
                # Use the first valid bundle ID found
                if found_bundle_ids:
                    bundle_id = found_bundle_ids[0]
                    print(f"DEBUG: Using bundle ID: '{bundle_id}'")
                    return bundle_id
                else:
                    print("DEBUG: No valid PRODUCT_BUNDLE_IDENTIFIER found in build settings")
            else:
                print(f"DEBUG: xcodebuild failed with code {result.returncode}")
                print(f"DEBUG: stderr: {result.stderr}")
                
        except Exception as e:
            print(f"Error getting bundle ID: {e}")
        
        # Fallback to known bundle IDs
        return self._get_fallback_bundle_id()
    
    def _get_fallback_bundle_id(self):
        """Get fallback bundle ID based on project path"""
        if "project 601" in self.project_path:
            print("Using fallback bundle ID for project 601: B9RA6QH559.project-601")
            return "B9RA6QH559.project-601"
        elif "Vision Builder" in self.project_path:
            print("Using fallback bundle ID for Vision Builder: B9RA6QH559.Vision-Builder")
            return "B9RA6QH559.Vision-Builder"
        
        print("No bundle ID found, returning unknown.bundle.id")
        return "unknown.bundle.id"

def generate_dynamic_jobs(project_config):
    """Generate job definitions based on project configuration"""
    if not project_config.xcodeproj_name:
        return {
            "Project • Error": {
                "icon": "⚠️",
                "color": "#FF3B30",
                "description": "No Xcode project found in current directory",
                "jobs": {
                    "no_project": {
                        "name": "No Project Found",
                        "description": "Please select a directory containing an Xcode project",
                        "instruction": "The current directory doesn't contain a .xcodeproj file. Please switch to a valid Xcode project directory.",
                        "cmd": 'echo "No Xcode project found in current directory"'
                    }
                }
            }
        }
    
    project_display_name = project_config.target or project_config.project_name
    scheme = project_config.scheme or "Unknown"
    bundle_id = project_config.bundle_id
    
    # Ensure bundle_id is never None or empty - use fallback
    if not bundle_id:
        bundle_id = project_config._get_fallback_bundle_id()
    
    print(f"DEBUG: Final job generation values:")
    print(f"  - Project: {project_display_name}")
    print(f"  - Scheme: {scheme}")
    print(f"  - Bundle ID: {bundle_id}")
    print(f"  - Bundle ID type: {type(bundle_id)}")
    print(f"  - Bundle ID repr: {repr(bundle_id)}")
    
    # Validate bundle ID before using it
    if bundle_id == "NO" or bundle_id is None or bundle_id == "":
        print("ERROR: Bundle ID is still 'NO', None, or empty - forcing fallback")
        bundle_id = project_config._get_fallback_bundle_id()
    
    return {
        f"Xcode • {project_display_name}": {
            "icon": "🔨",
            "color": "#007AFF",
            "description": f"Build and deploy your {project_display_name} app",
            "jobs": {
                "xcode_build_install": {
                    "name": "Build & Install on iPhone",
                    "description": "Compile your app and install it directly to your connected iPhone",
                    "instruction": "Make sure your iPhone is connected and unlocked. This builds a Debug version of your app and installs it on your device.",
                    "cmd": f'cd "{project_config.project_path}" && xcodebuild -project "{project_config.xcodeproj_name}" -scheme "{scheme}" -destination \'id=00008120-000230263E44201E\' -configuration Debug build install'
                },
                "xcode_launch": {
                    "name": "Launch on iPhone",
                    "description": "Open your installed app on your iPhone",
                    "instruction": "Your app must already be installed on the device. This will launch it remotely.",
                    "cmd": f'xcrun devicectl device process launch --device 00008120-000230263E44201E {bundle_id}'
                },
                "xcode_build_launch": {
                    "name": "Build & Launch (Complete)",
                    "description": "Build, install, and launch your app in one step",
                    "instruction": "The complete workflow: builds your app, installs it on your iPhone, then launches it automatically.",
                    "cmd": f'cd "{project_config.project_path}" && xcodebuild -project "{project_config.xcodeproj_name}" -scheme "{scheme}" -destination \'id=00008120-000230263E44201E\' -configuration Debug build install && xcrun devicectl device process launch --device 00008120-000230263E44201E {bundle_id}'
                }
            }
        },
        
        "Simulator • Testing": {
            "icon": "📱",
            "color": "#34C759",
            "description": "Test your app in the iOS Simulator",
            "jobs": {
                "sim_build_run": {
                    "name": "Run in Simulator",
                    "description": "Build and run your app in iPhone 16 Simulator",
                    "instruction": "Opens the iOS Simulator and runs your app. Great for quick testing without using your physical device.",
                    "cmd": f'cd "{project_config.project_path}" && xcodebuild -project "{project_config.xcodeproj_name}" -scheme "{scheme}" -destination \'platform=iOS Simulator,name=iPhone 16,OS=18.6\' -configuration Debug build && xcrun simctl launch booted {bundle_id}'
                },
                "sim_reset": {
                    "name": "Reset Simulator",
                    "description": "Clean slate: erase all data from iPhone 16 simulator",
                    "instruction": "This completely wipes the simulator, removing all apps and data. Use when the simulator is acting strange.",
                    "cmd": 'xcrun simctl erase "iPhone 16"'
                },
                "sim_screenshots": {
                    "name": "Take Simulator Screenshots",
                    "description": "Capture screenshots from all running simulators",
                    "instruction": "Automatically takes screenshots of all open simulators and saves them to your Desktop.",
                    "cmd": 'mkdir -p ~/Desktop/Screenshots && xcrun simctl list devices booted | grep -v "Unavailable" | grep iPhone | sed \'s/.*(/\' | sed \'s/).*//\' | xargs -I {} sh -c \'xcrun simctl io {} screenshot ~/Desktop/Screenshots/screenshot-{}-$(date +%Y%m%d-%H%M%S).png\''
                }
            }
        },

        "Quality • Testing": {
            "icon": "🧪",
            "color": "#FF9500",
            "description": "Ensure your code quality and catch bugs early",
            "jobs": {
                "run_tests": {
                    "name": "Run Unit Tests",
                    "description": "Execute all automated tests to verify your code works correctly",
                    "instruction": "Runs all the tests you've written to make sure your app functions properly. Green = good, red = needs fixing.",
                    "cmd": f'cd "{project_config.project_path}" && xcodebuild -project "{project_config.xcodeproj_name}" -scheme "{scheme}" -configuration Debug -destination \'platform=iOS Simulator,name=iPhone 16,OS=18.6\' test'
                },
                "smoke_test": {
                    "name": "Quick Smoke Test",
                    "description": "Fast test to ensure your app builds and launches without crashing",
                    "instruction": "A quick sanity check - builds the app and launches it briefly to make sure nothing is fundamentally broken.",
                    "cmd": f'cd "{project_config.project_path}" && xcodebuild -project "{project_config.xcodeproj_name}" -scheme "{scheme}" -configuration Debug -destination \'platform=iOS Simulator,name=iPhone 16,OS=18.6\' build && xcrun simctl launch booted {bundle_id} && sleep 3 && echo "Smoke test completed - app launched successfully"'
                },
                "test_coverage": {
                    "name": "Code Coverage Report",
                    "description": "See which parts of your code are tested vs untested",
                    "instruction": "Shows you what percentage of your code is covered by tests. Higher coverage = fewer bugs slip through.",
                    "cmd": f'cd "{project_config.project_path}" && xcodebuild -project "{project_config.xcodeproj_name}" -scheme "{scheme}" -configuration Debug -destination \'platform=iOS Simulator,name=iPhone 16,OS=18.6\' test -enableCodeCoverage YES'
                }
            }
        },

        "Code Quality": {
            "icon": "✨",
            "color": "#AF52DE",
            "description": "Keep your code clean, consistent, and professional",
            "jobs": {
                "swiftlint": {
                    "name": "Check Code Style",
                    "description": "Scan your code for style issues and best practices",
                    "instruction": "Reviews your Swift code for common style issues like long lines, spacing problems, or naming conventions.",
                    "cmd": f'cd "{project_config.project_path}" && /opt/homebrew/bin/swiftlint'
                },
                "swiftformat": {
                    "name": "Auto-Format Code",
                    "description": "Automatically fix code formatting issues",
                    "instruction": "Like auto-format in Word, but for code. Fixes indentation, spacing, and other formatting automatically. Install with: brew install swiftformat",
                    "cmd": f'cd "{project_config.project_path}" && /opt/homebrew/bin/swiftformat . --exclude "*/Xcode*.app" --exclude "*/.build" --exclude "*/DerivedData" --exclude "*/Downloads" --swift-version 5.9'
                },
                "code_analysis": {
                    "name": "Static Analysis",
                    "description": "Deep scan for potential bugs and security issues",
                    "instruction": "Uses Xcode's built-in analyzer to find potential bugs, memory leaks, and other issues before they become problems.",
                    "cmd": f'cd "{project_config.project_path}" && xcodebuild -project "{project_config.xcodeproj_name}" -scheme "{scheme}" -configuration Debug analyze'
                }
            }
        },

        "Version Control": {
            "icon": "📦",
            "color": "#FF3B30",
            "description": "Manage your code versions and collaborate safely",
            "jobs": {
                "git_status": {
                    "name": "Check Status",
                    "description": "See what files you've changed and current branch info",
                    "instruction": "Shows you which files are modified, what branch you're on, and recent commits. Like a summary of your recent work.",
                    "cmd": f'cd "{project_config.project_path}" && git status && echo "\\n--- Current Branch ---" && git branch --show-current && echo "\\n--- Recent Commits ---" && git log --oneline -5'
                },
                "git_push": {
                    "name": "Push Changes",
                    "description": "Upload your committed changes to GitHub",
                    "instruction": "Uploads your committed work to your remote repository. Safe operation that only sends your work out.",
                    "cmd": f'cd "{project_config.project_path}" && git push origin $(git branch --show-current)'
                },
                "git_branch": {
                    "name": "Create Feature Branch",
                    "description": "Start a new feature branch for safe development",
                    "instruction": "Creates a new branch so you can work on features without affecting the main code. Like making a copy to experiment with.",
                    "cmd": f'cd "{project_config.project_path}" && echo "Creating branch: feature/$(date +%Y%m%d)" && git checkout -b "feature/$(date +%Y%m%d)"'
                },
                "git_commit_all": {
                    "name": "Save All Changes",
                    "description": "Commit all current changes with timestamp",
                    "instruction": "Saves all your current work with an automatic timestamp message. Like creating a save point in a video game.",
                    "cmd": f'cd "{project_config.project_path}" && git add -A && git commit -m "Automated commit: $(date)"'
                }
            }
        },

        "App Store • Release": {
            "icon": "🚀",
            "color": "#007AFF",
            "description": "Prepare and submit your app to the App Store",
            "jobs": {
                "archive_release": {
                    "name": "Create Release Archive",
                    "description": "Build a release version for App Store submission",
                    "instruction": "Creates the official release build of your app, optimized and ready for the App Store. This is what users will download.",
                    "cmd": f'cd "{project_config.project_path}" && xcodebuild -project "{project_config.xcodeproj_name}" -scheme "{scheme}" -configuration Release -archivePath ~/Desktop/{project_display_name}.xcarchive archive'
                },
                "export_ipa": {
                    "name": "Export App Store Package",
                    "description": "Create the .ipa file for App Store Connect",
                    "instruction": "Converts your archive into the .ipa file that Apple needs for the App Store. You'll upload this file to App Store Connect.",
                    "cmd": f'cd "{project_config.project_path}" && if [ -d ~/Desktop/{project_display_name}.xcarchive ]; then xcodebuild -exportArchive -archivePath ~/Desktop/{project_display_name}.xcarchive -exportPath ~/Desktop/{project_display_name}_Export -exportOptionsPlist ExportOptions.plist; else echo "No archive found. Run \'Create Release Archive\' first."; fi'
                },
                "version_bump": {
                    "name": "Increment Version",
                    "description": "Automatically increase your app's version number",
                    "instruction": "Bumps your build number (like 1.0.1 → 1.0.2). Required each time you submit to the App Store.",
                    "cmd": f'cd "{project_config.project_path}" && agvtool next-version -all && echo "\\nNew version:" && agvtool what-version'
                },
                "validate_archive": {
                    "name": "Validate for App Store",
                    "description": "Check if your app meets App Store requirements",
                    "instruction": "Runs Apple's validation checks on your app to catch issues before submission. Better to find problems now than after waiting for review.",
                    "cmd": f'cd "{project_config.project_path}" && if [ -d ~/Desktop/{project_display_name}.xcarchive ]; then xcrun altool --validate-app -f ~/Desktop/{project_display_name}_Export/*.ipa -t ios --output-format xml; else echo "No archive found. Run \'Create Release Archive\' and \'Export App Store Package\' first."; fi'
                }
            }
        },

        "System Diagnostics": {
            "icon": "🔍",
            "color": "#8E8E93",
            "description": "Debug issues and monitor your development environment",
            "jobs": {
                "device_info": {
                    "name": "List All Devices",
                    "description": "Show connected iPhones, iPads, and simulators",
                    "instruction": "See all devices available for development. Helpful when your device isn't showing up in Xcode.",
                    "cmd": 'xcrun devicectl list devices && echo "\\n--- Available Simulators ---" && xcrun simctl list devices'
                },
                "xcode_info": {
                    "name": "Development Environment",
                    "description": "Display Xcode version, SDKs, and development tools",
                    "instruction": "Shows what version of Xcode you're using and what iOS versions you can target. Helpful for troubleshooting compatibility issues.",
                    "cmd": 'xcodebuild -version && echo "\\n--- Available SDKs ---" && xcodebuild -showsdks && echo "\\n--- Command Line Tools ---" && xcode-select -p'
                },
                "disk_usage": {
                    "name": "Development Storage",
                    "description": "Check disk space used by Xcode and development files",
                    "instruction": "See how much space Xcode files are using. DerivedData and DeviceSupport can get huge over time.",
                    "cmd": f'echo "=== Xcode DerivedData ===" && du -sh ~/Library/Developer/Xcode/DerivedData/* 2>/dev/null | head -10 || echo "No DerivedData found" && echo "\\n=== iOS DeviceSupport ===" && du -sh ~/Library/Developer/Xcode/iOS\\ DeviceSupport/* 2>/dev/null | tail -5 || echo "No DeviceSupport found" && echo "\\n=== Project Size ===" && du -sh "{project_config.project_path}"'
                },
                "system_performance": {
                    "name": "Mac Performance",
                    "description": "Check CPU, memory, and system performance",
                    "instruction": "See how your Mac is performing. High CPU or memory usage can slow down builds and development.",
                    "cmd": 'echo "=== System Performance ===" && top -l 1 -n 10 -o cpu && echo "\\n=== Memory Usage ===" && vm_stat && echo "\\n=== Disk Space ===" && df -h'
                },
                "network_test": {
                    "name": "Network Connectivity",
                    "description": "Test connections to Apple's developer services",
                    "instruction": "Verifies you can reach Apple's servers for App Store, TestFlight, and other services. Run this if uploads are failing.",
                    "cmd": 'echo "=== Testing Apple Services ===" && ping -c 3 developer.apple.com && echo "\\n=== App Store Connect ===" && ping -c 3 appstoreconnect.apple.com && echo "\\n=== TestFlight ===" && curl -I https://testflight.apple.com'
                }
            }
        },

        "Maintenance": {
            "icon": "🧹",
            "color": "#FF9500",
            "description": "Keep your development environment clean and optimized",
            "jobs": {
                "clean_derived": {
                    "name": "Clean Build Cache",
                    "description": "Remove Xcode's cached build data (fixes many issues)",
                    "instruction": "Like clearing your browser cache - removes temporary build files that sometimes cause weird errors. Try this first when builds fail mysteriously.",
                    "cmd": 'rm -rf ~/Library/Developer/Xcode/DerivedData/*'
                },
                "clean_project": {
                    "name": "Clean Project Build",
                    "description": "Clean your specific project's build folder",
                    "instruction": "Cleans just your project's build files, not all of Xcode's cache. Lighter version of Clean Build Cache.",
                    "cmd": f'cd "{project_config.project_path}" && xcodebuild -project "{project_config.xcodeproj_name}" -scheme "{scheme}" clean'
                },
                "update_tools": {
                    "name": "Update Development Tools",
                    "description": "Check for and install updates to command line tools",
                    "instruction": "Updates Xcode's command line tools to the latest version. Can fix compatibility issues and add new features.",
                    "cmd": 'softwareupdate -l | grep "Command Line Tools" && echo "Updates available. Run: softwareupdate -i -a" || echo "Command Line Tools are up to date"'
                },
                "organize_downloads": {
                    "name": "Organize Downloads",
                    "description": "Clean up and organize downloaded Xcode files",
                    "instruction": "Moves old iOS DeviceSupport files and organizes your Downloads folder. Helps free up disk space.",
                    "cmd": 'echo "=== Organizing Downloads ===" && find ~/Downloads -name "*.dmg" -mtime +30 -exec ls -lah {} \\; && echo "\\n=== Old DeviceSupport ===" && find ~/Library/Developer/Xcode/iOS\\ DeviceSupport -type d -mtime +90 | head -5'
                }
            }
        }
    }

# Global job definitions - will be replaced by dynamic generation
JOBS = {}

def update_job_commands():
    """Update job commands based on current project using dynamic configuration"""
    global JOBS, current_project
    
    if not current_project:
        return
    
    try:
        project_config = ProjectConfig(current_project)
        JOBS = generate_dynamic_jobs(project_config)
        print(f"✅ Updated jobs for project: {project_config.project_name}")
        print(f"   - Xcode project: {project_config.xcodeproj_name}")
        print(f"   - Scheme: {project_config.scheme}")
        print(f"   - Target: {project_config.target}")
        print(f"   - Bundle ID: {project_config.bundle_id}")
    except Exception as e:
        print(f"❌ Error updating job commands: {e}")
        # Fallback to generic jobs
        JOBS = {
            "Project • Build": {
                "icon": "🔨",
                "color": "#007AFF",
                "description": "Basic project build commands",
                "jobs": {
                    "generic_build": {
                        "name": "Build Project",
                        "description": "Attempt to build the current project",
                        "instruction": "This will try to build whatever Xcode project is found in the current directory.",
                        "cmd": f'cd "{current_project}" && find . -name "*.xcodeproj" -exec xcodebuild -project {{}} build \\;'
                    }
                }
            }
        }

app = FastAPI(title="APIAI Hub", description="Professional iOS Development Control Panel", version="2.0.0")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")

# Initialize job commands with current project on startup
update_job_commands()

# ---- Project Management Endpoints ----
@app.get("/projects")
def list_projects(request: Request, x_api_key: str | None = Header(None)):
    guard(x_api_key, request)
    projects = get_available_projects()
    return {"projects": projects, "current": current_project}

@app.post("/set-project")
async def set_project(request: Request, x_api_key: str | None = Header(None)):
    guard(x_api_key, request)
    data = await request.json()
    global current_project
    current_project = data["project_path"]
    update_job_commands()  # This will regenerate all job groups with new names
    return {"success": True, "current_project": current_project}

# ---- Health & Stats ----
@app.get("/health")
def health(request: Request, x_api_key: str | None = Header(None)):
    guard(x_api_key, request)
    return {"ok": True, "time": datetime.datetime.now().isoformat(), "service": "APIAI Hub Professional"}

@app.get("/stats")
def stats(request: Request, x_api_key: str | None = Header(None)):
    guard(x_api_key, request)
    vm = psutil.virtual_memory()
    du = psutil.disk_usage("/")
    boot = datetime.datetime.fromtimestamp(psutil.boot_time())
    
    return {
        "cpu": f"{psutil.cpu_percent(interval=0.2):.1f}%",
        "memory": {
            "percent": f"{vm.percent:.1f}%",
            "used": f"{vm.used / (1024**3):.1f}GB",
            "total": f"{vm.total / (1024**3):.1f}GB"
        },
        "disk": {
            "percent": f"{du.percent:.1f}%",
            "free": f"{du.free / (1024**3):.1f}GB",
            "total": f"{du.total / (1024**3):.1f}GB"
        },
        "uptime_sec": int((datetime.datetime.now() - boot).total_seconds()),
    }

@app.get("/jobs")
def list_jobs(request: Request, x_api_key: str | None = Header(None)):
    guard(x_api_key, request)
    update_job_commands()  # Refresh commands with current project
    return JOBS

# ---- Job Execution ----
class RunReq(BaseModel):
    job_name: str

async def run_command_async(job_name: str, command: str, group_name: str):
    """Run command asynchronously and log output - FIXED VERSION"""
    log_file = LOGS_DIR / f"{job_name}.log"
    
    with open(log_file, "w") as log:
        log.write(f"=== {group_name} • {job_name} ===\n")
        log.write(f"Started: {datetime.datetime.now().isoformat()}\n")
        log.write(f"Command: {command}\n")
        log.write("=" * 50 + "\n\n")
        log.flush()
        
        try:
            # FIXED: Pass command directly without nested shell invocation
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                shell=True
            )
            
            async for line in process.stdout:
                decoded_line = line.decode('utf-8')
                log.write(decoded_line)
                log.flush()
            
            await process.wait()
            log.write(f"\n{'='*50}\n")
            log.write(f"Completed: {datetime.datetime.now().isoformat()}\n")
            log.write(f"Exit Code: {process.returncode}\n")
            log.write(f"Status: {'✅ SUCCESS' if process.returncode == 0 else '❌ FAILED'}\n")
            
        except Exception as e:
            log.write(f"\n❌ ERROR: {str(e)}\n")
            log.write(f"Failed: {datetime.datetime.now().isoformat()}\n")

@app.post("/run")
async def run_job_async(req: RunReq, background_tasks: BackgroundTasks, request: Request, x_api_key: str | None = Header(None)):
    guard(x_api_key, request)
    
    # Find job in any group
    job_info = None
    group_name = None
    for group, group_data in JOBS.items():
        if req.job_name in group_data["jobs"]:
            job_info = group_data["jobs"][req.job_name]
            group_name = group
            break
    
    if not job_info:
        raise HTTPException(status_code=404, detail=f"Job '{req.job_name}' not found")
    
    background_tasks.add_task(run_command_async, req.job_name, job_info["cmd"], group_name)
    
    return {
        "status": "started",
        "job_name": req.job_name,
        "group": group_name,
        "message": f"Job '{job_info['name']}' started successfully"
    }

@app.post("/run_sync")
def run_sync(req: RunReq, request: Request, x_api_key: str | None = Header(None)):
    guard(x_api_key, request)
    
    # Find job in any group
    job_info = None
    for group_data in JOBS.values():
        if req.job_name in group_data["jobs"]:
            job_info = group_data["jobs"][req.job_name]
            break
            
    if not job_info:
        raise HTTPException(status_code=404, detail=f"Job '{req.job_name}' not found")
    
    proc = subprocess.run(["/bin/zsh", "-lc", job_info["cmd"]], capture_output=True, text=True, timeout=300)
    
    return {
        "success": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "job_name": req.job_name
    }

@app.get("/logs/{job_name}")
def get_logs(job_name: str, request: Request, x_api_key: str | None = Header(None)):
    guard(x_api_key, request)
    
    log_file = LOGS_DIR / f"{job_name}.log"
    if not log_file.exists():
        return {"error": f"No log file found for job '{job_name}'"}
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Return last 200 lines
            tail_lines = lines[-200:] if len(lines) > 200 else lines
            return {
                "job_name": job_name,
                "log_content": ''.join(tail_lines),
                "total_lines": len(lines)
            }
    except Exception as e:
        return {"error": f"Could not read log file: {str(e)}"}

# ---- UI ----
@app.get("/ui")
def ui_page(request: Request):
    return FileResponse(ROOT / "app" / "static" / "dashboard.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
