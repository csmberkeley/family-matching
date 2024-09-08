import csv
import sys
from enum import Enum

### HOW TO USE ###
"""
Author: Jason Chang, former 61A Coordinator

This is a script for semi-autonomously matching JMs to families based on preferential data. In theory, 
this script is generalized enough to be used to match any subset of people given a set of constraints, 
but the primary intent of this script is for family matching and thus correct operation to fit other 
scenarios cannot be guaranteed. Before running the script, make sure that your CSVs satisfy all of 
the below assumptions; otherwise, the script is not guaranteed to work properly.

Assumptions before running the script:
- Numbers in sheets must be integers
- Preference and difference constraints must have matching headers and options between SM and JM sheets
  (see sample inputs for JMs and SMs)

Assumptions about SM pair CSV headers:
- SM name headers must be called "SM 1" and "SM 2", respectively
- Aside from the above headers, no other headers contain the string "SM"
- Headers must not contain square brackets

Assumptions about JM CSV headers:
- Name header must be called "Name"
- Headers only contain square brackets to denote options (see sample input for JMs)

Follow the below steps to run the script:
(1) Download the script.
(2) Download CSVs for both JM and SM pair data. (see sample inputs for JMs and SMs)
(3) You may change the variable values in the INPUTS/OUTPUTS section below (it's a bit farther down the script).
    BE CAREFUL NOT TO CHANGE THE VARIABLE NAMES
(4) In Terminal, run python family_matcher.py. Note: This script was written for Python 3.6, so using other
    versions may lead to unintended behavior.
"""


### CONSTRAINTS ###
class Constraint:
    def __init__(self, header):
        self.header = header

    def is_satisfied():
        return False


class PreferenceConstraint(Constraint):
    def __init__(self, header, max_pref):
        super().__init__(header)
        self.max_pref = max_pref
        self.options = []

    def is_satisfied(self, pref):
        return int(pref) <= self.max_pref


class CountConstraint(Constraint):
    def __init__(self, header, value, min_count, max_count):
        super().__init__(header)
        self.value = value
        self.min_count = min_count
        self.max_count = max_count

    def is_match(self, value):
        return value == self.value

    def is_satisfied(self, count):
        return self.min_count <= count and count <= self.max_count

    def can_be_satisfied(self, count, availability):
        return count + availability >= self.min_count


class JMCountConstraint(CountConstraint):
    def __init__(self, min_count, max_count):
        super().__init__("JM Count", "", min_count, max_count)

    def can_be_satisfied(self, count, availability):
        return count + availability == self.max_count


class DifferenceConstraint(Constraint):
    def __init__(self, header, max_diff):
        super().__init__(header)
        self.max_diff = max_diff

    def is_satisfied(self, val1, val2):
        return abs(int(val1) - int(val2)) <= self.max_diff


class Text(Enum):
    NONE = (0,)
    SHORT = (1,)
    FULL = 2


################################################
### SHOULD NOT NEED TO EDIT ABOVE THIS POINT ###
################################################

### INPUTS/OUTPUTS ###

"""
Below are brief descriptions for the types of constraints this script considers.

JMCountConstraint(min_count: int, max_count: int)
- Defines a constraint for how many JMs a family should have
- The following must be true: (# of families) * (jm_count_constraint.max_count) >= (total # of JMs)

PreferenceConstraint(header: string, max_pref: int)
- Defines a constraint to match JMs to the best fit family given preference ratings for some options
- Preference ratings are assumed to be positive integers, where lower numbers indicate higher preference
- max_pref indicates the lowest preference (highest rating) to consider for family matching 
  (i.e. threshold for low preferences that shouldn't be considered)

CountConstraint(header: string, value: string, min_count: int, max_count: int)
- Defines a constraint for how many JMs in a family should have a certain value
- The following must be true: count_constraint.max_count <= jm_count_constraint.max_count

DifferenceConstraint(header: string, max_diff: int)
- Defines a constraint to match JMs to the best fit family given the SM pair value and JM value
- max_diff indicates the maximum difference between the SM pair value and JM value to consider
  (i.e. threshold for high variance matches that shouldn't be considered)
"""

