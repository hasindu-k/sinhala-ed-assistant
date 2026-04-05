from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.shared.models.evaluation_session import MarkingSchema, MarkingSchemaItem


class MarkingSchemaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_marking_schema(self, schema_id: UUID) -> Optional[MarkingSchema]:
        return self.db.query(MarkingSchema).filter(MarkingSchema.id == schema_id).first()

    def get_marking_schema_by_session(self, evaluation_session_id: UUID) -> Optional[MarkingSchema]:
        return (
            self.db.query(MarkingSchema)
            .filter(MarkingSchema.evaluation_session_id == evaluation_session_id)
            .first()
        )

    def get_marking_schema_items(self, schema_id: UUID) -> List[MarkingSchemaItem]:
        return (
            self.db.query(MarkingSchemaItem)
            .filter(MarkingSchemaItem.marking_schema_id == schema_id)
            .order_by(MarkingSchemaItem.sort_order.asc(), MarkingSchemaItem.id.asc())
            .all()
        )

    def create_marking_schema(
        self,
        evaluation_session_id: UUID,
        *,
        resource_id: Optional[UUID] = None,
        is_confirmed: bool = False,
    ) -> MarkingSchema:
        schema = MarkingSchema(
            evaluation_session_id=evaluation_session_id,
            resource_id=resource_id,
            is_confirmed=is_confirmed,
        )
        self.db.add(schema)
        self.db.commit()
        self.db.refresh(schema)
        return schema

    def replace_marking_schema_items(self, schema_id: UUID, items: List[dict]) -> List[MarkingSchemaItem]:
        (
            self.db.query(MarkingSchemaItem)
            .filter(MarkingSchemaItem.marking_schema_id == schema_id)
            .delete(synchronize_session=False)
        )

        created_items: List[MarkingSchemaItem] = []
        for item in items:
            model = MarkingSchemaItem(marking_schema_id=schema_id, **item)
            self.db.add(model)
            created_items.append(model)

        self.db.commit()
        for item in created_items:
            self.db.refresh(item)
        return created_items

    def update_marking_schema(
        self,
        schema_id: UUID,
        *,
        resource_id: Optional[UUID] = None,
        is_confirmed: Optional[bool] = None,
    ) -> Optional[MarkingSchema]:
        schema = self.db.query(MarkingSchema).filter(MarkingSchema.id == schema_id).first()
        if not schema:
            return None

        if resource_id is not None:
            schema.resource_id = resource_id
        if is_confirmed is not None:
            schema.is_confirmed = is_confirmed

        self.db.commit()
        self.db.refresh(schema)
        return schema

    def delete_marking_schema(self, evaluation_session_id: UUID) -> bool:
        rows = (
            self.db.query(MarkingSchema)
            .filter(MarkingSchema.evaluation_session_id == evaluation_session_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return rows > 0
