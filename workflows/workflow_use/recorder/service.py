import asyncio
import json
import pathlib
import platform
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from playwright.async_api import BrowserContext, async_playwright

# Assuming views.py is correctly located for this import path
from workflow_use.recorder.views import (
    HttpRecordingStoppedEvent,
    HttpWorkflowUpdateEvent,
    RecorderEvent,
    WorkflowDefinitionSchema,  # This is the expected output type
)

# Path Configuration (should be identical to recorder.py if run from the same context)
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
EXT_DIR = SCRIPT_DIR.parent.parent.parent / "extension" / ".output" / "chrome-mv3"
USER_DATA_DIR = SCRIPT_DIR / "user_data_dir"


class RecordingService:
    def __init__(self):
        self.event_queue: asyncio.Queue[RecorderEvent] = asyncio.Queue()
        self.last_workflow_update_event: Optional[HttpWorkflowUpdateEvent] = None
        self.playwright_context: Optional[BrowserContext] = None

        self.final_workflow_output: Optional[WorkflowDefinitionSchema] = None
        self.recording_complete_event = asyncio.Event()
        self.final_workflow_processed_lock = asyncio.Lock()
        self.final_workflow_processed_flag = False

        self.app = FastAPI(title="Temporary Recording Event Server")
        self.app.add_api_route(
            "/event", self._handle_event_post, methods=["POST"], status_code=202
        )
        # -- DEBUGGING --
        # Turn this on to debug requests
        # @self.app.middleware("http")
        # async def log_requests(request: Request, call_next):
        #     print(f"[Debug] Incoming request: {request.method} {request.url}")
        #     try:
        #         # Read request body
        #         body = await request.body()
        #         print(f"[Debug] Request body: {body.decode('utf-8', errors='replace')}")
        #         response = await call_next(request)
        #         print(f"[Debug] Response status: {response.status_code}")
        #         return response
        #     except Exception as e:
        #         print(f"[Error] Error processing request: {str(e)}")

        self.uvicorn_server_instance: Optional[uvicorn.Server] = None
        self.server_task: Optional[asyncio.Task] = None
        self.playwright_task: Optional[asyncio.Task] = None
        self.event_processor_task: Optional[asyncio.Task] = None

    async def _handle_event_post(self, event_data: RecorderEvent):
        if isinstance(event_data, HttpWorkflowUpdateEvent):
            self.last_workflow_update_event = event_data
        await self.event_queue.put(event_data)
        return {"status": "accepted", "message": "Event queued for processing"}

    async def _process_event_queue(self):
        print("[Service] Event processing task started.")
        try:
            while True:
                event = await self.event_queue.get()
                print(f"[Service] Event Received: {event.type}")
                if isinstance(event, HttpWorkflowUpdateEvent):
                    # self.last_workflow_update_event is already updated in _handle_event_post
                    pass
                elif isinstance(event, HttpRecordingStoppedEvent):
                    print(
                        "[Service] RecordingStoppedEvent received, processing final workflow..."
                    )
                    await self._capture_and_signal_final_workflow(
                        "RecordingStoppedEvent"
                    )
                self.event_queue.task_done()
        except asyncio.CancelledError:
            print("[Service] Event processing task cancelled.")
        except Exception as e:
            print(f"[Service] Error in event processing task: {e}")

    async def _capture_and_signal_final_workflow(self, trigger_reason: str):
        processed_this_call = False
        async with self.final_workflow_processed_lock:
            if (
                not self.final_workflow_processed_flag
                and self.last_workflow_update_event
            ):
                print(
                    f"[Service] Capturing final workflow (Trigger: {trigger_reason})."
                )
                self.final_workflow_output = self.last_workflow_update_event.payload
                self.final_workflow_processed_flag = True
                processed_this_call = True

        if processed_this_call:
            print(
                "[Service] Final workflow captured. Setting recording_complete_event."
            )
            self.recording_complete_event.set()  # Signal completion to the main method

            # If processing was due to RecordingStoppedEvent, also try to close the browser
            if trigger_reason == "RecordingStoppedEvent" and self.playwright_context:
                print(
                    "[Service] Attempting to close Playwright browser due to RecordingStoppedEvent..."
                )
                try:
                    await self.playwright_context.close()
                    print("[Service] Playwright browser close command issued.")
                except Exception as e_close:
                    print(
                        f"[Service] Error closing Playwright browser on recording stop: {e_close}"
                    )

    async def _launch_playwright_and_wait(self):
        print(f"[Service] Attempting to load extension from: {EXT_DIR}")
        if not EXT_DIR.exists() or not EXT_DIR.is_dir():
            print(f"[Service] ERROR: Extension directory not found: {EXT_DIR}")
            self.recording_complete_event.set()  # Signal failure
            return

        # Get Chrome executable path and user data directory based on operating system
        chrome_paths = {
            "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
            "Windows": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
            "Linux": "/usr/bin/google-chrome"  # Linux
        }
        
        # Chrome user data directories (existing profiles)
        chrome_user_data_dirs = {
            "Darwin": pathlib.Path.home() / "Library/Application Support/Google/Chrome",  # macOS
            "Windows": pathlib.Path.home() / "AppData/Local/Google/Chrome/User Data",  # Windows
            "Linux": pathlib.Path.home() / ".config/google-chrome"  # Linux
        }
        
        system = platform.system()
        chrome_path = chrome_paths.get(system)
        chrome_user_data_dir = chrome_user_data_dirs.get(system)
        
        if not chrome_path:
            print(f"[Service] WARNING: Unsupported operating system: {system}. Falling back to Chromium.")
            chrome_path = None
            chrome_user_data_dir = None

        # Use existing Chrome profile if available, otherwise create a clean session
        if chrome_user_data_dir and chrome_user_data_dir.exists():
            user_data_path = str(chrome_user_data_dir.resolve())
            print(f"[Service] Using existing Chrome profile: {user_data_path}")
        else:
            # Fallback to clean session if user profile not found
            USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            user_data_path = str(USER_DATA_DIR.resolve())
            print(f"[Service] Chrome profile not found, using clean session: {user_data_path}")

        async with async_playwright() as p:
            try:
                launch_args = [
                    f"--disable-extensions-except={str(EXT_DIR.resolve())}",
                    f"--load-extension={str(EXT_DIR.resolve())}",
                    "--disable-infobars",  # Remove info bars including automation message
                    "--disable-dev-shm-usage",  # Improve stability
                    "--disable-web-security",  # Allow extension to work with existing profile
                    "--disable-features=VizDisplayCompositor",  # Improve compatibility
                    "--no-first-run",  # Skip first run experience
                    "--no-default-browser-check",  # Skip default browser check
                    "--disable-default-apps",  # Disable default apps
                    "--disable-popup-blocking",  # Allow popups for workflow recording
                ]
                
                if chrome_path:
                    print(f"[Service] Launching Chrome from: {chrome_path}")
                    self.playwright_context = await p.chromium.launch_persistent_context(
                        user_data_path,
                        headless=False,
                        no_viewport=True,
                        executable_path=chrome_path,  # Use Chrome instead of Chromium
                        args=launch_args,
                        ignore_default_args=["--enable-automation", "--no-sandbox"],  # Remove automation flag and sandbox warning
                        user_agent=None,  # Use default user agent (not automation user agent)
                        extra_http_headers=None,  # Use normal headers
                    )
                else:
                    print("[Service] Launching Chromium (fallback)")
                    self.playwright_context = await p.chromium.launch_persistent_context(
                        user_data_path,
                        headless=False,
                        no_viewport=True,
                        args=launch_args,
                    )
                
                print(
                    "[Service] Browser launched successfully. Waiting for close or recording stop..."
                )
                await self.playwright_context.wait_for_event("close", timeout=0)
                print("[Service] Browser context 'close' event detected.")
            except asyncio.CancelledError:
                print("[Service] Playwright task cancelled.")
                if self.playwright_context:
                    try:
                        await self.playwright_context.close()
                    except:
                        pass  # Best effort
                raise  # Re-raise to be caught by gather
            except Exception as e:
                print(f"[Service] Error in Playwright task: {e}")
            finally:
                print("[Service] Playwright task finalization.")
                self.playwright_context = None
                # This call ensures that if browser is closed manually, we still try to capture.
                await self._capture_and_signal_final_workflow("PlaywrightTaskEnded")

    async def capture_workflow(self) -> Optional[WorkflowDefinitionSchema]:
        print("[Service] Starting capture_workflow session...")
        # Reset state for this session
        self.last_workflow_update_event = None
        self.final_workflow_output = None
        self.recording_complete_event.clear()
        self.final_workflow_processed_flag = False

        # Start background tasks
        self.event_processor_task = asyncio.create_task(self._process_event_queue())
        self.playwright_task = asyncio.create_task(self._launch_playwright_and_wait())

        # Configure and start Uvicorn server
        config = uvicorn.Config(
            self.app, host="127.0.0.1", port=7331, log_level="warning", loop="asyncio"
        )
        self.uvicorn_server_instance = uvicorn.Server(config)
        self.server_task = asyncio.create_task(self.uvicorn_server_instance.serve())
        print("[Service] Uvicorn server task started.")

        try:
            print("[Service] Waiting for recording to complete...")
            await self.recording_complete_event.wait()
            print("[Service] Recording complete event received. Proceeding to cleanup.")
        except asyncio.CancelledError:
            print("[Service] capture_workflow task was cancelled externally.")
        finally:
            print("[Service] Starting cleanup phase...")

            # 1. Stop Uvicorn server
            if (
                self.uvicorn_server_instance
                and self.server_task
                and not self.server_task.done()
            ):
                print("[Service] Signaling Uvicorn server to shut down...")
                self.uvicorn_server_instance.should_exit = True
                try:
                    await asyncio.wait_for(
                        self.server_task, timeout=5
                    )  # Give server time to shut down
                except asyncio.TimeoutError:
                    print(
                        "[Service] Uvicorn server shutdown timed out. Cancelling task."
                    )
                    self.server_task.cancel()
                except (
                    asyncio.CancelledError
                ):  # If capture_workflow itself was cancelled
                    pass
                except Exception as e_server_shutdown:
                    print(
                        f"[Service] Error during Uvicorn server shutdown: {e_server_shutdown}"
                    )

            # 2. Stop Playwright task (and ensure browser is closed)
            if self.playwright_task and not self.playwright_task.done():
                print("[Service] Cancelling Playwright task...")
                self.playwright_task.cancel()
                try:
                    await self.playwright_task
                except asyncio.CancelledError:
                    pass
                except Exception as e_pw_cancel:
                    print(
                        f"[Service] Error awaiting cancelled Playwright task: {e_pw_cancel}"
                    )

            if self.playwright_context:  # Final check to close context if still open
                print("[Service] Ensuring Playwright context is closed in cleanup...")
                try:
                    await self.playwright_context.close()
                except Exception as e_pc_close:
                    print(
                        f"[Service] Error closing context in final cleanup: {e_pc_close}"
                    )
                self.playwright_context = None

            # 3. Stop event processor task
            if self.event_processor_task and not self.event_processor_task.done():
                print("[Service] Cancelling event processor task...")
                self.event_processor_task.cancel()
                try:
                    await self.event_processor_task
                except asyncio.CancelledError:
                    pass
                except Exception as e_ep_cancel:
                    print(
                        f"[Service] Error awaiting cancelled event processor task: {e_ep_cancel}"
                    )

            print("[Service] Cleanup phase complete.")

        if self.final_workflow_output:
            print("[Service] Returning captured workflow.")
        else:
            print("[Service] No workflow captured or an error occurred.")
        return self.final_workflow_output


async def main_service_runner():  # Example of how to run the service
    service = RecordingService()
    workflow_data = await service.capture_workflow()
    if workflow_data:
        print("\n--- CAPTURED WORKFLOW DATA (from main_service_runner) ---")
        # Assuming WorkflowDefinitionSchema has model_dump_json or similar
        try:
            print(workflow_data.model_dump_json(indent=2))
        except AttributeError:
            print(
                json.dumps(workflow_data, indent=2)
            )  # Fallback for plain dicts if model_dump_json not present
        print("-----------------------------------------------------")
    else:
        print("No workflow data was captured by the service.")


if __name__ == "__main__":
    # This allows running service.py directly for testing
    try:
        asyncio.run(main_service_runner())
    except KeyboardInterrupt:
        print("Service runner interrupted by user.")
