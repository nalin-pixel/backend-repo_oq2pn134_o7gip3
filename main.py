import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Section, Doc

app = FastAPI(title="DocsOS API", description="API para documentación de Sistemas Operativos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- Helpers ---------

def oid_str(oid):
    return str(oid) if isinstance(oid, ObjectId) else oid


def serialize_doc(doc: dict):
    if not doc:
        return doc
    doc["id"] = oid_str(doc.pop("_id", None))
    # convert any ObjectId fields we know
    if "section_id" in doc and isinstance(doc["section_id"], ObjectId):
        doc["section_id"] = str(doc["section_id"])
    return doc


# --------- Models ---------

class SectionCreate(Section):
    pass

class DocCreate(Doc):
    pass

# --------- Routes ---------

@app.get("/")
def root():
    return {"message": "DocsOS API running"}

@app.get("/schema")
def schema_overview():
    # expose schemas to the DB viewer if needed
    return {
        "section": Section.model_json_schema(),
        "doc": Doc.model_json_schema(),
    }

# Sections
@app.post("/sections")
def create_section(payload: SectionCreate):
    try:
        section_id = create_document("section", payload)
        return {"id": section_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sections")
def list_sections():
    try:
        items = get_documents("section", {}, None)
        items.sort(key=lambda x: x.get("order", 0))
        return [serialize_doc(i) for i in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Docs
@app.post("/docs")
def create_doc(payload: DocCreate):
    try:
        # ensure section exists
        sec = db["section"].find_one({"_id": ObjectId(payload.section_id)}) if ObjectId.is_valid(payload.section_id) else None
        if not sec:
            raise HTTPException(status_code=400, detail="Section not found")
        data = payload.model_dump()
        data["section_id"] = ObjectId(payload.section_id)
        inserted_id = db["doc"].insert_one({**data}).inserted_id
        return {"id": str(inserted_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/docs")
def list_docs(section_id: Optional[str] = None):
    try:
        query = {}
        if section_id and ObjectId.is_valid(section_id):
            query["section_id"] = ObjectId(section_id)
        items = list(db["doc"].find(query))
        return [serialize_doc(i) for i in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Image upload (stores on disk under /uploads and returns URL)
UPLOAD_DIR = "uploads"
BASE_URL = os.getenv("BASE_URL", "")

os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        filename = file.filename
        path = os.path.join(UPLOAD_DIR, filename)
        # avoid overwrite
        base, ext = os.path.splitext(filename)
        idx = 1
        while os.path.exists(path):
            filename = f"{base}_{idx}{ext}"
            path = os.path.join(UPLOAD_DIR, filename)
            idx += 1
        with open(path, "wb") as f:
            f.write(await file.read())
        # Expose via static
        url = f"/static/{filename}"
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# Test endpoint
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            collections = db.list_collection_names()
            response["collections"] = collections[:10]
            response["database"] = "✅ Connected & Working"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
