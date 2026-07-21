import json
import unittest

from controller import CalibrationProfile, Controller, GestureObservation


class ControllerTests(unittest.TestCase):
    def test_calibration_round_trip(self):
        profile = CalibrationProfile(handedness="left", dwell_ms=200)
        self.assertEqual(CalibrationProfile.from_json(profile.to_json()), profile)

    def test_debounce_and_pause(self):
        now = [0.0]
        controller = Controller(CalibrationProfile(dwell_ms=100, debounce_ms=500), clock=lambda: now[0])
        controller.resume()
        observation = lambda: GestureObservation("next", 0.9, timestamp=now[0])
        self.assertIsNone(controller.observe(observation()))
        now[0] = 0.11
        self.assertEqual(controller.observe(observation()), "next")
        self.assertEqual(controller.snapshot()["command"], {"id": 1, "name": "next"})
        now[0] = 0.2
        self.assertIsNone(controller.observe(observation()))
        controller.pause()
        now[0] = 1
        self.assertIsNone(controller.observe(observation()))

    def test_invalid_calibration_is_rejected(self):
        with self.assertRaises(ValueError):
            CalibrationProfile.from_json(json.dumps({"confidence_threshold": 0.1}))

    def test_manual_commands_share_the_bounded_browser_channel(self):
        controller = Controller()
        controller.execute("previous")
        self.assertEqual(controller.snapshot()["command"], {"id": 1, "name": "previous"})
        with self.assertRaises(ValueError):
            controller.execute("open-terminal")


if __name__ == "__main__":
    unittest.main()
