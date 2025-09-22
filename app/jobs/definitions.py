# All job definitions
JOBS = {
    "Xcode • Vision Builder": {
        "icon": "🔨",
        "color": "#007AFF",
        "description": "Build and deploy your Vision Builder app",
        "jobs": {
            "xcode_build_install": {
                "name": "Build & Install on iPhone",
                "description": "Compile your app and install it directly to your connected iPhone",
                "instruction": "Make sure your iPhone is connected and unlocked. This builds a Debug version of your app and installs it on your device.",
                "estimated_time": "2-3 minutes",
                "cmd": '''cd "/Users/matthewmacosko/Documents/Vision Builder" && xcodebuild -project "Vision Builder.xcodeproj" -scheme "Vision Builder" -destination 'id=00008120-000230263E44201E' -configuration Debug build install'''
            }
        }
    }
}