# [Mandatory] Inclusive range for number of JMs per family
jm_count_constraint = JMCountConstraint(4, 5)
# [Optional] Preference constraints
preference_constraints = [
    PreferenceConstraint("Please fill in your family meeting availability", 2)
]
# [Optional] Count constraints
count_constraints = [CountConstraint("Gender", "Female", 2, 3)]
# [Optional] Difference constraints
difference_constraints = [
    DifferenceConstraint("How social do you want your family to be?", 1)
]
# [Mandatory] Relative path to CSV of JM matching data
path_jms = "sample-input-jm.csv"
# [Mandatory] Relative path to CSV of SM matching data
path_sms = "sample-input-sm.csv"
# [Mandatory] Write location for script final output (short)
path_write_short = "./families_out.csv"
# [Mandatory] Write location for script final output (full)
path_write_full = "./families_out_full.csv"
# [Mandatory] Setting for Terminal text output (Text.NONE, Text.SHORT, Text.FULL)
text_output = Text.NONE

################################################
### SHOULD NOT NEED TO EDIT BELOW THIS POINT ###
################################################

### UTILS ###
MAX_ITERS = 100


def is_preference(header):
    return any([c.header in header for c in preference_constraints])


def is_count(header):
    return any([header == c.header for c in count_constraints])


def is_difference(header):
    return any([header == c.header for c in difference_constraints])


def get_constraint(header, constraints):
    for c in constraints:
        if header == c.header:
            return c


def get_preference_header(header):
    return header.split("[")[0][:-1]


def get_preference_option(header):
    return header.split("[")[1][:-1]


### DATA MODELS ###
class DataValue:
    def __init__(self, header, value):
        self.header = header
        self.value = value


class SMs:
    def __init__(self):
        self.sms = []
        self.data = []

    def load_data(self, data):
        for header in data:
            if "SM" in header:
                self.sms.append(data[header])
            elif is_preference(header) or is_count(header) or is_difference(header):
                self.data.append(DataValue(header, data[header]))

    def get_datavalue(self, header):
        for dv in self.data:
            if dv.header == header:
                return dv


class JM:
    def __init__(self, name):
        self.name = name
        self.data = []

    def load_data(self, data):
        for header in data:
            if is_preference(header):
                pref_header = get_preference_header(header)
                pref_option = get_preference_option(header)
                dv = get_datavalue = self.get_datavalue(pref_header)
                if dv:
                    dv.value[pref_option] = data[header]
                else:
                    new_dict = {}
                    new_dict[pref_option] = data[header]
                    new_dv = DataValue(pref_header, new_dict)
                    self.data.append(new_dv)
            elif is_count(header) or is_difference(header):
                self.data.append(DataValue(header, data[header]))

    def get_datavalue(self, header):
        for dv in self.data:
            if dv.header == header:
                return dv


class FamilyStatus(Enum):
    INCOMPLETE = 0
    COMPLETE = 1


