#!/usr/bin/env python3
import os
import subprocess
import rumps

APP_LABEL = "com.local.dictate"
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictate.log")


def _launchctl(cmd: str) -> str:
    try:
        out = subprocess.check_output(["launchctl", cmd, APP_LABEL], stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="ignore").strip()
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        return str(e)


def _status() -> bool:
    try:
        out = subprocess.check_output(["launchctl", "list"], stderr=subprocess.STDOUT).decode("utf-8", errors="ignore")
        return APP_LABEL in out
    except Exception:
        return False


class DictateMenu(rumps.App):
    def __init__(self):
        super(DictateMenu, self).__init__("🎤", title="Dictation")
        self.menu = [
            rumps.MenuItem("Start", callback=self.start_service),
            rumps.MenuItem("Stop", callback=self.stop_service),
            rumps.MenuItem("Restart", callback=self.restart_service),
            None,
            rumps.MenuItem("Open Log", callback=self.open_log),
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]
        self.icon = None
        rumps.notifications._clear()
        rumps.Timer(self.refresh_title, 2).start()

    def refresh_title(self, _=None):
        running = _status()
        self.title = "🎤" if running else "❌"

    def start_service(self, _):
        _launchctl("start")
        self.refresh_title()

    def stop_service(self, _):
        _launchctl("stop")
        self.refresh_title()

    def restart_service(self, _):
        subprocess.call(["launchctl", "unload", os.path.expanduser("~/Library/LaunchAgents/%s.plist" % APP_LABEL)])
        subprocess.call(["launchctl", "load", os.path.expanduser("~/Library/LaunchAgents/%s.plist" % APP_LABEL)])
        subprocess.call(["launchctl", "start", APP_LABEL])
        self.refresh_title()

    def open_log(self, _):
        try:
            subprocess.Popen(["open", LOG_PATH])
        except Exception:
            pass

    def quit_app(self, _):
        rumps.quit_application()


if __name__ == '__main__':
    DictateMenu().run()


