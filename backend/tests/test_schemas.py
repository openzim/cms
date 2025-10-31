"""Tests for base schema models and their inheritance behavior"""

import json
from datetime import UTC, datetime
from enum import Enum

from dateutil.parser import isoparse

from cms_backend.schemas import BaseModel, CamelModel, DashModel, WithExtraModel
from cms_backend.utils.datetime import getnow


class TestBaseModel:
    """Test BaseModel configuration and datetime serialization"""

    def test_datetime_serialization_naive_utc(self):
        """Test that naive datetimes get UTC timezone indication"""

        class TestSchema(BaseModel):
            created_at: datetime

        naive_dt = getnow()  # naive UTC datetime
        schema = TestSchema(created_at=naive_dt)

        # Serialize to JSON
        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # Check Z suffix is used for UTC
        assert parsed["created_at"].endswith("Z")

        # Verify it parses back as UTC
        parsed_dt = isoparse(parsed["created_at"])
        assert parsed_dt.tzname() == "UTC"

    def test_datetime_serialization_timezone_aware(self):
        """Test that timezone-aware datetimes preserve timezone info"""

        class TestSchema(BaseModel):
            created_at: datetime

        aware_dt = datetime.now(UTC)
        schema = TestSchema(created_at=aware_dt)

        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # Should have timezone info (either Z or +00:00)
        assert "Z" in parsed["created_at"] or "+00:00" in parsed["created_at"]

    def test_from_attributes(self):
        """Test that from_attributes is enabled"""

        class TestSchema(BaseModel):
            name: str
            value: int

        # Create a simple object to populate from
        class DataObject:
            def __init__(self):
                self.name = "test"
                self.value = 42

        obj = DataObject()
        schema = TestSchema.model_validate(obj)

        assert schema.name == "test"
        assert schema.value == 42

    def test_use_enum_values(self):
        """Test that enum values are used instead of enum instances"""

        class Status(str, Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        class TestSchema(BaseModel):
            status: Status

        schema = TestSchema(status=Status.ACTIVE)
        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # Should be the string value, not enum representation
        assert parsed["status"] == "active"
        assert not parsed["status"].startswith("Status.")

    def test_populate_by_name(self):
        """Test that fields can be populated by their name"""

        class TestSchema(BaseModel):
            user_name: str

        # Should work with the actual field name
        schema = TestSchema(user_name="alice")
        assert schema.user_name == "alice"


class TestWithExtraModel:
    """Test WithExtraModel allows extra fields"""

    def test_extra_fields_allowed(self):
        """Test that extra fields are preserved"""

        class TestSchema(WithExtraModel):
            name: str
            value: int

        schema = TestSchema(
            name="test",
            value=42,
            extra_field="extra",  # pyright: ignore[reportCallIssue]
            another="value",  # pyright: ignore[reportCallIssue]
        )

        # Check fields are accessible
        assert schema.name == "test"
        assert schema.value == 42

        # Check extra fields are in model_dump
        dumped = schema.model_dump()
        assert dumped["extra_field"] == "extra"
        assert dumped["another"] == "value"

    def test_datetime_serialization_with_extra(self):
        """Test that datetime serialization works with extra fields"""

        class TestSchema(WithExtraModel):
            name: str
            created_at: datetime

        schema = TestSchema(
            name="test",
            created_at=getnow(),
            extra_data="preserved",  # pyright: ignore[reportCallIssue]
        )

        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # Check datetime has Z suffix
        assert parsed["created_at"].endswith("Z")
        # Check extra field preserved
        assert parsed["extra_data"] == "preserved"

    def test_from_attributes_inherited(self):
        """Test that from_attributes is inherited from BaseModel"""

        class TestSchema(WithExtraModel):
            name: str

        class DataObject:
            def __init__(self):
                self.name = "test"
                self.extra = "allowed"

        obj = DataObject()
        schema = TestSchema.model_validate(obj)

        assert schema.name == "test"


class TestCamelModel:
    """Test CamelModel converts field names to camelCase"""

    def test_camel_case_aliases(self):
        """Test that fields are aliased to camelCase"""

        class TestSchema(CamelModel):
            user_name: str
            created_at: datetime
            is_active: bool

        schema = TestSchema(user_name="alice", created_at=getnow(), is_active=True)

        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # Check fields are in camelCase
        assert "userName" in parsed
        assert "createdAt" in parsed
        assert "isActive" in parsed

        # Check snake_case not present
        assert "user_name" not in parsed
        assert "created_at" not in parsed
        assert "is_active" not in parsed

    def test_datetime_serialization_with_camel_case(self):
        """Test datetime serialization works with camelCase"""

        class TestSchema(CamelModel):
            created_at: datetime

        schema = TestSchema(created_at=getnow())

        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # Check field is camelCase
        assert "createdAt" in parsed
        # Check datetime has Z suffix
        assert parsed["createdAt"].endswith("Z")

    def test_populate_by_name_inherited(self):
        """Test that populate_by_name is inherited"""

        class TestSchema(CamelModel):
            user_name: str

        # Should work with snake_case name
        schema = TestSchema(user_name="alice")
        assert schema.user_name == "alice"

        # Should also work with camelCase alias in dict/json input
        schema2 = TestSchema.model_validate({"userName": "bob"})
        assert schema2.user_name == "bob"


class TestDashModel:
    """Test DashModel converts field names to kebab-case"""

    def test_kebab_case_aliases(self):
        """Test that fields are aliased to kebab-case"""

        class TestSchema(DashModel):
            user_name: str
            created_at: datetime
            is_active: bool

        schema = TestSchema(user_name="alice", created_at=getnow(), is_active=True)

        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # Check fields are in kebab-case
        assert "user-name" in parsed
        assert "created-at" in parsed
        assert "is-active" in parsed

        # Check snake_case not present
        assert "user_name" not in parsed
        assert "created_at" not in parsed
        assert "is_active" not in parsed

    def test_datetime_serialization_with_kebab_case(self):
        """Test datetime serialization works with kebab-case"""

        class TestSchema(DashModel):
            created_at: datetime

        schema = TestSchema(created_at=getnow())

        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # Check field is kebab-case
        assert "created-at" in parsed
        # Check datetime has Z suffix
        assert parsed["created-at"].endswith("Z")

    def test_populate_by_name_inherited(self):
        """Test that populate_by_name is inherited"""

        class TestSchema(DashModel):
            user_name: str

        # Should work with snake_case name
        schema = TestSchema(user_name="alice")
        assert schema.user_name == "alice"

        # Should also work with kebab-case alias in dict/json input
        schema2 = TestSchema.model_validate({"user-name": "bob"})
        assert schema2.user_name == "bob"


class TestInheritanceChain:
    """Test complex inheritance scenarios"""

    def test_multiple_datetimes(self):
        """Test multiple datetime fields in same schema"""

        class TestSchema(BaseModel):
            created_at: datetime
            updated_at: datetime
            deleted_at: datetime | None

        now = getnow()
        schema = TestSchema(created_at=now, updated_at=now, deleted_at=None)

        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # All datetime fields should have Z suffix
        assert parsed["created_at"].endswith("Z")
        assert parsed["updated_at"].endswith("Z")
        assert parsed["deleted_at"] is None

    def test_nested_models(self):
        """Test datetime serialization in nested models"""

        class NestedSchema(BaseModel):
            timestamp: datetime

        class ParentSchema(BaseModel):
            name: str
            nested: NestedSchema

        schema = ParentSchema(name="test", nested=NestedSchema(timestamp=getnow()))

        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # Nested datetime should have Z suffix
        assert parsed["nested"]["timestamp"].endswith("Z")

    def test_list_of_models_with_datetime(self):
        """Test datetime serialization in list of models"""

        class ItemSchema(BaseModel):
            name: str
            created: datetime

        class ListSchema(BaseModel):
            items: list[ItemSchema]

        schema = ListSchema(
            items=[
                ItemSchema(name="item1", created=getnow()),
                ItemSchema(name="item2", created=getnow()),
            ]
        )

        json_str = schema.model_dump_json()
        parsed = json.loads(json_str)

        # All items should have datetime with Z suffix
        for item in parsed["items"]:
            assert item["created"].endswith("Z")