class Family:
    def __init__(self):
        self.sms = SMs()
        self.jms = []
        self.status = FamilyStatus.INCOMPLETE

    # Mentor manipulation
    def add_sms(self, data):
        self.sms.load_data(data)

    def add_jm(self, jm):
        try:
            self.jms.append(jm)
            self.update_status()
            return True
        except Exception as e:
            if jm in self.jms:
                self.jms.remove(jm)
            self.update_status()

            print("An error occurred when adding a JM to a family.", e)
            return False

    def swap_jm(self, jm_outgoing, jm_incoming):
        try:
            self.jms.remove(jm_outgoing)
            self.jms.append(jm_incoming)
            self.update_status()
            return True
        except Exception as e:
            if jm_outgoing not in self.jms:
                self.jms.append(jm_outgoing)
            if jm_incoming in self.jms:
                self.jms.remove(jm_incoming)
            self.update_status()
            print("An error occurred when swapping JMs.", e)
            return False

    def remove_jm(self, jm):
        try:
            self.jms.remove(jm)
            self.update_status()
            return True
        except Exception as e:
            if jm not in self.jms:
                self.jms.append(jm)
            self.update_status()
            print("An error occurred when removing a JM from a family.", e)
            return False

    def allow_steal(self, jm):
        without_jm = list(filter(lambda j: j is not jm, self.jms))
        return all(
            [self.jm_steal_check(j, without_jm) for j in without_jm]
        ) and jm_count_constraint.is_satisfied(len(self.jms) - 1)

    def allow_swap(self, jm_outgoing, jm_incoming):
        with_swapped_jms = list(
            map(lambda j: jm_incoming if j is jm_outgoing else j, self.jms)
        )
        return all([self.jm_swap_check(j, with_swapped_jms) for j in with_swapped_jms])

    # Constraint satisfaction
    def jm_steal_check(self, jm, jms):
        compatible = []
        for dv in jm.data:
            sm_dv = self.sms.get_datavalue(dv.header)
            if is_preference(dv.header):
                constraint = get_constraint(dv.header, preference_constraints)
                compatible.append(constraint.is_satisfied(dv.value[sm_dv.value]))
            elif is_count(dv.header):
                constraint = get_constraint(dv.header, count_constraints)
                count = sum(
                    [constraint.is_match(j.get_datavalue(dv.header).value) for j in jms]
                )
                compatible.append(constraint.is_satisfied(count))
            elif is_difference(dv.header):
                constraint = get_constraint(dv.header, difference_constraints)
                compatible.append(constraint.is_satisfied(sm_dv.value, dv.value))
        return all(compatible)

    def jm_swap_check(self, jm, jms):
        compatible = []
        good_family_size = jm_count_constraint.can_be_satisfied(
            len(self.jms), self.get_availability()
        )
        compatible.append(good_family_size)
        for dv in jm.data:
            sm_dv = self.sms.get_datavalue(dv.header)
            if is_preference(dv.header):
                constraint = get_constraint(dv.header, preference_constraints)
                compatible.append(constraint.is_satisfied(dv.value[sm_dv.value]))
            elif is_count(dv.header):
                constraint = get_constraint(dv.header, count_constraints)
                count = sum(
                    [constraint.is_match(j.get_datavalue(dv.header).value) for j in jms]
                )
                if self.status == FamilyStatus.COMPLETE:
                    compatible.append(constraint.is_satisfied(count))
                else:
                    compatible.append(
                        constraint.can_be_satisfied(count, self.get_availability())
                    )
            elif is_difference(dv.header):
                constraint = get_constraint(dv.header, difference_constraints)
                compatible.append(constraint.is_satisfied(sm_dv.value, dv.value))
        return all(compatible)

    def jm_add_check(self, jm):
        compatible = []
        good_family_size = jm_count_constraint.can_be_satisfied(
            len(self.jms) + 1, max(self.get_availability() - 1, 0)
        )
        compatible.append(good_family_size)
        for dv in jm.data:
            sm_dv = self.sms.get_datavalue(dv.header)
            if is_preference(dv.header):
                constraint = get_constraint(dv.header, preference_constraints)
                compatible.append(constraint.is_satisfied(dv.value[sm_dv.value]))
            elif is_count(dv.header):
                constraint = get_constraint(dv.header, count_constraints)
                count = sum(
                    [
                        constraint.is_match(j.get_datavalue(dv.header).value)
                        for j in self.jms
                    ]
                )
                count += constraint.is_match(dv.value)
                compatible.append(
                    constraint.can_be_satisfied(
                        count, max(self.get_availability() - 1, 0)
                    )
                )
            elif is_difference(dv.header):
                constraint = get_constraint(dv.header, difference_constraints)
                compatible.append(constraint.is_satisfied(sm_dv.value, dv.value))
        return all(compatible)

    def full_check(self):
        compatible = []
        compatible.append(jm_count_constraint.is_satisfied(len(self.jms)))
        for jm in self.jms:
            for dv in jm.data:
                sm_dv = self.sms.get_datavalue(dv.header)
                if is_preference(dv.header):
                    constraint = get_constraint(dv.header, preference_constraints)
                    compatible.append(constraint.is_satisfied(dv.value[sm_dv.value]))
                elif is_count(dv.header):
                    constraint = get_constraint(dv.header, count_constraints)
                    count = sum(
                        [
                            constraint.is_match(j.get_datavalue(dv.header).value)
                            for j in self.jms
                        ]
                    )
                    compatible.append(constraint.is_satisfied(count))
                elif is_difference(dv.header):
                    constraint = get_constraint(dv.header, difference_constraints)
                    compatible.append(constraint.is_satisfied(sm_dv.value, dv.value))
        return all(compatible)

    def update_status(self):
        if self.full_check():
            self.status = FamilyStatus.COMPLETE
        else:
            self.status = FamilyStatus.INCOMPLETE

    def get_availability(self):
        return jm_count_constraint.max_count - len(self.jms)

    # Output handlers
    def short_output(self):
        return (
            self.sms.sms
            + [True if self.status == FamilyStatus.COMPLETE else False]
            + list(map(lambda j: j.name, self.jms))
        )

    def full_output(self, constraint_headers):
        jm_rows = []
        family_completion = True if self.status == FamilyStatus.COMPLETE else False
        for jm in self.jms:
            res = self.sms.sms + [family_completion] + [jm.name]
            for header in constraint_headers[4:]:
                if is_preference(header):
                    pref_header = get_preference_header(header)
                    dv = jm.get_datavalue(pref_header)
                    pref_option = get_preference_option(header)
                    res.append(dv.value[pref_option])
                else:
                    dv = jm.get_datavalue(header)
                    res.append(dv.value)
            jm_rows.append(res)
        return jm_rows


