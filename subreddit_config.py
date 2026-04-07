"""
Candidate subreddits and per-sub posting configuration.
"""

import json
import os

CANDIDATE_SUBS = [
    # Career / interviews
    "cscareerquestions",
    "interviews",
    "leetcode",
    "codinginterview",
    "ExperiencedDevs",
    # Defense / aerospace
    "defenseindustry",
    "AerospaceEngineering",
    "defense",
    # C++ / embedded / robotics
    "cpp",
    "embedded",
    "robotics",
    "ROS",
    # General engineering
    "AskEngineers",
    "engineering",
    # Job hunting
    "jobs",
    "careerguidance",
    "resumes",
    # Autonomy / AI
    "artificial",
    "MachineLearning",
    "autonomousVehicles",
]

SUB_CONFIG = {
    "interviews": {"tag": "[Advice]", "min_karma": 50},
    "cscareerquestions": {"tag": None, "min_karma": 0},
    "leetcode": {"tag": None, "min_karma": 0},
    "defenseindustry": {"tag": None, "min_karma": 0},
    "embedded": {"tag": None, "min_karma": 0},
    "cpp": {"tag": None, "min_karma": 0},
    "codinginterview": {"tag": None, "min_karma": 0},
    "ExperiencedDevs": {"tag": None, "min_karma": 0},
    "AerospaceEngineering": {"tag": None, "min_karma": 0},
    "defense": {"tag": None, "min_karma": 0},
    "robotics": {"tag": None, "min_karma": 0},
    "ROS": {"tag": None, "min_karma": 0},
    "AskEngineers": {"tag": None, "min_karma": 0},
    "engineering": {"tag": None, "min_karma": 0},
    "jobs": {"tag": None, "min_karma": 0},
    "careerguidance": {"tag": None, "min_karma": 0},
    "resumes": {"tag": None, "min_karma": 0},
    "artificial": {"tag": None, "min_karma": 0},
    "MachineLearning": {"tag": None, "min_karma": 0},
    "autonomousVehicles": {"tag": None, "min_karma": 0},
}


def get_all_candidate_subs():
    """Return CANDIDATE_SUBS merged with any approved discovered subs."""
    all_subs = list(CANDIDATE_SUBS)
    discovered_file = os.path.join("data", "discovered_subs.json")
    if os.path.exists(discovered_file):
        with open(discovered_file, "r") as f:
            data = json.load(f)
        for sub in data.get("approved", []):
            if sub not in [s.lower() for s in all_subs]:
                all_subs.append(sub)
    return all_subs
