"""
File System Service
Handles hierarchical file/folder organization using the Pointer Pattern.
Decouples organizational structure from actual playground configurations.
"""
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from typing import Optional
import logging

from . import firestore_service

logger = logging.getLogger(__name__)

# Collection names
FILE_SYSTEM_COLLECTION = 'file_system'
PLAYGROUNDS_COLLECTION = 'playgrounds'

# Ensure db is available
db = firestore_service.db


def _ensure_db():
    """Ensure database is initialized."""
    if db is None:
        raise RuntimeError(
            "Firestore not initialized. Please check GOOGLE_CLOUD_PROJECT "
            "and GOOGLE_APPLICATION_CREDENTIALS environment variables."
        )


def get_directory_contents(parent_id: str = "root") -> dict:
    """
    Fetches directory contents with enriched bot metadata (Double Fetch pattern).
    
    Args:
        parent_id: The parent folder ID. Defaults to "root" for top-level.
        
    Returns:
        Dict with 'items' and 'breadcrumbs' arrays.
    """
    _ensure_db()
    
    # Step 1: Query file_system for all items with this parent
    fs_query = db.collection(FILE_SYSTEM_COLLECTION).where(
        filter=FieldFilter('parent_id', '==', parent_id)
    )
    fs_docs = fs_query.stream()
    
    items = []
    playground_ids_to_fetch = []
    bot_items_map = {}  # Map playground_id -> item index for merging
    
    for doc in fs_docs:
        data = doc.to_dict()
        item = {
            'fs_id': doc.id,
            'type': data.get('type'),
            'name': data.get('name'),
            'playground_id': data.get('playground_id'),
            'preview': None
        }
        items.append(item)
        
        # Track bots for batch enrichment
        if data.get('type') == 'bot' and data.get('playground_id'):
            playground_ids_to_fetch.append(data.get('playground_id'))
            bot_items_map[data.get('playground_id')] = len(items) - 1
    
    # Step 2: Batch fetch playground data for all bots
    if playground_ids_to_fetch:
        # Firestore 'in' queries are limited to 30 items
        # Split into chunks if needed
        for i in range(0, len(playground_ids_to_fetch), 30):
            chunk = playground_ids_to_fetch[i:i+30]
            playground_refs = [
                db.collection(PLAYGROUNDS_COLLECTION).document(pg_id) 
                for pg_id in chunk
            ]
            playground_docs = db.get_all(playground_refs)
            
            for pg_doc in playground_docs:
                if pg_doc.exists:
                    pg_data = pg_doc.to_dict()
                    item_idx = bot_items_map.get(pg_doc.id)
                    if item_idx is not None:
                        items[item_idx]['preview'] = {
                            'status': pg_data.get('status', 'unknown'),
                            'last_modified': _serialize_timestamp(pg_data.get('last_modified_at'))
                        }
    
    # Step 3: Resolve breadcrumbs
    breadcrumbs = _resolve_breadcrumbs(parent_id)
    
    # Sort items: folders first, then bots, alphabetically within each
    items.sort(key=lambda x: (0 if x['type'] == 'folder' else 1, x['name'].lower()))
    
    return {
        'items': items,
        'breadcrumbs': breadcrumbs
    }


def _resolve_breadcrumbs(current_id: str) -> list:
    """
    Recursively resolves the path from current folder to root.
    
    Args:
        current_id: The current folder ID
        
    Returns:
        List of breadcrumb objects from root to current
    """
    _ensure_db()
    
    breadcrumbs = []
    
    # Always start with root
    if current_id == "root":
        return [{'id': 'root', 'name': 'Root'}]
    
    # Trace path back to root
    visited = set()
    node_id = current_id
    
    while node_id and node_id != "root":
        if node_id in visited:
            logger.error(f"Circular reference detected in breadcrumbs: {node_id}")
            break
        visited.add(node_id)
        
        doc = db.collection(FILE_SYSTEM_COLLECTION).document(node_id).get()
        if not doc.exists:
            logger.warning(f"Breadcrumb node not found: {node_id}")
            break
            
        data = doc.to_dict()
        breadcrumbs.append({
            'id': doc.id,
            'name': data.get('name', 'Unknown')
        })
        node_id = data.get('parent_id')
    
    # Add root and reverse to get correct order
    breadcrumbs.append({'id': 'root', 'name': 'Root'})
    breadcrumbs.reverse()
    
    return breadcrumbs