### CONTROLLERS ###
class FamilyMatcher:
    def __init__(self):
        self.families = []
        self.stray_jms = []

    # Load mentor data
    def load_sms(self):
        try:
            with open(path_sms, newline="") as file_sms:
                reader = csv.DictReader(file_sms)
                for row in reader:
                    self.add_family(row)
        except Exception as e:
            print("An error occurred while adding SMs to a family.", e)

    def load_pref_headers(self, headers):
        for header in headers:
            if is_preference(header):
                pref_header = get_preference_header(header)
                pref_constraint = get_constraint(pref_header, preference_constraints)
                pref_constraint.options.append(header)

    def load_jms(self):
        try:
            with open(path_jms, newline="") as file_jms:
                reader = csv.DictReader(file_jms)
                did_read_pref_headers = False
                for row in reader:
                    if not did_read_pref_headers:
                        self.load_pref_headers(row)
                        did_read_pref_headers = True
                    self.add_jm(row)
        except Exception as e:
            print("An error occurred when initially loading JM data.", e)
            raise e

    def add_family(self, sm_data):
        new_family = Family()
        new_family.add_sms(sm_data)
        self.families.append(new_family)

    def add_jm(self, jm_data):
        new_jm = JM(jm_data["Name"])
        new_jm.load_data(jm_data)
        self.stray_jms.append(new_jm)

    # Mentor manipulation
    def assign_perfect_fits(self):
        assigned = []
        for jm in self.stray_jms:
            fit_found = False
            for family in self.families:
                if not fit_found and family.jm_add_check(jm):
                    fit_found = True
                    family.add_jm(jm)
                    assigned.append(jm)
        for assigned_jm in assigned:
            self.stray_jms.remove(assigned_jm)

    def perfect_stray_adds(self, incomplete_families, complete_families):
        for i in incomplete_families:
            assigned = []
            for jm in self.stray_jms:
                if not jm_count_constraint.is_satisfied(len(i.jms)) and i.jm_add_check(
                    jm
                ):
                    i.add_jm(jm)
                    assigned.append(jm)
            for assigned_jm in assigned:
                self.stray_jms.remove(assigned_jm)
        self.promote_families_by_status(incomplete_families, complete_families)

    def perfect_steals(self, incomplete_families, complete_families):
        for i in incomplete_families:
            for c in complete_families:
                stolen = None
                for jm in c.jms:
                    if (
                        stolen is None
                        and not jm_count_constraint.is_satisfied(len(i.jms))
                        and i.jm_add_check(jm)
                        and c.allow_steal(jm)
                    ):
                        stolen = jm
                if stolen is not None:
                    i.add_jm(stolen)
                    c.remove_jm(stolen)
                    break
        self.promote_families_by_status(incomplete_families, complete_families)

    def perfect_swaps(self, incomplete_families, complete_families):
        for i in incomplete_families:
            for f in self.families:
                swap_this, swap_other = None, None
                for jm in i.jms:
                    for other_jm in f.jms:
                        if (
                            swap_this is None
                            and swap_other is None
                            and i.allow_swap(jm, other_jm)
                            and f.allow_swap(other_jm, jm)
                        ):
                            swap_this, swap_other = jm, other_jm
                if swap_this is not None and swap_other is not None:
                    i.swap_jm(swap_this, swap_other)
                    f.swap_jm(swap_other, swap_this)
        self.promote_families_by_status(incomplete_families, complete_families)

    def stray_swap(self, jm_from_family, jm_to_family):
        self.stray_jms.remove(jm_to_family)
        self.stray_jms.append(jm_from_family)

    def perfect_stray_swaps(self, incomplete_families, complete_families):
        for f in self.families:
            swap_family, swap_stray = None, None
            for jm in f.jms:
                for stray in self.stray_jms:
                    if (
                        swap_family is None
                        and swap_stray is None
                        and f.allow_swap(jm, stray)
                    ):
                        swap_family, swap_stray = jm, stray
            if swap_family is not None and swap_stray is not None:
                f.swap_jm(swap_family, swap_stray)
                self.stray_swap(swap_family, swap_stray)
        self.promote_families_by_status(incomplete_families, complete_families)

    def iterate(self):
        for _ in range(MAX_ITERS):
            self.assign_perfect_fits()
            incomplete_families, complete_families = [], []
            self.split_families_by_status(incomplete_families, complete_families)
            self.perfect_stray_adds(incomplete_families, complete_families)
            self.perfect_steals(incomplete_families, complete_families)
            self.perfect_swaps(incomplete_families, complete_families)
            self.perfect_stray_swaps(incomplete_families, complete_families)

    def split_families_by_status(self, incomplete_families, complete_families):
        for f in self.families:
            if f.status == FamilyStatus.COMPLETE:
                complete_families.append(f)
            else:
                incomplete_families.append(f)

    def promote_families_by_status(self, incomplete_families, complete_families):
        promoted = []
        for f in incomplete_families:
            if f.status == FamilyStatus.COMPLETE:
                complete_families.append(f)
                promoted.append(f)
        for promoted_family in promoted:
            incomplete_families.remove(promoted_family)


