from dataclasses import dataclass

import cvxpy as cp

EPS = 1e-6


@dataclass
class User:
    id: str
    name: str

    # score for sociability
    sociability: int


@dataclass
class JMPreference:
    user_id: str
    slot_id: str

    # preference; 1 = most preferred, 5 = least preferred
    value: int


@dataclass
class Slot:
    id: str
    time: str

    # sms assigned to this slot
    sm_list: list[str]


@dataclass
class MatcherConfig:
    min_family_size: int
    max_family_size: int

    sociability_bias: float


def get_optimization(
    jm_users: list[User],
    preferences: list[JMPreference],
    slots: list[Slot],
    config: MatcherConfig,
):
    # map from (user_id, slot_id) => preference
    preference_map = {}
    for preference in preferences:
        preference_map[(preference.user_id, preference.slot_id)] = preference.value

    # variables for assignments
    assignment = {}

    for user in jm_users:
        for slot in slots:
            pref = preference_map.get((user.id, slot.id), 0)
            if pref <= 0:
                assignment[user.id, slot.id] = cp.Constant(0)
            else:
                assignment[user.id, slot.id] = cp.Variable(
                    name=f"{user.id}/{slot.id}", boolean=True
                )

    constraints = []

    # ensure each JM is only assigned to one slot
    for user in jm_users:
        total_assigned = sum(assignment[user.id, slot.id] for slot in slots)
        constraints.append(total_assigned == 1)

    # limit the family size
    for slot in slots:
        total_assigned = sum(assignment[user.id, slot.id] for user in jm_users)
        constraints.extend(
            [
                config.min_family_size <= total_assigned,
                total_assigned <= config.max_family_size,
            ]
        )

    # minimize the total preferences for each user
    objective = sum(
        preference_map[user_id, slot_id] * variable
        for (user_id, slot_id), variable in assignment.items()
        if (user_id, slot_id) in preference_map
    )

    # add a penalty for differences in sociability
    # sociability_difference = 0
    # sociability_constraints = []
    # for slot in slots:
    #     num_assigned = sum(assignment[user.id, slot.id] for user in jm_users)
    #     total_sociability = sum(assignment[user.id, slot.id] * user.sociability for user in jm_users)
    #
    #     average_sociability = cp.Variable()
    #     sociability_constraints.extend([
    #         average_sociability * num_assigned == total_sociability
    #     ])
    #
    #     for user in jm_users:
    #         variable = assignment[user.id, slot.id]
    #         sociability_difference += variable * cp.abs(
    #             user.sociability - average_sociability
    #         )
    #
    # objective += config.sociability_bias * sociability_difference
    # constraints.extend(sociability_constraints)

    return objective, constraints, assignment


def run_matcher(
    jm_users: list[User],
    preferences: list[JMPreference],
    slots: list[Slot],
    config: MatcherConfig,
):
    objective, constraints, assignment = get_optimization(
        jm_users, preferences, slots, config
    )

    slots_by_id = {slot.id: slot for slot in slots}

    # minimization problem (low preferences are better)
    problem = cp.Problem(cp.Minimize(objective), constraints)
    problem.solve(verbose=True)

    # print(problem.value)

    final_assignment = {}

    for user in jm_users:
        matched_slot_ids = set()
        for slot in slots:
            assignment_obj = assignment[user.id, slot.id]
            if isinstance(assignment_obj, cp.Variable) and assignment_obj.value > EPS:
                matched_slot_ids.add(slot.id)

        assert len(matched_slot_ids) == 1
        matched_slot_id = list(matched_slot_ids)[0]
        final_assignment[user.id] = slots_by_id[matched_slot_id]

    return final_assignment
