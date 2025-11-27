"""
Mongo Task Repository Adapter.
"""

from typing import List, Optional
from domain.entities import Job, JobStatus, Chunk
from ports.repository import TaskRepositoryPort
from repositories.models import (
    JobModel,
    JobCreate,
    JobUpdate,
    JobStatus as MongoJobStatus,
)
from core.database import get_database
from repositories.objectid_utils import str_to_objectid
from core.logger import logger


class MongoTaskRepository(TaskRepositoryPort):
    """MongoDB implementation of TaskRepositoryPort."""

    def __init__(self, collection_name: str = "stt_jobs"):
        self.collection_name = collection_name

    def _to_entity(self, model: JobModel) -> Job:
        """Convert Pydantic model to Domain Entity."""
        return Job(
            id=model.id,
            original_filename=model.original_filename,
            minio_audio_path=model.minio_audio_path,
            file_size_mb=model.file_size_mb,
            language=model.language,
            status=JobStatus(model.status.value),
            worker_id=model.worker_id,
            retry_count=model.retry_count,
            chunks=[
                Chunk(
                    index=c.chunk_index,
                    start_time=c.start_time,
                    end_time=c.end_time,
                    file_path=c.file_path,
                    transcription=c.transcription,
                    status=JobStatus(c.status.value),
                    error_message=c.error_message,
                    processed_at=c.processed_at,
                )
                for c in model.chunks
            ],
            chunks_total=model.chunks_total,
            chunks_completed=model.chunks_completed,
            transcription_text=model.transcription_text,
            minio_result_path=model.minio_result_path,
            audio_duration_seconds=model.audio_duration_seconds,
            error_message=model.error_message,
            model_used=model.model_used,
            chunk_strategy=model.chunk_strategy,
            created_at=model.created_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Job) -> JobModel:
        """Convert Domain Entity to Pydantic Model."""
        # Note: This is a simplified conversion. In a real app, we might need more care.
        from repositories.models import ChunkModel

        chunks = [
            ChunkModel(
                chunk_index=c.index,
                start_time=c.start_time,
                end_time=c.end_time,
                file_path=c.file_path,
                transcription=c.transcription,
                status=MongoJobStatus(c.status.value),
                error_message=c.error_message,
                processed_at=c.processed_at,
            )
            for c in entity.chunks
        ]

        return JobModel(
            id=entity.id,
            status=MongoJobStatus(entity.status.value),
            language=entity.language,
            original_filename=entity.original_filename,
            minio_audio_path=entity.minio_audio_path,
            minio_result_path=entity.minio_result_path,
            file_size_mb=entity.file_size_mb,
            audio_duration_seconds=entity.audio_duration_seconds,
            worker_id=entity.worker_id,
            retry_count=entity.retry_count,
            chunks_total=entity.chunks_total,
            chunks_completed=entity.chunks_completed,
            chunks=chunks,
            transcription_text=entity.transcription_text,
            error_message=entity.error_message,
            model_used=entity.model_used,
            chunk_strategy=entity.chunk_strategy,
            created_at=entity.created_at,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            updated_at=entity.updated_at,
        )

    async def create_job(self, job: Job) -> Job:
        model = self._to_model(job)
        db = await get_database()
        collection = await db.get_collection(self.collection_name)

        # Insert
        data = model.to_dict()
        # Ensure _id is handled if provided, or let Mongo generate it
        if job.id:
            # If ID is provided (e.g. UUID), we might want to use it as _id or just a field.
            # The legacy system used ObjectId as _id and mapped it to 'id'.
            # If we generated a UUID in UseCase, we might want to store it as 'id' field
            # and let Mongo have its own _id, or force _id to be the UUID (if we change schema).
            # For compatibility, let's stick to Mongo generating _id, but we have a problem:
            # UseCase generated an ID.
            # Legacy `create_job` ignored input ID and returned new ObjectId.
            # Let's try to use the UseCase ID if possible, or just ignore it and update the entity.
            pass

        # For now, let's follow the legacy pattern: insert and get ObjectId
        # But UseCase expects the ID it generated to be respected OR updated.
        # If we want to support UUIDs, we should store them.
        # Let's assume we store the UseCase ID as `job_id` (legacy field) or just `id`.
        # The `JobModel` has `id` field which maps to `_id`.

        # If we want to use the UUID from UseCase as the ID:
        # data['_id'] = job.id
        # But `JobModel` uses ObjectId usually.
        # Let's just insert and update the entity with the new ID if it was None,
        # or if we want to enforce the UUID, we need to change how `JobModel` works.
        # Given `JobModel` definition: `id: Optional[str] = Field(None, description="MongoDB _id as string")`

        # Let's just insert.
        result = await collection.insert_one(data)

        # Update entity ID with the one from Mongo
        from repositories.objectid_utils import objectid_to_str

        new_id = objectid_to_str(result.inserted_id)

        # Return a new entity with the correct ID
        # (We should probably update the input entity too, but returning new is safer)
        # Re-fetch to be sure? Or just patch.
        job.id = new_id
        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        db = await get_database()
        collection = await db.get_collection(self.collection_name)

        try:
            oid = str_to_objectid(job_id)
            doc = await collection.find_one({"_id": oid})
        except:
            # Maybe it's not an ObjectId? Try finding by 'id' field if we stored UUIDs there?
            # For now assume ObjectId
            return None

        if doc:
            model = JobModel.from_dict(doc)
            return self._to_entity(model)
        return None

    async def update_job(self, job: Job) -> bool:
        model = self._to_model(job)
        db = await get_database()
        collection = await db.get_collection(self.collection_name)

        oid = str_to_objectid(job.id)
        data = model.to_dict()

        # Remove _id from update data
        if "_id" in data:
            del data["_id"]
        if "id" in data:
            del data["id"]

        result = await collection.update_one({"_id": oid}, {"$set": data})
        return result.modified_count > 0 or result.matched_count > 0

    async def get_pending_jobs(self, limit: int = 10) -> List[Job]:
        db = await get_database()
        collection = await db.get_collection(self.collection_name)

        cursor = (
            collection.find({"status": "PENDING"}).sort("created_at", 1).limit(limit)
        )
        jobs = []
        async for doc in cursor:
            jobs.append(self._to_entity(JobModel.from_dict(doc)))
        return jobs

    async def list_jobs(
        self, limit: int = 100, status: Optional[str] = None
    ) -> List[Job]:
        db = await get_database()
        collection = await db.get_collection(self.collection_name)

        query = {}
        if status:
            query["status"] = status

        cursor = collection.find(query).sort("created_at", -1).limit(limit)
        jobs = []
        async for doc in cursor:
            jobs.append(self._to_entity(JobModel.from_dict(doc)))
        return jobs
