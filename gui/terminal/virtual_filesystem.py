import os
import uuid
from pathlib import Path
from sqlalchemy import and_
from jarvis_integration.internals.db import get_db
from jarvis_integration.models.fileSystem import FileSystem
from jarvis_integration.models.users import Users
from config import SessionManager, JARVIS_DIR, loggers
from typing import List, Tuple, Optional, Dict
from functools import wraps
import time
from datetime import datetime

logger = loggers["DB"]

class VirtualFileSystemError(Exception):
    """Custom exception for VirtualFileSystem errors."""
    pass

def retry_db_operation(max_attempts: int = 3, delay: float = 1):
    """Decorator to retry database operations on failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise VirtualFileSystemError(f"Failed after {max_attempts} attempts: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator

class VirtualFileSystem:
    def __init__(self):
        """Initialize the virtual file system for a specific user.

        Attributes:
            user_model: User model instance.
            user_id: User ID as string.
            current_dir_id: ID of the current directory.
            path_cache: Cached current directory path.
            undo_stack: Stack for undoable actions.
            redo_stack: Stack for redoable actions.
        """
        session=SessionManager()
        session.load_session()
        self.user_model = Users.get_user_by_email(session.get_email())
        self.user_id: str = self.user_model.id
        self.current_dir_id: Optional[str] = None
        self.path_cache: Optional[str] = None
        self.undo_stack: List[Tuple[str, Dict]] = []
        self.redo_stack: List[Tuple[str, Dict]] = []
        self._set_user_root()

    def _get_session(self):
        """Get a new database session context manager.

        Returns:
            Context manager for database session.
        """
        return get_db()

    @retry_db_operation()
    def _set_user_root(self) -> None:
        """Set up user-specific root directory.

        Raises:
            VirtualFileSystemError: If root directory setup fails.
        """
        try:
            with self._get_session() as db:
                root_name = f"{self.user_model.name}" if self.user_id else "/"
                root = db.query(FileSystem).filter(
                    and_(FileSystem.name == root_name, FileSystem.user_id == self.user_id, FileSystem.is_dir == True)
                ).first()
                if not root:
                    root = FileSystem(
                        id=str(uuid.uuid4()),
                        user_id=self.user_id,
                        name=root_name,
                        is_dir=True
                    )
                    db.add(root)
                    db.commit()
                self.current_dir_id = root.id
                self.path_cache = None
        except Exception as e:
            logger.error(f"Error setting user root for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to set user root: {e}")

    @retry_db_operation()
    def get_current_dir(self) -> str:
        """Get the current virtual directory path.

        Returns:
            str: The absolute path of the current directory.

        Raises:
            VirtualFileSystemError: If the current directory ID is invalid or database access fails.
        """
        if self.path_cache:
            return self.path_cache
        try:
            with self._get_session() as db:
                path = []
                current_id = self.current_dir_id
                while current_id:
                    node = db.query(FileSystem).filter_by(id=current_id, user_id=self.user_id).first()
                    if not node:
                        raise VirtualFileSystemError("Invalid current directory ID")
                    if node.name != f"/user_{self.user_id}" and node.name != "/":
                        path.append(node.name)
                    current_id = node.parent_id
                self.path_cache = "/" + "/".join(reversed(path)) if path else "/"
                return self.path_cache
        except Exception as e:
            logger.error(f"Error getting current directory for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to get current directory: {e}")

    @retry_db_operation()
    def list_dir(self) -> List[Tuple[str, bool]]:
        """List contents of the current directory.

        Returns:
            List[Tuple[str, bool]]: List of (name, is_dir) tuples for directory contents.

        Raises:
            VirtualFileSystemError: If listing the directory fails.
        """
        try:
            with self._get_session() as db:
                nodes = db.query(FileSystem).filter(
                    and_(FileSystem.parent_id == self.current_dir_id, FileSystem.user_id == self.user_id)
                ).all()
                return [(node.name, node.is_dir) for node in nodes]
        except Exception as e:
            logger.error(f"Error listing directory for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to list directory: {e}")

    def validate_path_component(self, name: str) -> None:
        """Validate a path component (file or directory name).

        Args:
            name: Name to validate.

        Raises:
            VirtualFileSystemError: If the name is invalid.
        """
        if not name:
            raise VirtualFileSystemError("Name cannot be empty")
        if "/" in name or name in [".", ".."]:
            raise VirtualFileSystemError(f"Invalid name: {name}. Cannot contain '/' or be '.' or '..'")

    @retry_db_operation()
    def change_dir(self, path: str) -> None:
        """Change the current directory.

        Args:
            path: Path to change to (absolute or relative).

        Raises:
            VirtualFileSystemError: If the path is invalid or directory change fails.
        """
        if not path:
            return
        try:
            with self._get_session() as db:
                if path == "/":
                    root = db.query(FileSystem).filter(
                        and_(
                            FileSystem.name == (f"/user_{self.user_id}" if self.user_id else "/"),
                            FileSystem.is_dir == True,
                            FileSystem.user_id == self.user_id
                        )
                    ).first()
                    if not root:
                        raise VirtualFileSystemError("Root directory not found")
                    self.current_dir_id = root.id
                    self.path_cache = None
                    return

                if path == "..":
                    current = db.query(FileSystem).filter_by(id=self.current_dir_id, user_id=self.user_id).first()
                    if current and current.parent_id:
                        self.current_dir_id = current.parent_id
                        self.path_cache = None
                    return

                parts = path.strip("/").split("/") if path.startswith("/") else path.split("/")
                current_id = self.current_dir_id
                if path.startswith("/"):
                    root = db.query(FileSystem).filter(
                        and_(
                            FileSystem.name == (f"/user_{self.user_id}" if self.user_id else "/"),
                            FileSystem.is_dir == True,
                            FileSystem.user_id == self.user_id
                        )
                    ).first()
                    if not root:
                        raise VirtualFileSystemError("Root directory not found")
                    current_id = root.id

                for part in parts:
                    if not part:
                        continue
                    self.validate_path_component(part)
                    node = db.query(FileSystem).filter(
                        and_(
                            FileSystem.parent_id == current_id,
                            FileSystem.name == part,
                            FileSystem.is_dir == True,
                            FileSystem.user_id == self.user_id
                        )
                    ).first()
                    if not node:
                        raise VirtualFileSystemError(f"{path}: No such directory")
                    current_id = node.id

                self.current_dir_id = current_id
                self.path_cache = None
        except Exception as e:
            logger.error(f"Error changing directory to {path} for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to change directory to {path}: {e}")

    @retry_db_operation()
    def create_dir(self, name: str) -> None:
        """Create a directory.

        Args:
            name: Name of the directory to create.

        Raises:
            VirtualFileSystemError: If the directory name is invalid or creation fails.
        """
        self.validate_path_component(name)
        try:
            with self._get_session() as db:
                if db.query(FileSystem).filter(
                    and_(
                        FileSystem.parent_id == self.current_dir_id,
                        FileSystem.name == name,
                        FileSystem.user_id == self.user_id
                    )
                ).first():
                    raise VirtualFileSystemError(f"{name}: Directory exists")
                dir_id = str(uuid.uuid4())
                new_dir = FileSystem(
                    id=dir_id,
                    user_id=self.user_id,
                    name=name,
                    parent_id=self.current_dir_id,
                    is_dir=True
                )
                db.add(new_dir)
                db.commit()
                self.undo_stack.append(('create_dir', {'id': dir_id, 'name': name, 'parent_id': self.current_dir_id}))
                self.redo_stack.clear()
        except Exception as e:
            logger.error(f"Error creating directory {name} for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to create directory {name}: {e}")

    @retry_db_operation()
    def create_file(self, name: str) -> None:
        """Create an empty file with the specified or default extension.

        Args:
            name: Name of the file to create.

        Raises:
            VirtualFileSystemError: If the file name is invalid or creation fails.
        """
        self.validate_path_component(name)
        try:
            with self._get_session() as db:
                if db.query(FileSystem).filter(
                    and_(
                        FileSystem.parent_id == self.current_dir_id,
                        FileSystem.name == name,
                        FileSystem.user_id == self.user_id
                    )
                ).first():
                    raise VirtualFileSystemError(f"{name}: File exists")
                extension = os.path.splitext(name)[1] or ".txt"
                folder_path = os.path.join(JARVIS_DIR, "data", "files", self.user_id or "global")
                os.makedirs(folder_path, exist_ok=True)
                file_id = str(uuid.uuid4())
                real_path = os.path.join(folder_path, f"{file_id}{extension}")
                Path(real_path).write_text("")
                os.chmod(real_path, 0o600)
                new_file = FileSystem(
                    id=file_id,
                    user_id=self.user_id,
                    name=name,
                    parent_id=self.current_dir_id,
                    is_dir=False,
                    real_path=real_path
                )
                db.add(new_file)
                db.commit()
                self.undo_stack.append(('create_file', {'id': file_id, 'name': name, 'parent_id': self.current_dir_id, 'real_path': real_path}))
                self.redo_stack.clear()
        except Exception as e:
            logger.error(f"Error creating file {name} for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to create file {name}: {e}")

    @retry_db_operation()
    def write_file(self, name: str, content: str) -> None:
        """Write content to a file.

        Args:
            name: Name of the file to write to.
            content: Content to write.

        Raises:
            VirtualFileSystemError: If the file does not exist, is a directory, or writing fails.
        """
        self.validate_path_component(name)
        try:
            with self._get_session() as db:
                node = db.query(FileSystem).filter(
                    and_(
                        FileSystem.parent_id == self.current_dir_id,
                        FileSystem.name == name,
                        FileSystem.is_dir == False,
                        FileSystem.user_id == self.user_id
                    )
                ).first()
                if not node:
                    raise VirtualFileSystemError(f"{name}: No such file")
                if not node.real_path:
                    raise VirtualFileSystemError(f"{name}: Invalid file path")
                old_content = Path(node.real_path).read_text()
                Path(node.real_path).write_text(content)
                self.undo_stack.append(('write_file', {'id': node.id, 'name': name, 'old_content': old_content, 'new_content': content}))
                self.redo_stack.clear()
        except Exception as e:
            logger.error(f"Error writing to file {name} for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to write to file {name}: {e}")

    @retry_db_operation()
    def remove(self, name: str) -> None:
        """Remove a file or empty directory.

        Args:
            name: Name of the file or directory to remove.

        Raises:
            VirtualFileSystemError: If the item does not exist or directory is not empty.
        """
        self.validate_path_component(name)
        try:
            with self._get_session() as db:
                node = db.query(FileSystem).filter(
                    and_(
                        FileSystem.parent_id == self.current_dir_id,
                        FileSystem.name == name,
                        FileSystem.user_id == self.user_id
                    )
                ).first()
                if not node:
                    raise VirtualFileSystemError(f"{name}: No such file or directory")
                if node.is_dir:
                    if db.query(FileSystem).filter(
                        and_(FileSystem.parent_id == node.id, FileSystem.user_id == self.user_id)
                    ).count() > 0:
                        raise VirtualFileSystemError(f"{name}: Directory not empty")
                old_real_path = node.real_path if not node.is_dir else None
                if old_real_path and os.path.exists(old_real_path):
                    os.remove(old_real_path)
                db.delete(node)
                db.commit()
                self.undo_stack.append((
                    'remove',
                    {
                        'id': node.id,
                        'name': name,
                        'parent_id': self.current_dir_id,
                        'is_dir': node.is_dir,
                        'real_path': old_real_path
                    }
                ))
                self.redo_stack.clear()
        except Exception as e:
            logger.error(f"Error removing {name} for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to remove {name}: {e}")

    @retry_db_operation()
    def remove_recursive(self, name: str) -> None:
        """Recursively remove a directory and its contents.

        Args:
            name: Name of the directory to remove.

        Raises:
            VirtualFileSystemError: If the directory does not exist or removal fails.
        """
        self.validate_path_component(name)
        try:
            with self._get_session() as db:
                node = db.query(FileSystem).filter(
                    and_(
                        FileSystem.parent_id == self.current_dir_id,
                        FileSystem.name == name,
                        FileSystem.is_dir == True,
                        FileSystem.user_id == self.user_id
                    )
                ).first()
                if not node:
                    raise VirtualFileSystemError(f"{name}: No such directory")
                self._delete_recursive(db, node.id)
                db.delete(node)
                db.commit()
                self.undo_stack.append(('remove_recursive', {'id': node.id, 'name': name, 'parent_id': self.current_dir_id}))
                self.redo_stack.clear()
        except Exception as e:
            logger.error(f"Error recursively removing {name} for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to recursively remove {name}: {e}")

    def _delete_recursive(self, db, node_id: str) -> None:
        """Helper method to delete directory contents recursively.

        Args:
            db: Database session.
            node_id: ID of the node to delete recursively.
        """
        children = db.query(FileSystem).filter(
            and_(FileSystem.parent_id == node_id, FileSystem.user_id == self.user_id)
        ).all()
        for child in children:
            if child.is_dir:
                self._delete_recursive(db, child.id)
            elif child.real_path and os.path.exists(child.real_path):
                os.remove(child.real_path)
            db.delete(child)

    @retry_db_operation()
    def read_file(self, name: str) -> str:
        """Read file contents.

        Args:
            name: Name of the file to read.

        Returns:
            str: Contents of the file.

        Raises:
            VirtualFileSystemError: If the file does not exist or reading fails.
        """
        self.validate_path_component(name)
        try:
            with self._get_session() as db:
                node = db.query(FileSystem).filter(
                    and_(
                        FileSystem.parent_id == self.current_dir_id,
                        FileSystem.name == name,
                        FileSystem.is_dir == False,
                        FileSystem.user_id == self.user_id
                    )
                ).first()
                if not node:
                    raise VirtualFileSystemError(f"{name}: No such file")
                if not node.real_path:
                    raise VirtualFileSystemError(f"{name}: Invalid file path")
                return Path(node.real_path).read_text()
        except Exception as e:
            logger.error(f"Error reading file {name} for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to read file {name}: {e}")

    @retry_db_operation()
    def get_file_metadata(self, name: str) -> Dict[str, any]:
        """Get metadata for a file or directory.

        Args:
            name: Name of the file or directory.

        Returns:
            Dict[str, any]: Dictionary containing size (bytes) and last modified time.

        Raises:
            VirtualFileSystemError: If the item does not exist or metadata retrieval fails.
        """
        self.validate_path_component(name)
        try:
            with self._get_session() as db:
                node = db.query(FileSystem).filter(
                    and_(
                        FileSystem.parent_id == self.current_dir_id,
                        FileSystem.name == name,
                        FileSystem.user_id == self.user_id
                    )
                ).first()
                if not node:
                    raise VirtualFileSystemError(f"{name}: No such file or directory")
                metadata = {'is_dir': node.is_dir}
                if not node.is_dir and node.real_path and os.path.exists(node.real_path):
                    stats = os.stat(node.real_path)
                    metadata['size'] = stats.st_size
                    metadata['last_modified'] = datetime.fromtimestamp(stats.st_mtime).isoformat()
                return metadata
        except Exception as e:
            logger.error(f"Error getting metadata for {name} for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to get metadata for {name}: {e}")

    @retry_db_operation()
    def complete_path(self, path: str, directories_only: bool = False) -> List[str]:
        """Complete path for tab completion.

        Args:
            path: Partial path to complete.
            directories_only: If True, return only directories.

        Returns:
            List[str]: List of matching paths.

        Raises:
            VirtualFileSystemError: If path completion fails.
        """
        try:
            with self._get_session() as db:
                if path.startswith("/"):
                    parts = path.strip("/").split("/")
                    root = db.query(FileSystem).filter(
                        and_(
                            FileSystem.name == (f"/user_{self.user_id}" if self.user_id else "/"),
                            FileSystem.is_dir == True,
                            FileSystem.user_id == self.user_id
                        )
                    ).first()
                    parent_id = root.id if root else None
                    prefix = "/"
                else:
                    parts = path.split("/")
                    parent_id = self.current_dir_id
                    prefix = ""

                if not parent_id:
                    return []

                if len(parts) > 1:
                    for part in parts[:-1]:
                        if not part:
                            continue
                        node = db.query(FileSystem).filter(
                            and_(
                                FileSystem.parent_id == parent_id,
                                FileSystem.name == part,
                                FileSystem.is_dir == True,
                                FileSystem.user_id == self.user_id
                            )
                        ).first()
                        if not node:
                            return []
                        parent_id = node.id
                    last_part = parts[-1]
                else:
                    last_part = parts[0]

                query = db.query(FileSystem.name).filter(
                    and_(
                        FileSystem.parent_id == parent_id,
                        FileSystem.name.ilike(f"{last_part}%"),
                        FileSystem.user_id == self.user_id
                    )
                )
                if directories_only:
                    query = query.filter(FileSystem.is_dir == True)
                matches = [prefix + "/".join(parts[:-1] + [name[0]]) if parts[:-1] else name[0] for name in query.all()]
                return matches
        except Exception as e:
            logger.error(f"Error completing path {path} for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to complete path {path}: {e}")

    @retry_db_operation()
    def undo(self) -> bool:
        """Undo the last file system operation.

        Returns:
            bool: True if undo was successful, False if no actions to undo.

        Raises:
            VirtualFileSystemError: If the undo operation fails.
        """
        if not self.undo_stack:
            return False
        try:
            with self._get_session() as db:
                action, data = self.undo_stack.pop()
                if action == 'create_dir':
                    node = db.query(FileSystem).filter_by(id=data['id'], user_id=self.user_id).first()
                    if node:
                        db.delete(node)
                        db.commit()
                    self.redo_stack.append((action, data))
                elif action == 'create_file':
                    node = db.query(FileSystem).filter_by(id=data['id'], user_id=self.user_id).first()
                    if node:
                        if node.real_path and os.path.exists(node.real_path):
                            os.remove(node.real_path)
                        db.delete(node)
                        db.commit()
                    self.redo_stack.append((action, data))
                elif action == 'remove':
                    node = FileSystem(
                        id=data['id'],
                        user_id=self.user_id,
                        name=data['name'],
                        parent_id=data['parent_id'],
                        is_dir=data['is_dir'],
                        real_path=data['real_path']
                    )
                    if data['real_path'] and not data['is_dir']:
                        Path(data['real_path']).write_text("")
                        os.chmod(data['real_path'], 0o600)
                    db.add(node)
                    db.commit()
                    self.redo_stack.append((action, data))
                elif action == 'write_file':
                    node = db.query(FileSystem).filter_by(id=data['id'], user_id=self.user_id).first()
                    if node and node.real_path:
                        Path(node.real_path).write_text(data['old_content'])
                    self.redo_stack.append((action, data))
                elif action == 'remove_recursive':
                    # Simplified: restore directory without contents
                    node = FileSystem(
                        id=data['id'],
                        user_id=self.user_id,
                        name=data['name'],
                        parent_id=data['parent_id'],
                        is_dir=True
                    )
                    db.add(node)
                    db.commit()
                    self.redo_stack.append((action, data))
                self.path_cache = None
                return True
        except Exception as e:
            logger.error(f"Error undoing action for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to undo action: {e}")

    @retry_db_operation()
    def redo(self) -> bool:
        """Redo the last undone file system operation.

        Returns:
            bool: True if redo was successful, False if no actions to redo.

        Raises:
            VirtualFileSystemError: If the redo operation fails.
        """
        if not self.redo_stack:
            return False
        try:
            with self._get_session() as db:
                action, data = self.redo_stack.pop()
                if action == 'create_dir':
                    new_dir = FileSystem(
                        id=data['id'],
                        user_id=self.user_id,
                        name=data['name'],
                        parent_id=data['parent_id'],
                        is_dir=True
                    )
                    db.add(new_dir)
                    db.commit()
                    self.undo_stack.append((action, data))
                elif action == 'create_file':
                    new_file = FileSystem(
                        id=data['id'],
                        user_id=self.user_id,
                        name=data['name'],
                        parent_id=data['parent_id'],
                        is_dir=False,
                        real_path=data['real_path']
                    )
                    if data['real_path']:
                        Path(data['real_path']).write_text("")
                        os.chmod(data['real_path'], 0o600)
                    db.add(new_file)
                    db.commit()
                    self.undo_stack.append((action, data))
                elif action == 'remove':
                    node = db.query(FileSystem).filter_by(id=data['id'], user_id=self.user_id).first()
                    if node:
                        if node.real_path and os.path.exists(node.real_path):
                            os.remove(node.real_path)
                        db.delete(node)
                        db.commit()
                    self.undo_stack.append((action, data))
                elif action == 'write_file':
                    node = db.query(FileSystem).filter_by(id=data['id'], user_id=self.user_id).first()
                    if node and node.real_path:
                        Path(node.real_path).write_text(data['new_content'])
                    self.undo_stack.append((action, data))
                elif action == 'remove_recursive':
                    node = db.query(FileSystem).filter_by(id=data['id'], user_id=self.user_id).first()
                    if node:
                        self._delete_recursive(db, node.id)
                        db.delete(node)
                        db.commit()
                    self.undo_stack.append((action, data))
                self.path_cache = None
                return True
        except Exception as e:
            logger.error(f"Error redoing action for user {self.user_id}: {e}")
            raise VirtualFileSystemError(f"Failed to redo action: {e}")

    def close(self) -> None:
        """Close database session. No action needed as get_db() manages sessions."""
        pass

    def __del__(self) -> None:
        """Ensure no session cleanup is needed."""
        pass

    def __enter__(self):
        """Support context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """No session cleanup needed."""
        pass