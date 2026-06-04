
import json
from app.config import get_settings
from pyzotero import zotero

settings = get_settings()
client = zotero.Zotero(
    settings.zotero_user_id,
    settings.zotero_library_type,
    settings.zotero_api_key,
)

collections = client.all_collections()
print("collection_count", len(collections))

for item in collections:
    data = item.get("data", {}) if isinstance(item, dict) else {}
    key = data.get("key") or item.get("key")
    name = data.get("name")
    if "TEMP_TRASH_TEST" in str(name):
        print("MATCH")
        print(json.dumps(item, ensure_ascii=False, indent=2, default=str))
