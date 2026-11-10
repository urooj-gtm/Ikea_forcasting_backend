from fastapi import APIRouter, File, HTTPException, UploadFile

from .. import config
from ..services.spi import public_meta, read_spi
from ..store import store

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


def ingest(content: bytes, filename: str) -> dict:
    try:
        df, meta = read_spi(content, filename)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    store.put(df, meta)
    return public_meta(meta)


@router.get("")
def list_snapshots():
    return [public_meta(m) for m in store.metas()]


@router.post("")
async def upload_snapshot(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {config.MAX_UPLOAD_MB} MB.")
    return ingest(content, file.filename or "")