### OUTPUT HANDLERS ###
def get_short_headers():
    headers = ["SM 1", "SM 2", "Perfectly Compatible"]
    for i in range(jm_count_constraint.max_count):
        headers.append("JM " + str(i + 1))
    return headers


def csv_short(matcher):
    try:
        with open(path_write_short, "w") as file_write:
            writer = csv.writer(file_write, quoting=csv.QUOTE_MINIMAL)
            writer.writerow(get_short_headers())
            for family in matcher.families:
                writer.writerow(family.short_output())
            idx = 0
            while idx < len(matcher.stray_jms):
                jms = matcher.stray_jms[
                    idx : idx
                    + min(jm_count_constraint.max_count, len(matcher.stray_jms) - idx)
                ]
                writer.writerow(
                    [False] + ["Unassigned"] * 2 + list(map(lambda j: j.name, jms))
                )
                idx += jm_count_constraint.max_count
    except Exception as e:
        print("An error occurred when writing CSV output (short).", e)


def get_full_headers():
    headers = ["SM 1", "SM 2", "Family Complete", "JM"]
    for pc in preference_constraints:
        headers.extend(pc.options)
    for cc in count_constraints:
        headers.append(cc.header)
    for dc in difference_constraints:
        headers.append(dc.header)
    return headers


