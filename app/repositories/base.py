"""
Base repository class with common database operations.
"""

from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """Base repository class with common CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> ModelType:
        """Create a new model instance."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id: str) -> Optional[ModelType]:
        """Get model instance by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> List[ModelType]:
        """Get all model instances with pagination."""
        order_column = getattr(self.model, order_by, self.model.created_at)

        if order_desc:
            order_column = order_column.desc()

        result = await self.session.execute(
            select(self.model).order_by(order_column).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def get_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        """Get model instance by a specific field."""
        if not hasattr(self.model, field):
            raise ValueError(
                f"Model {self.model.__name__} doesn't have field '{field}'"
            )

        result = await self.session.execute(
            select(self.model).where(getattr(self.model, field) == value)
        )
        return result.scalar_one_or_none()

    async def get_many_by_field(
        self, field: str, value: Any, offset: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Get multiple model instances by a specific field."""
        if not hasattr(self.model, field):
            raise ValueError(
                f"Model {self.model.__name__} doesn't have field '{field}'"
            )

        result = await self.session.execute(
            select(self.model)
            .where(getattr(self.model, field) == value)
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """Update model instance by ID."""
        # Remove None values and protected fields
        update_data = {
            k: v
            for k, v in kwargs.items()
            if v is not None and k not in ["id", "created_at"]
        }

        if not update_data:
            return await self.get_by_id(id)

        result = await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**update_data)
            .returning(self.model)
        )

        updated_instance = result.scalar_one_or_none()
        if updated_instance:
            await self.session.refresh(updated_instance)

        return updated_instance

    async def delete(self, id: str) -> bool:
        """Delete model instance by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0

    async def exists(self, **kwargs) -> bool:
        """Check if model instance exists with given criteria."""
        conditions = [
            getattr(self.model, key) == value for key, value in kwargs.items()
        ]
        result = await self.session.execute(
            select(func.count(self.model.id)).where(and_(*conditions))
        )
        return result.scalar() > 0

    async def count(self, **kwargs) -> int:
        """Count model instances with optional criteria."""
        if kwargs:
            conditions = [
                getattr(self.model, key) == value for key, value in kwargs.items()
            ]
            result = await self.session.execute(
                select(func.count(self.model.id)).where(and_(*conditions))
            )
        else:
            result = await self.session.execute(select(func.count(self.model.id)))
        return result.scalar()

    async def search(
        self,
        search_fields: List[str],
        search_term: str,
        offset: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        """Search model instances across multiple fields."""
        conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                field_attr = getattr(self.model, field)
                conditions.append(field_attr.ilike(f"%{search_term}%"))

        if not conditions:
            return []

        result = await self.session.execute(
            select(self.model).where(or_(*conditions)).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def bulk_create(
        self, instances_data: List[Dict[str, Any]]
    ) -> List[ModelType]:
        """Create multiple model instances."""
        instances = [self.model(**data) for data in instances_data]
        self.session.add_all(instances)
        await self.session.flush()

        # Refresh all instances to get updated data
        for instance in instances:
            await self.session.refresh(instance)

        return instances

    async def bulk_update(
        self, updates: List[Dict[str, Any]], id_field: str = "id"
    ) -> int:
        """Update multiple model instances."""
        updated_count = 0

        for update_data in updates:
            if id_field not in update_data:
                continue

            id_value = update_data.pop(id_field)
            result = await self.session.execute(
                update(self.model)
                .where(getattr(self.model, id_field) == id_value)
                .values(**update_data)
            )
            updated_count += result.rowcount

        return updated_count

    async def bulk_delete(self, ids: List[str]) -> int:
        """Delete multiple model instances by IDs."""
        if not ids:
            return 0

        result = await self.session.execute(
            delete(self.model).where(self.model.id.in_(ids))
        )
        return result.rowcount

    async def get_with_relationships(
        self, id: str, relationships: List[str]
    ) -> Optional[ModelType]:
        """Get model instance with eagerly loaded relationships."""
        stmt = select(self.model).where(self.model.id == id)

        for relationship in relationships:
            if hasattr(self.model, relationship):
                stmt = stmt.options(selectinload(getattr(self.model, relationship)))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
