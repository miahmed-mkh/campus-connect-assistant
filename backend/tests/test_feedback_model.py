from backend.app.models import Feedback, Message


def test_feedback_table_name() -> None:
    assert Feedback.__tablename__ == "feedbacks"


def test_feedback_columns() -> None:
    assert list(Feedback.__table__.columns.keys()) == [
        "id",
        "message_id",
        "rating",
        "created_at",
        "updated_at",
    ]


def test_feedback_message_id_is_unique_and_required() -> None:
    message_id = Feedback.__table__.c.message_id

    assert message_id.nullable is False
    assert message_id.unique is True


def test_feedback_rating_is_required() -> None:
    rating = Feedback.__table__.c.rating

    assert rating.nullable is False
    assert rating.type.length == 10


def test_feedback_relationship_is_one_to_one() -> None:
    assert Message.feedback.property.uselist is False
    assert Feedback.message.property.uselist is False


def test_feedback_rating_check_constraint() -> None:
    constraints = {
        constraint.name
        for constraint in Feedback.__table__.constraints
    }

    assert "ck_feedbacks_rating" in constraints
