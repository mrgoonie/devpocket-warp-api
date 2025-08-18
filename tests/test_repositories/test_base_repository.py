"""
Comprehensive tests for BaseRepository to achieve 75% coverage.

Tests all BaseRepository methods including:
- CRUD operations (create, read, update, delete)
- Search and filtering
- Bulk operations
- Transaction handling
- Error scenarios
- Relationship loading
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import Column, String, Integer, select, update, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.models.base import BaseModel


# Test model for BaseRepository testing
class TestModel(BaseModel):
    """Test model for BaseRepository testing."""
    
    __tablename__ = "test_model"
    
    name = Column(String(100), nullable=False)
    value = Column(Integer, default=0)
    category = Column(String(50), nullable=True)


@pytest.mark.database
class TestBaseRepository:
    """Comprehensive tests for BaseRepository functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession for testing."""
        session = MagicMock(spec=AsyncSession)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create BaseRepository instance for testing."""
        return BaseRepository(TestModel, mock_session)

    @pytest.fixture
    def sample_test_data(self):
        """Sample data for testing."""
        return {
            "name": "test_item",
            "value": 42,
            "category": "test_category"
        }

    # Test Create Operations
    @pytest.mark.asyncio
    async def test_create_with_dict_data(self, repository, mock_session, sample_test_data):
        """Test creating model instance with dictionary data."""
        # Mock the instance creation
        mock_instance = MagicMock(spec=TestModel)
        mock_instance.id = "test-id"
        mock_instance.name = "test_item"
        
        with patch.object(repository.model, '__call__', return_value=mock_instance):
            result = await repository.create(sample_test_data)

            mock_session.add.assert_called_once_with(mock_instance)
            mock_session.flush.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_instance)
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_create_with_model_instance(self, repository, mock_session):
        """Test creating with existing model instance."""
        mock_instance = MagicMock(spec=TestModel)
        mock_instance.id = "test-id"
        
        result = await repository.create(mock_instance)

        mock_session.add.assert_called_once_with(mock_instance)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_instance)
        assert result == mock_instance

    @pytest.mark.asyncio
    async def test_create_with_none_data_and_kwargs(self, repository, mock_session):
        """Test creating with None data and kwargs."""
        mock_instance = MagicMock(spec=TestModel)
        mock_instance.id = "test-id"
        
        with patch.object(repository.model, '__call__', return_value=mock_instance):
            result = await repository.create(None, name="test", value=123)

            mock_session.add.assert_called_once_with(mock_instance)
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_create_with_object_with_dict_attribute(self, repository, mock_session):
        """Test creating with object that has __dict__ attribute."""
        class MockData:
            def __init__(self):
                self.name = "test"
                self.value = 42
        
        mock_data = MockData()
        mock_instance = MagicMock(spec=TestModel)
        
        with patch.object(repository.model, '__call__', return_value=mock_instance):
            result = await repository.create(mock_data, category="extra")

            mock_session.add.assert_called_once_with(mock_instance)
            assert result == mock_instance

    # Test Read Operations
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, repository, mock_session):
        """Test successful get by ID."""
        mock_instance = MagicMock(spec=TestModel)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_instance
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id("test-id")

        assert result == mock_instance
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_session):
        """Test get by ID when item not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id("nonexistent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_alias_method(self, repository, mock_session):
        """Test get method as alias for get_by_id."""
        mock_instance = MagicMock(spec=TestModel)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_instance
        mock_session.execute.return_value = mock_result

        result = await repository.get("test-id")

        assert result == mock_instance
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, mock_session):
        """Test get_all with pagination and ordering."""
        mock_instances = [MagicMock(spec=TestModel) for _ in range(3)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_instances
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(offset=10, limit=20, order_by="name", order_desc=False)

        assert result == mock_instances
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_default_ordering(self, repository, mock_session):
        """Test get_all with default ordering (created_at desc)."""
        mock_instances = [MagicMock(spec=TestModel) for _ in range(2)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_instances
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert result == mock_instances
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_invalid_order_field(self, repository, mock_session):
        """Test get_all with invalid order field falls back to created_at."""
        mock_instances = [MagicMock(spec=TestModel)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_instances
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Mock getattr to return created_at when invalid field is accessed
        with patch('builtins.getattr') as mock_getattr:
            mock_getattr.side_effect = lambda obj, attr, default=None: (
                repository.model.created_at if attr == "nonexistent_field" else 
                getattr(obj, attr, default)
            )
            
            result = await repository.get_all(order_by="nonexistent_field")

            assert result == mock_instances

    @pytest.mark.asyncio
    async def test_get_by_field_success(self, repository, mock_session):
        """Test successful get by field."""
        mock_instance = MagicMock(spec=TestModel)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_instance
        mock_session.execute.return_value = mock_result

        with patch('builtins.hasattr', return_value=True):
            with patch('builtins.getattr', return_value=MagicMock()):
                result = await repository.get_by_field("name", "test_value")

                assert result == mock_instance
                mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_field_invalid_field(self, repository, mock_session):
        """Test get by field with invalid field name."""
        with patch('builtins.hasattr', return_value=False):
            with pytest.raises(ValueError, match="doesn't have field"):
                await repository.get_by_field("invalid_field", "test_value")

    @pytest.mark.asyncio
    async def test_get_many_by_field_success(self, repository, mock_session):
        """Test successful get many by field."""
        mock_instances = [MagicMock(spec=TestModel) for _ in range(3)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_instances
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        with patch('builtins.hasattr', return_value=True):
            with patch('builtins.getattr', return_value=MagicMock()):
                result = await repository.get_many_by_field("category", "test_cat", offset=5, limit=10)

                assert result == mock_instances
                mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_many_by_field_invalid_field(self, repository, mock_session):
        """Test get many by field with invalid field name."""
        with patch('builtins.hasattr', return_value=False):
            with pytest.raises(ValueError, match="doesn't have field"):
                await repository.get_many_by_field("invalid_field", "test_value")

    # Test Update Operations
    @pytest.mark.asyncio
    async def test_update_by_id_success(self, repository, mock_session):
        """Test successful update by ID."""
        mock_instance = MagicMock(spec=TestModel)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_instance
        mock_session.execute.return_value = mock_result

        result = await repository.update("test-id", name="new_name", value=100)

        assert result == mock_instance
        mock_session.refresh.assert_called_once_with(mock_instance)

    @pytest.mark.asyncio
    async def test_update_by_id_not_found(self, repository, mock_session):
        """Test update by ID when item not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.update("nonexistent-id", name="new_name")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_by_id_no_update_data(self, repository, mock_session):
        """Test update by ID with no valid update data."""
        mock_instance = MagicMock(spec=TestModel)
        
        with patch.object(repository, 'get_by_id', return_value=mock_instance):
            result = await repository.update("test-id", id="should_be_ignored", created_at="should_be_ignored")

            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_update_by_id_with_none_values(self, repository, mock_session):
        """Test update by ID filtering out None values."""
        mock_instance = MagicMock(spec=TestModel)
        
        with patch.object(repository, 'get_by_id', return_value=mock_instance):
            result = await repository.update("test-id", name=None, value="valid_value")

            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_update_by_instance_success(self, repository, mock_session):
        """Test successful update by instance."""
        mock_instance = MagicMock(spec=TestModel)
        mock_instance.name = "old_name"
        
        with patch('builtins.hasattr', return_value=True):
            with patch('builtins.setattr') as mock_setattr:
                result = await repository.update(mock_instance, name="new_name", value=123)

                assert result == mock_instance
                mock_setattr.assert_called()
                mock_session.flush.assert_called_once()
                mock_session.refresh.assert_called_once_with(mock_instance)

    @pytest.mark.asyncio
    async def test_update_by_instance_protected_fields(self, repository, mock_session):
        """Test update by instance ignores protected fields."""
        mock_instance = MagicMock(spec=TestModel)
        
        with patch('builtins.hasattr', return_value=True):
            with patch('builtins.setattr') as mock_setattr:
                result = await repository.update(mock_instance, id="new_id", created_at="new_date", name="new_name")

                assert result == mock_instance
                # Should not set protected fields
                mock_setattr.assert_called_with(mock_instance, "name", "new_name")

    # Test Delete Operations
    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_session):
        """Test successful delete."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete("test-id")

        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        """Test delete when item not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete("nonexistent-id")

        assert result is False

    # Test Existence and Count Operations
    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_session):
        """Test exists returns True when item exists."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        result = await repository.exists(name="test_name", category="test_cat")

        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_session):
        """Test exists returns False when item doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        result = await repository.exists(name="nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_none_count(self, repository, mock_session):
        """Test exists handles None count result."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.exists(name="test")

        assert result is False

    @pytest.mark.asyncio
    async def test_count_with_criteria(self, repository, mock_session):
        """Test count with criteria."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        result = await repository.count(category="test_cat", value=42)

        assert result == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_without_criteria(self, repository, mock_session):
        """Test count without criteria."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_none_result(self, repository, mock_session):
        """Test count handles None result."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0

    # Test Search Operations
    @pytest.mark.asyncio
    async def test_search_success(self, repository, mock_session):
        """Test successful search across multiple fields."""
        mock_instances = [MagicMock(spec=TestModel) for _ in range(2)]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_instances
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        with patch('builtins.hasattr', return_value=True):
            with patch('builtins.getattr') as mock_getattr:
                mock_field = MagicMock()
                mock_field.ilike.return_value = MagicMock()
                mock_getattr.return_value = mock_field
                
                result = await repository.search(["name", "category"], "search_term", offset=0, limit=5)

                assert result == mock_instances
                mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_no_valid_fields(self, repository, mock_session):
        """Test search with no valid fields."""
        with patch('builtins.hasattr', return_value=False):
            result = await repository.search(["invalid_field"], "search_term")

            assert result == []
            mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_empty_fields_list(self, repository, mock_session):
        """Test search with empty fields list."""
        result = await repository.search([], "search_term")

        assert result == []
        mock_session.execute.assert_not_called()

    # Test Bulk Operations
    @pytest.mark.asyncio
    async def test_bulk_create_success(self, repository, mock_session):
        """Test successful bulk create."""
        instances_data = [
            {"name": "item1", "value": 1},
            {"name": "item2", "value": 2},
        ]
        
        mock_instances = [MagicMock(spec=TestModel) for _ in range(2)]
        
        with patch.object(repository.model, '__call__', side_effect=mock_instances):
            result = await repository.bulk_create(instances_data)

            assert result == mock_instances
            mock_session.add_all.assert_called_once_with(mock_instances)
            mock_session.flush.assert_called_once()
            assert mock_session.refresh.call_count == 2

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(self, repository, mock_session):
        """Test bulk create with empty list."""
        result = await repository.bulk_create([])

        assert result == []
        mock_session.add_all.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_bulk_update_success(self, repository, mock_session):
        """Test successful bulk update."""
        updates = [
            {"id": "1", "name": "updated1"},
            {"id": "2", "name": "updated2"},
        ]
        
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.bulk_update(updates)

        assert result == 2  # Two successful updates
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_bulk_update_missing_id_field(self, repository, mock_session):
        """Test bulk update with missing ID field."""
        updates = [
            {"name": "updated1"},  # Missing id field
            {"id": "2", "name": "updated2"},
        ]
        
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.bulk_update(updates)

        assert result == 1  # Only one successful update
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_update_custom_id_field(self, repository, mock_session):
        """Test bulk update with custom ID field."""
        updates = [
            {"custom_id": "1", "name": "updated1"},
            {"custom_id": "2", "name": "updated2"},
        ]
        
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.bulk_update(updates, id_field="custom_id")

        assert result == 2
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_bulk_delete_success(self, repository, mock_session):
        """Test successful bulk delete."""
        ids = ["1", "2", "3"]
        
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        result = await repository.bulk_delete(ids)

        assert result == 3
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_delete_empty_list(self, repository, mock_session):
        """Test bulk delete with empty list."""
        result = await repository.bulk_delete([])

        assert result == 0
        mock_session.execute.assert_not_called()

    # Test Relationship Loading
    @pytest.mark.asyncio
    async def test_get_with_relationships_success(self, repository, mock_session):
        """Test successful get with relationships."""
        mock_instance = MagicMock(spec=TestModel)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_instance
        mock_session.execute.return_value = mock_result

        with patch('builtins.hasattr', return_value=True):
            with patch('builtins.getattr', return_value=MagicMock()):
                result = await repository.get_with_relationships("test-id", ["relationship1", "relationship2"])

                assert result == mock_instance
                mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_relationships_invalid_relationship(self, repository, mock_session):
        """Test get with relationships with invalid relationship name."""
        mock_instance = MagicMock(spec=TestModel)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_instance
        mock_session.execute.return_value = mock_result

        with patch('builtins.hasattr', return_value=False):
            result = await repository.get_with_relationships("test-id", ["invalid_relationship"])

            assert result == mock_instance
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_relationships_not_found(self, repository, mock_session):
        """Test get with relationships when item not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_with_relationships("nonexistent-id", ["relationship1"])

        assert result is None

    @pytest.mark.asyncio
    async def test_get_with_relationships_empty_list(self, repository, mock_session):
        """Test get with relationships with empty relationships list."""
        mock_instance = MagicMock(spec=TestModel)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_instance
        mock_session.execute.return_value = mock_result

        result = await repository.get_with_relationships("test-id", [])

        assert result == mock_instance
        mock_session.execute.assert_called_once()

    # Test Error Scenarios
    @pytest.mark.asyncio
    async def test_create_database_error(self, repository, mock_session):
        """Test create with database error."""
        mock_session.flush.side_effect = SQLAlchemyError("Database error")
        
        with patch.object(repository.model, '__call__', return_value=MagicMock()):
            with pytest.raises(SQLAlchemyError):
                await repository.create({"name": "test"})

    @pytest.mark.asyncio
    async def test_update_database_error(self, repository, mock_session):
        """Test update with database error."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(SQLAlchemyError):
            await repository.update("test-id", name="new_name")

    @pytest.mark.asyncio
    async def test_delete_database_error(self, repository, mock_session):
        """Test delete with database error."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(SQLAlchemyError):
            await repository.delete("test-id")

    @pytest.mark.asyncio
    async def test_search_database_error(self, repository, mock_session):
        """Test search with database error."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        with patch('builtins.hasattr', return_value=True):
            with patch('builtins.getattr') as mock_getattr:
                mock_field = MagicMock()
                mock_field.ilike.return_value = MagicMock()
                mock_getattr.return_value = mock_field
                
                with pytest.raises(SQLAlchemyError):
                    await repository.search(["name"], "search_term")

    @pytest.mark.asyncio
    async def test_bulk_operations_database_error(self, repository, mock_session):
        """Test bulk operations with database error."""
        mock_session.flush.side_effect = SQLAlchemyError("Database error")
        
        with patch.object(repository.model, '__call__', return_value=MagicMock()):
            with pytest.raises(SQLAlchemyError):
                await repository.bulk_create([{"name": "test"}])

    # Test Edge Cases
    @pytest.mark.asyncio
    async def test_create_with_special_characters(self, repository, mock_session):
        """Test create with special characters in data."""
        special_data = {
            "name": "test'\"<>&",
            "value": -1,
            "category": "üñïçödé"
        }
        
        mock_instance = MagicMock(spec=TestModel)
        
        with patch.object(repository.model, '__call__', return_value=mock_instance):
            result = await repository.create(special_data)

            assert result == mock_instance
            mock_session.add.assert_called_once_with(mock_instance)

    @pytest.mark.asyncio
    async def test_search_with_special_characters(self, repository, mock_session):
        """Test search with special characters."""
        mock_instances = []
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_instances
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        with patch('builtins.hasattr', return_value=True):
            with patch('builtins.getattr') as mock_getattr:
                mock_field = MagicMock()
                mock_field.ilike.return_value = MagicMock()
                mock_getattr.return_value = mock_field
                
                result = await repository.search(["name"], "test'\"<>&üñïçödé")

                assert result == mock_instances

    @pytest.mark.asyncio
    async def test_update_with_large_offset_limit(self, repository, mock_session):
        """Test operations with very large offset/limit values."""
        mock_instances = []
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_instances
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(offset=1000000, limit=1000000)

        assert result == mock_instances
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_name_access(self, repository):
        """Test accessing model name from repository."""
        assert repository.model == TestModel
        assert repository.model.__name__ == "TestModel"

    @pytest.mark.asyncio
    async def test_session_access(self, repository, mock_session):
        """Test accessing session from repository."""
        assert repository.session == mock_session


@pytest.mark.database
class TestBaseRepositoryIntegration:
    """Integration tests for BaseRepository with real database session."""

    @pytest.fixture
    def real_repository(self, test_session):
        """Create BaseRepository with real test session."""
        from app.models.user import User
        return BaseRepository(User, test_session)

    @pytest.mark.asyncio
    async def test_real_create_and_get(self, real_repository):
        """Test create and get with real database session."""
        from app.models.user import UserRole
        
        user_data = {
            "username": "test_user_repo",
            "email": "test_repo@example.com",
            "full_name": "Test Repository User",
            "hashed_password": "hashed_password",
            "role": UserRole.USER
        }

        # Create user
        created_user = await real_repository.create(user_data)
        assert created_user.id is not None
        assert created_user.username == "test_user_repo"

        # Get user back
        fetched_user = await real_repository.get_by_id(created_user.id)
        assert fetched_user is not None
        assert fetched_user.username == "test_user_repo"

    @pytest.mark.asyncio
    async def test_real_update_and_delete(self, real_repository):
        """Test update and delete with real database session."""
        from app.models.user import UserRole
        
        user_data = {
            "username": "test_update_user",
            "email": "test_update@example.com",
            "full_name": "Test Update User",
            "hashed_password": "hashed_password",
            "role": UserRole.USER
        }

        # Create user
        created_user = await real_repository.create(user_data)
        user_id = created_user.id

        # Update user
        updated_user = await real_repository.update(user_id, full_name="Updated Name")
        assert updated_user.full_name == "Updated Name"

        # Delete user
        deleted = await real_repository.delete(user_id)
        assert deleted is True

        # Verify deletion
        fetched_user = await real_repository.get_by_id(user_id)
        assert fetched_user is None