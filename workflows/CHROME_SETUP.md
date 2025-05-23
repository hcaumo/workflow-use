# Chrome Browser Configuration

This project has been configured to use **Google Chrome** instead of **Chromium** by default. **Chrome will now open with your existing profile** (bookmarks, extensions, saved passwords, etc.) and **behave like a normal browser** without showing "Chrome is being controlled by automated test software".

## What Changed

The following files have been modified to use Chrome with your existing profile:

1. **`workflow_use/browser_config.py`** - New configuration module with profile support and anti-detection
2. **`cli.py`** - Updated to use Chrome browser
3. **`backend/service.py`** - Updated to use Chrome browser  
4. **`workflow_use/workflow/service.py`** - Updated to use Chrome by default
5. **`workflow_use/recorder/service.py`** - Updated to use Chrome with your existing profile and normal behavior

## Browser Configuration

The `browser_config.py` module provides several functions:

- `get_chrome_browser()` - Returns a Browser instance configured to use Chrome (clean session)
- `get_chrome_browser_with_profile()` - Returns a Browser instance that uses your existing Chrome profile
- `get_chrome_browser(use_existing_profile=True)` - Same as above with parameter
- `get_default_browser()` - Returns a Browser instance using the default Chromium

### Chrome Profile Locations by Operating System

- **macOS**: `~/Library/Application Support/Google/Chrome`
- **Windows**: `~/AppData/Local/Google/Chrome/User Data`
- **Linux**: `~/.config/google-chrome`

## Normal Browser Behavior

Chrome is configured to behave exactly like a normal browser:

- ✅ **No automation detection** - No "Chrome is being controlled by automated test software" message
- ✅ **Normal user agent** - Websites see Chrome as a regular browser
- ✅ **Standard headers** - All HTTP requests appear normal
- ✅ **Full functionality** - All Chrome features work normally
- ✅ **Website compatibility** - Sites that block automation tools will work normally

### Anti-Detection Features

The configuration includes these Chrome arguments to ensure normal behavior:

- `--disable-blink-features=AutomationControlled` - Removes automation detection
- `--disable-infobars` - Removes automation info bars
- `--ignore-default-args=["--enable-automation"]` - Removes automation flags
- `--no-first-run` - Skips first-run experience
- `--no-default-browser-check` - Skips default browser prompts

## Profile Usage

### Recording Workflows (`create-workflow`)
- ✅ **Uses your existing Chrome profile automatically**
- ✅ **Behaves like normal Chrome** - no automation warnings
- ✅ **Access to your bookmarks, extensions, saved passwords**
- ✅ **Familiar environment for recording workflows**
- ✅ **All your Chrome settings and customizations**
- ✅ **Websites work normally** - no automation blocking

### Running Workflows
- ✅ Uses Chrome with optimized settings for automation
- ✅ Still uses Chrome executable but may use clean session for reliability

## Configuration Options

The Chrome browser is configured with:

- `headless=False` - Runs in visible mode so you can see what's happening
- `disable_security=True` - Disabled for existing profile compatibility
- `browser_binary_path` - Points to your Chrome installation
- **Profile Detection** - Automatically finds and uses your existing Chrome profile
- **Anti-Detection** - Configured to avoid automation detection by websites

## Benefits of Using Your Chrome Profile

- **🏠 Familiar Environment**: Use Chrome exactly as you have it configured
- **🔖 Your Bookmarks**: Access all your saved bookmarks during recording
- **🧩 Your Extensions**: All your Chrome extensions work during recording
- **🔐 Saved Passwords**: Auto-fill works with your saved credentials
- **⚙️ Your Settings**: All your Chrome preferences and customizations
- **🎨 Your Theme**: Chrome appears with your chosen theme and layout
- **🌐 Normal Browsing**: No automation warnings or website blocking
- **🛡️ Stealth Mode**: Websites can't detect that it's automated

## Automatic Fallback

If your Chrome profile is not found, the system will automatically:
1. Fall back to creating a clean Chrome session
2. If Chrome is not available, fall back to Chromium
3. Display clear messages about what's happening

## All Commands Now Use Chrome

All workflow-use commands will now use Chrome:

- ✅ `python3 cli.py create-workflow` - Opens Chrome **with your profile** and **normal behavior**
- ✅ `python3 cli.py run-workflow` - Uses Chrome for execution  
- ✅ `python3 cli.py run-as-tool` - Uses Chrome for execution
- ✅ `python3 cli.py launch-gui` - Backend uses Chrome for workflows

## Switching Back to Chromium

If you want to use Chromium instead of Chrome, you can:

1. **Option 1**: Modify the imports in the files to use `get_default_browser()` instead of `get_chrome_browser()`

2. **Option 2**: Change the browser configuration in your code:
   ```python
   from workflow_use.browser_config import get_default_browser
   browser = get_default_browser()
   ```

3. **Option 3**: Use the Browser class directly:
   ```python
   from browser_use import Browser
   browser = Browser()  # Uses Chromium by default
   ```

4. **Option 4**: For RecordingService, comment out the `executable_path=chrome_path` line in `recorder/service.py`

## Troubleshooting

If you encounter issues:

1. **Chrome not found**: Make sure Chrome is installed in the default location
2. **Permission errors**: Ensure Chrome has necessary permissions
3. **Profile conflicts**: If Chrome is already running, close it before starting recording
4. **Extension issues**: Some extensions might interfere with recording
5. **Recording issues**: The RecordingService will fall back to clean session if profile loading fails
6. **Automation detected**: If websites still detect automation, check Chrome version compatibility

### Common Solutions

- **Close existing Chrome windows** before running `create-workflow`
- **Disable problematic extensions** temporarily if recording fails
- **Check Chrome permissions** for accessibility and automation
- **Update Chrome** to latest version for best compatibility
- **Restart Chrome** if automation detection persists

For any issues, you can always fall back to Chromium by using `get_default_browser()` instead of `get_chrome_browser()`. 