def csv_full(matcher):
    try:
        with open(path_write_full, "w") as file_write:
            writer = csv.writer(file_write, quoting=csv.QUOTE_MINIMAL)
            full_headers = get_full_headers()
            writer.writerow(full_headers)
            for family in matcher.families:
                writer.writerows(family.full_output(full_headers))
            for jm in matcher.stray_jms:
                jm_row = [False] + ["Unassigned"] * 2 + [jm.name]
                for header in full_headers[4:]:
                    if is_preference(header):
                        pref_header = get_preference_header(header)
                        dv = jm.get_datavalue(pref_header)
                        pref_option = get_preference_option(header)
                        jm_row.append(dv.value[pref_option])
                    else:
                        dv = jm.get_datavalue(header)
                        jm_row.append(dv.value)
                writer.writerow(jm_row)
    except Exception as e:
        print("An error occurred when writing CSV output (full).", e)


def text_short(matcher):
    print("################\n### FAMILIES ###\n################\n")
    for f in matcher.families:
        print("----------------")
        print("INCOMPLETE" if f.status == FamilyStatus.INCOMPLETE else "COMPLETE")
        sm_str = "SMs ({0}): ".format(len(f.sms.sms))
        for sm in f.sms.sms:
            sm_str += sm + ", "
        print(sm_str[:-2])
        jm_str = "JMs ({0}): ".format(len(f.jms))
        for j in f.jms:
            jm_str += j.name + ", "
        print(jm_str[:-2])
        print("----------------\n")
    print("#################\n### STRAY JMS ###\n#################\n")
    for j in matcher.stray_jms:
        print(j.name)


def text_full(matcher):
    print("################\n### FAMILIES ###\n################\n")
    for f in matcher.families:
        print("----------------")
        print("INCOMPLETE" if f.status == FamilyStatus.INCOMPLETE else "COMPLETE")
        sm_str = "SMs ({0}): ".format(len(f.sms.sms))
        for sm in f.sms.sms:
            sm_str += sm + ", "
        print(sm_str[:-2])
        for dv in f.sms.data:
            print(dv.header + ":", dv.value)
        print("JMs ({0}): ".format(len(f.jms)))
        for j in f.jms:
            print("---")
            print(j.name)
            for dv in j.data:
                print(dv.header + ":", dv.value)
        print("----------------\n")
    print("#################\n### STRAY JMS ###\n#################\n")
    for j in matcher.stray_jms:
        print("----------------")
        print(j.name)
        for dv in j.data:
            print(dv.header + ":", dv.value)
        print("----------------\n")


### MAIN ###
def run():
    # Load mentors
    matcher = FamilyMatcher()
    matcher.load_sms()
    matcher.load_jms()

    # Run algorithm
    matcher.iterate()

    # CSV output
    csv_short(matcher)
    csv_full(matcher)

    # Text output
    if text_output == Text.SHORT:
        text_short(matcher)
    elif text_output == Text.FULL:
        text_full(matcher)


if __name__ == "__main__":
    run()