def create_folder(name: str, parent_id: str = "root") -> dict:
    """
    Creates a new folder in the file system.
    
    Args:
        name: Display name for the folder
        parent_id: Parent folder ID (defaults to root)
        
    Returns:
        The created folder item
    """
    _ensure_db()
    
    # Validate parent exists (unless it's root)
    if parent_id != "root":
        parent_doc = db.collection(FILE_SYSTEM_COLLECTION).document(parent_id).get()
        if not parent_doc.exists:
            raise ValueError(f"Parent folder not found: {parent_id}")
        if parent_doc.to_dict().get('type') != 'folder':
            raise ValueError("Parent must be a folder")
    
    # Create the folder document
    folder_ref = db.collection(FILE_SYSTEM_COLLECTION).document()
    folder_data = {
        'type': 'folder',
        'name': name,
        'parent_id': parent_id,
        'created_at': firestore.SERVER_TIMESTAMP
    }
    folder_ref.set(folder_data)
    
    return {
        'fs_id': folder_ref.id,
        'type': 'folder',
        'name': name,
        'playground_id': None,
        'preview': None
    }


def create_bot_pointer(name: str, playground_id: str, parent_id: str = "root") -> dict:
    """
    Creates a file system pointer for an existing playground.
    This function only handles the organizational hierarchy, not playground creation.
    
    Args:
        name: Display name for the bot in the file system
        playground_id: The ID of the already-created playground entity
        parent_id: Parent folder ID (defaults to root)
        
    Returns:
        The created bot item with fs_id and playground_id
    """
    _ensure_db()
    
    # Validate parent exists (unless it's root)
    if parent_id != "root":
        parent_doc = db.collection(FILE_SYSTEM_COLLECTION).document(parent_id).get()
        if not parent_doc.exists:
            raise ValueError(f"Parent folder not found: {parent_id}")
        if parent_doc.to_dict().get('type') != 'folder':
            raise ValueError("Parent must be a folder")
    
    # Create the file system pointer
    fs_ref = db.collection(FILE_SYSTEM_COLLECTION).document()
    fs_data = {
        'type': 'bot',
        'name': name,
        'parent_id': parent_id,
        'playground_id': playground_id,
        'created_at': firestore.SERVER_TIMESTAMP
    }
    fs_ref.set(fs_data)
    
    logger.info(f"Created bot pointer: {fs_ref.id} -> playground {playground_id}")
    
    return {
        'fs_id': fs_ref.id,
        'type': 'bot',
        'name': name,
        'playground_id': playground_id,
        'preview': {
            'status': 'CREATED',
            'last_modified': None
        }
    }


def move_item(fs_id: str, new_parent_id: str) -> dict:
    """
    Moves an item to a new parent folder.
    
    Args:
        fs_id: The file system ID of the item to move
        new_parent_id: The new parent folder ID
        
    Returns:
        Success status
    """
    _ensure_db()
    
    # Validate item exists
    item_ref = db.collection(FILE_SYSTEM_COLLECTION).document(fs_id)
    item_doc = item_ref.get()
    if not item_doc.exists:
        raise ValueError(f"Item not found: {fs_id}")
    
    # Validate new parent exists (unless it's root)
    if new_parent_id != "root":
        parent_doc = db.collection(FILE_SYSTEM_COLLECTION).document(new_parent_id).get()
        if not parent_doc.exists:
            raise ValueError(f"Target folder not found: {new_parent_id}")
        if parent_doc.to_dict().get('type') != 'folder':
            raise ValueError("Target must be a folder")
        
        # Prevent moving a folder into itself or its descendants
        item_data = item_doc.to_dict()
        if item_data.get('type') == 'folder':
            if _is_descendant(new_parent_id, fs_id):
                raise ValueError("Cannot move a folder into itself or its descendants")
    
    # Update the parent_id
    item_ref.update({
        'parent_id': new_parent_id
    })
    
    return {'status': 'success'}


