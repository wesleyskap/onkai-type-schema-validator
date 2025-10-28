from typed_schema_validator import Field, Schema


class UserProfile(Schema):
    user_id: int = Field(alias="userId", gt=0)
    name: str = "Anonymous"
    email: str | None = None


def test_schema_fields_introspection():
    f_info = UserProfile.fields()

    assert "user_id" in f_info
    assert f_info["user_id"]["type"] is int
    assert f_info["user_id"]["alias"] == "userId"
    assert f_info["user_id"]["constraints"].gt == 0

    assert f_info["name"]["type"] is str
    assert f_info["name"]["has_default"] is True
    assert f_info["name"]["default"] == "Anonymous"

    assert f_info["email"]["has_default"] is True
    assert f_info["email"]["default"] is None
