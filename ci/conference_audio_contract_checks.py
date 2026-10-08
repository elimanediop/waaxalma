"""Static regression checks for Waaxalma conference audio wiring."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "streamlit" / "assets" / "js"
HTML = ROOT / "streamlit" / "assets" / "html"

class ConferenceAudioContractTests(unittest.TestCase):
    def test_reference_device_storage_key(self):
        direct = (JS / "realtime_client.1.js").read_text(encoding="utf-8")
        enhanced = (JS / "realtime_enhanced_client.1.js").read_text(encoding="utf-8")
        for source in (direct, enhanced):
            self.assertIn("waaxalma.conferenceInputDeviceId", source)
            self.assertIn("attachConferenceReference", source)
            self.assertIn("setReferenceStream", source)

    def test_independent_conference_monitor(self):
        source = (JS / "conference_monitor_selector.1.js").read_text(encoding="utf-8")
        self.assertIn("waaxalma.conferenceMonitorEnabled", source)
        self.assertIn("waaxalma.conferenceMonitorOutputDeviceId", source)
        self.assertIn("waaxalma.conferenceInputDeviceId", source)
        self.assertNotIn("fullDuplexController", source)
        self.assertIn("stopMonitoring", source)
        self.assertTrue((HTML / "conference_monitor_selector.html").is_file())

    def test_streamlit_wiring(self):
        app = (ROOT / "streamlit" / "streamlit_app.py").read_text(encoding="utf-8")
        assets = (ROOT / "streamlit" / "ui" / "assets.py").read_text(encoding="utf-8")
        self.assertIn("load_conference_monitor_selector", app)
        self.assertIn("def load_conference_monitor_selector", assets)

if __name__ == "__main__":
    unittest.main()
