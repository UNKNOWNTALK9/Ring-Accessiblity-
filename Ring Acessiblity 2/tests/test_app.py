import os, tempfile, unittest
os.environ["DATABASE_PATH"] = os.path.join(tempfile.gettempdir(), "ring_accessible_alert_test.db")
os.environ["RING_MODE"] = "demo"
import tests, app as application

class RingAccessibleAlertTests(unittest.TestCase):
    def setUp(self):
        application.app.config["TESTING"] = True
        self.client = application.app.test_client()
        with application.db() as con:
            con.execute("DELETE FROM events")

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["status"], "ok")

    def test_demo_event_persists(self):
        r = self.client.post("/api/events/demo", json={"event_type":"doorbell_pressed"})
        self.assertEqual(r.status_code, 201)
        event_id = r.json["event"]["id"]
        listing = self.client.get("/api/events")
        self.assertTrue(any(e["id"] == event_id for e in listing.json))

    def test_invalid_event_rejected(self):
        r = self.client.post("/api/events/demo", json={"event_type":"unrecognized"})
        self.assertEqual(r.status_code, 400)

    def test_acknowledge_event(self):
        created = self.client.post("/api/events/demo", json={"event_type":"person_detected"}).json["event"]
        r = self.client.patch(f"/api/events/{created['id']}/acknowledge", json={})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["acknowledged"], 1)

    def test_settings_persist(self):
        r = self.client.put("/api/settings", json={"high_contrast":True,"alert_duration":20})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.client.get("/api/settings").json["high_contrast"])
        self.assertEqual(self.client.get("/api/settings").json["alert_duration"], 20)

    def test_rule_creation(self):
        r = self.client.post("/api/rules", json={"name":"Test rule","event_type":"doorbell_pressed","actions":["visual","history"]})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json["name"], "Test rule")

if __name__ == "__main__":
    unittest.main()
