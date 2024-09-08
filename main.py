import csv
import random
import re
from pprint import pprint

from matcher import JMPreference, MatcherConfig, Slot, User, run_matcher

JM_PREFERENCE_FILE = "jm_preferences.csv"
SM_PREFERENCE_FILE = "sm_preferences.csv"

SHORT_OUT = "output_short.csv"
LONG_OUT = "output_long.csv"

# JM PREFERENCES
JM_FIRST_NAME_COLUMN = "First name"
JM_LAST_NAME_COLUMN = "Last name"
JM_ROLE_COLUMN = "For which position are you accepting/rejecting?"
JM_ROLE_CHECK = "Junior Mentor"
JM_SOCIAL_COLUMN = "How much time would you like to spend within your family focusing on teaching improvement vs being more social?"

# SM PREFERENCES
SM_TIME_COLUMN = "Time"


def parse_sm_slots() -> list[Slot]:
    slots = []
    next_id = 0
    with open(SM_PREFERENCE_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            time = row[SM_TIME_COLUMN]
            sms = [
                val.strip() for key, val in row.items() if "sm" in key.lower().split()
            ]

            slots.append(Slot(id=str(next_id), time=time, sm_list=sms))

            next_id += 1

    return slots


def parse_jm_preferences(slots: list[Slot]) -> tuple[list[User], list[JMPreference]]:
    users = []
    preferences = []

    slots_by_time = {}
    for slot in slots:
        if slot.time not in slots_by_time:
            slots_by_time[slot.time] = []
        slots_by_time[slot.time].append(slot)

    slots_preference_check = {time: False for time in slots_by_time}

    with open(JM_PREFERENCE_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row[JM_ROLE_COLUMN] != JM_ROLE_CHECK:
                continue

            first_name = row[JM_FIRST_NAME_COLUMN].strip()
            last_name = row[JM_LAST_NAME_COLUMN].strip()
            name = f"{first_name} {last_name}"

            cur_user = User(id=name, name=name, sociability=int(row[JM_SOCIAL_COLUMN]))

            for key, val in row.items():
                if "[" in key and "]" in key:
                    # detected as a preference column
                    time = re.findall(r"\[([^\]]+)\]", key)
                    assert len(time) == 1
                    time = time[0]

                    time_slots = slots_by_time.get(time, [])

                    if time in slots_preference_check:
                        slots_preference_check[time] = True

                    for slot in time_slots:
                        preferences.append(
                            JMPreference(
                                user_id=cur_user.id, slot_id=slot.id, value=int(val)
                            )
                        )

            users.append(cur_user)

    assert all(val for val in slots_preference_check.values())

    return users, preferences


def main():
    slots = parse_sm_slots()
    users, preferences = parse_jm_preferences(slots)

    random.shuffle(users)
    random.shuffle(preferences)

    config = MatcherConfig(min_family_size=3, max_family_size=6, sociability_bias=1)

    matching = run_matcher(users, preferences, slots, config)

    users_by_id = {user.id: user for user in users}
    slots_by_id = {slot.id: slot for slot in slots}
    preference_map = {}
    for preference in preferences:
        preference_map[(preference.user_id, preference.slot_id)] = preference.value

    max_sms = max(len(slot.sm_list) for slot in slots)

    matching_by_slot: dict[str, list[User]] = {}
    for user_id, slot in matching.items():
        user = users_by_id[user_id]
        if slot.id not in matching_by_slot:
            matching_by_slot[slot.id] = []
        matching_by_slot[slot.id].append(user)

    max_jms = max(len(users) for users in matching_by_slot.values())

    rows = []
    for slot_id in sorted(matching_by_slot.keys()):
        users = sorted(matching_by_slot[slot_id], key=lambda u: u.id)
        slot = slots_by_id[slot_id]
        user_names = [user.name for user in users]

        padded_sm_list = slot.sm_list + [""] * (max_sms - len(slot.sm_list))
        padded_jm_list = user_names + [""] * (max_jms - len(user_names))
        rows.append([*padded_sm_list, *padded_jm_list])

    header = [f"SM {i+1}" for i in range(max_sms)] + [
        f"JM {i+1}" for i in range(max_jms)
    ]

    with open(SHORT_OUT, "w", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    rows = []
    for slot_id in sorted(matching_by_slot.keys()):
        users = sorted(matching_by_slot[slot_id], key=lambda u: u.id)
        slot = slots_by_id[slot_id]
        padded_sm_list = slot.sm_list + [""] * (max_sms - len(slot.sm_list))

        for user in users:
            rows.append([*padded_sm_list, user.name, preference_map[user.id, slot_id], user.sociability])

    header = [f"SM {i+1}" for i in range(max_sms)] + ["JM", "Preference", "Sociability"]
    with open(LONG_OUT, "w", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None, help="Random seed to use")

    args = parser.parse_args()

    seed = args.seed
    if args.seed is None:
        seed = random.randint(0, int(1e6))
    print(f"Using seed: {seed}\n")
    random.seed(seed)

    main()
