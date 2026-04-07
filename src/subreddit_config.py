"""
Candidate subreddits organized by domain, and per-sub posting configuration.
"""

import json
import os

SUB_DOMAINS = {
    "Defense / Aerospace": [
        "defenseindustry",
        "AerospaceEngineering",
        "defense",
    ],
    "FAANG / Big Tech": [
        "cscareerquestions",
        "leetcode",
        "codinginterview",
        "ExperiencedDevs",
    ],
    "Embedded / Robotics": [
        "embedded",
        "robotics",
        "ROS",
        "cpp",
    ],
    "AI / ML": [
        "artificial",
        "MachineLearning",
        "autonomousVehicles",
    ],
    "General Engineering": [
        "AskEngineers",
        "engineering",
    ],
    "Job Hunting": [
        "jobs",
        "careerguidance",
        "resumes",
        "interviews",
    ],
}

# Flat list of all candidate subs (all domains combined)
CANDIDATE_SUBS = []
for subs in SUB_DOMAINS.values():
    CANDIDATE_SUBS.extend(subs)

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


def get_subs_for_domains(selected_domains):
    """Return list of subreddits for the selected domains."""
    subs = []
    for domain in selected_domains:
        subs.extend(SUB_DOMAINS.get(domain, []))
    # Deduplicate while preserving order
    seen = set()
    result = []
    for s in subs:
        if s.lower() not in seen:
            seen.add(s.lower())
            result.append(s)
    return result


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
