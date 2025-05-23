"""Browser configuration for workflow-use."""
import platform
from pathlib import Path
from browser_use import Browser, BrowserConfig


def get_chrome_browser(use_existing_profile: bool = False) -> Browser:
    """Create a Browser instance configured to use Chrome instead of Chromium.
    
    Args:
        use_existing_profile: If True, uses your existing Chrome profile with bookmarks, 
                            extensions, etc. If False, creates a clean session.
    """
    
    # Define Chrome paths for different operating systems
    chrome_paths = {
        "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        "Windows": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
        "Linux": "/usr/bin/google-chrome"  # Linux
    }
    
    system = platform.system()
    chrome_path = chrome_paths.get(system)
    
    if not chrome_path:
        raise ValueError(f"Unsupported operating system: {system}")
    
    # Configure extra arguments for Chrome
    extra_args = [
        "--disable-infobars",  # Remove info bars including automation message
        "--disable-dev-shm-usage",  # Improve stability
        "--no-first-run",  # Skip first run experience
        "--no-default-browser-check",  # Skip default browser check
        "--disable-default-apps",  # Disable default apps
    ]
    
    if use_existing_profile:
        # Add arguments that help with existing profile compatibility
        extra_args.extend([
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding"
        ])
    
    # Create browser config with Chrome path
    config = BrowserConfig(
        browser_binary_path=chrome_path,
        headless=False,  # Run in non-headless mode so you can see what's happening
        disable_security=use_existing_profile,  # Disable security when using existing profile
        extra_browser_args=extra_args,
        # You can add more configuration options here as needed
    )
    
    return Browser(config=config)


def get_chrome_browser_with_profile() -> Browser:
    """Create a Chrome browser instance that uses your existing Chrome profile."""
    return get_chrome_browser(use_existing_profile=True)


def get_default_browser() -> Browser:
    """Get the default browser configuration (Chromium)."""
    return Browser() 