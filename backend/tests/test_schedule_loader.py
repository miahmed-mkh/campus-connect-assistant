from backend.app.services.schedule_loader import (
    SCHEDULE_SOURCE,
    load_course_slots,
    load_exams,
    load_important_dates,
    load_rooms,
    load_schedule_data,
    load_schedule_teachers,
    load_subjects,
)


def test_load_schedule_data() -> None:
    data = load_schedule_data()

    assert len(data["formations"]) == 8
    assert len(data["emploi_du_temps"]) == 4
    assert len(data["examens"]) == 2


def test_load_course_slots_flattens_schedules() -> None:
    course_slots = load_course_slots()

    assert len(course_slots) == 56

    first_slot = course_slots[0]

    assert first_slot["groupe"] == "B1-A"
    assert first_slot["formation"] == "B1"
    assert first_slot["semestre"] == "S1"
    assert first_slot["jour"] == "Lundi"
    assert first_slot["source"] == SCHEDULE_SOURCE


def test_course_slots_contain_expected_groups() -> None:
    groups = {
        slot["groupe"]
        for slot in load_course_slots()
    }

    assert groups == {
        "B1-A",
        "B3-DATA-1",
        "M1-IA-1",
        "B3-CYBER-1",
    }


def test_load_exams_flattens_exam_sessions() -> None:
    data = load_schedule_data()
    expected_count = sum(
        len(session["epreuves"])
        for session in data["examens"]
    )

    exams = load_exams()

    assert len(exams) == expected_count
    assert all(exam["source"] == SCHEDULE_SOURCE for exam in exams)
    assert all("formation" in exam for exam in exams)
    assert all("session" in exam for exam in exams)


def test_load_important_dates() -> None:
    dates = load_important_dates()

    assert len(dates) == 30
    assert dates[0]["date"] == "2024-09-02"
    assert dates[0]["evenement"] == "Rentrée académique"
    assert dates[0]["source"] == SCHEDULE_SOURCE


def test_load_schedule_reference_data() -> None:
    assert len(load_subjects()) == 30
    assert len(load_rooms()) == 17
    assert len(load_schedule_teachers()) == 20