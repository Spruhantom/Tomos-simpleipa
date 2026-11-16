import unittest
from simpleipa.planner import build_plan, ConfigurationError

class PlannerTests(unittest.TestCase):
    def test_default_server_profile(self):
        plan = build_plan({"role": "server", "platform": "rocky"})
        self.assertIn("users_and_groups", plan.features)
        self.assertIn("sudo_rules", plan.features)

    def test_ssh_keys_adds_user_dependency(self):
        plan = build_plan({"role": "server", "platform": "almalinux",
                           "features": ["ssh_keys"]})
        self.assertIn("users_and_groups", plan.features)

    def test_rejects_wrong_platform(self):
        with self.assertRaises(ConfigurationError):
            build_plan({"role": "server", "platform": "ubuntu"})

    def test_rejects_unknown_feature(self):
        with self.assertRaises(ConfigurationError):
            build_plan({"role": "server", "platform": "rocky",
                        "features": ["made_up"]})

    def test_rejects_role_incompatible_feature(self):
        with self.assertRaises(ConfigurationError):
            build_plan({"role": "client", "platform": "ubuntu",
                        "features": ["dns"]})

if __name__ == "__main__":
    unittest.main()