def _is_descendant(potential_descendant: str, ancestor_id: str) -> bool:
    """
    Checks if potential_descendant is a descendant of ancestor_id.
    Used to prevent circular folder structures.
    """
    _ensure_db()
    
    if potential_descendant == ancestor_id:
        return True
    
    current_id = potential_descendant
    visited = set()
    
    while current_id and current_id != "root":
        if current_id in visited:
            return False  # Circular reference, shouldn't happen
        visited.add(current_id)
        
        if current_id == ancestor_id:
            return True
            
        doc = db.collection(FILE_SYSTEM_COLLECTION).document(current_id).get()
        if not doc.exists:
            return False
        current_id = doc.to_dict().get('parent_id')
    
    return False


def delete_item(fs_id: str) -> None:
    """
    Deletes an item from the file system.
    For bots, also deletes the underlying playground document.
    Folders must be empty to be deleted (returns 409 if not).
    
    Args:
        fs_id: The file system ID of the item to delete
        
    Raises:
        ValueError: If item not found
        PermissionError: If folder is not empty (409 Conflict)
    """
    _ensure_db()
    
    # Get the item
    item_ref = db.collection(FILE_SYSTEM_COLLECTION).document(fs_id)
    item_doc = item_ref.get()
    
    if not item_doc.exists:
        raise ValueError(f"Item not found: {fs_id}")
    
    item_data = item_doc.to_dict()
    
    # If it's a folder, check if empty
    if item_data.get('type') == 'folder':
        children_query = db.collection(FILE_SYSTEM_COLLECTION).where(
            filter=FieldFilter('parent_id', '==', fs_id)
        ).limit(1)
        children = list(children_query.stream())
        
        if children:
            raise PermissionError("Cannot delete non-empty folder")
    
    # If it's a bot, delete the playground too
    batch = db.batch()
    
    if item_data.get('type') == 'bot':
        playground_id = item_data.get('playground_id')
        if playground_id:
            playground_ref = db.collection(PLAYGROUNDS_COLLECTION).document(playground_id)
            batch.delete(playground_ref)
    
    # Delete the file system entry
    batch.delete(item_ref)
    batch.commit()


def rename_item(fs_id: str, new_name: str) -> dict:
    """
    Renames an item in the file system.
    For bots, also updates the playground display_name.
    
    Args:
        fs_id: The file system ID of the item to rename
        new_name: The new name
        
    Returns:
        The updated item
    """
    _ensure_db()
    
    item_ref = db.collection(FILE_SYSTEM_COLLECTION).document(fs_id)
    item_doc = item_ref.get()
    
    if not item_doc.exists:
        raise ValueError(f"Item not found: {fs_id}")
    
    item_data = item_doc.to_dict()
    
    batch = db.batch()
    
    # Update file system name
    batch.update(item_ref, {'name': new_name})
    
    # If it's a bot, also update playground display_name
    if item_data.get('type') == 'bot' and item_data.get('playground_id'):
        playground_ref = db.collection(PLAYGROUNDS_COLLECTION).document(
            item_data.get('playground_id')
        )
        batch.update(playground_ref, {'display_name': new_name})
    
    batch.commit()
    
    return {
        'fs_id': fs_id,
        'type': item_data.get('type'),
        'name': new_name,
        'playground_id': item_data.get('playground_id'),
        'preview': None  # Would need to re-fetch for full preview
    }


def folder_exists(folder_id: str) -> bool:
    """
    Checks if a folder exists.
    
    Args:
        folder_id: The folder ID to check
        
    Returns:
        True if folder exists, False otherwise
    """
    _ensure_db()
    
    if folder_id == "root":
        return True
    
    doc = db.collection(FILE_SYSTEM_COLLECTION).document(folder_id).get()
    return doc.exists and doc.to_dict().get('type') == 'folder'


def _serialize_timestamp(timestamp) -> Optional[str]:
    """Converts Firestore timestamp to ISO string."""
    if timestamp is None:
        return None
    try:
        return timestamp.isoformat()
    except AttributeError:
        return str(timestamp)
