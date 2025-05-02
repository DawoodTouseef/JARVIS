import os
import uuid
from pathlib import Path
from sqlalchemy import and_
from jarvis_integration.internals.db import get_db
from jarvis_integration.models.fileSystem import FileSystem
from jarvis_integration.models.users import Users
from config import SessionManager, JARVIS_DIR, loggers
from typing import List, Tuple

logger = loggers["DB"]

class VirtualFileSystemError(Exception):
    """Custom exception for VirtualFileSystem errors."""
    pass

class VirtualFileSystem:
    def __init__(self):
        """Initialize the virtual file system for a specific user."""

        user = SessionManager()
        user.load_session()
        email = user.get_email()
        self.user_model = Users.get_user_by_email(email)
        self.user_id = self.user_model.id
        self.current_dir_id = None
        self._set_user_root()

    def _get_session(self):
        """Get a new database session context manager."""
        return get_db()

    def _set_user_root(self):
        """Set up user-specific root directory."""
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
        except Exception as e:
            logger.error(f"Error setting user root: {e}")
            raise VirtualFileSystemError(f"Failed to set user root: {e}")

    def get_current_dir(self) -> str:
        """Get current virtual directory path."""
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
                return "/" + "/".join(reversed(path)) if path else "/"
        except Exception as e:
            logger.error(f"Error getting current directory: {e}")
            raise VirtualFileSystemError(f"Failed to get current directory: {e}")

    def list_dir(self) -> List[Tuple[str, bool]]:
        """List contents of current directory."""
        try:
            with self._get_session() as db:
                nodes = db.query(FileSystem).filter(
                    and_(FileSystem.parent_id == self.current_dir_id, FileSystem.user_id == self.user_id)
                ).all()
                return [(node.name, node.is_dir) for node in nodes]
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
            raise VirtualFileSystemError(f"Failed to list directory: {e}")

    def change_dir(self, path: str):
        """Change current directory."""
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
                    return

                if path == "..":
                    current = db.query(FileSystem).filter_by(id=self.current_dir_id, user_id=self.user_id).first()
                    if current and current.parent_id:
                        self.current_dir_id = current.parent_id
                    return

                if path.startswith("/"):
                    parts = path.strip("/").split("/")
                    current = db.query(FileSystem).filter(
                        and_(
                            FileSystem.name == (f"/user_{self.user_id}" if self.user_id else "/"),
                            FileSystem.is_dir == True,
                            FileSystem.user_id == self.user_id
                        )
                    ).first()
                    if not current:
                        raise VirtualFileSystemError("Root directory not found")
                    current_id = current.id
                else:
                    parts = path.split("/")
                    current_id = self.current_dir_id

                for part in parts:
                    if not part:
                        continue
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
        except Exception as e:
            logger.error(f"Error changing directory: {e}")
            raise VirtualFileSystemError(f"Failed to change directory: {e}")

    def create_dir(self, name: str):
        """Create a directory."""
        if not name or "/" in name or name in [".", ".."]:
            raise VirtualFileSystemError("Invalid directory name")
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
                new_dir = FileSystem(
                    id=str(uuid.uuid4()),
                    user_id=self.user_id,
                    name=name,
                    parent_id=self.current_dir_id,
                    is_dir=True
                )
                db.add(new_dir)
                db.commit()
        except Exception as e:
            logger.error(f"Error creating directory: {e}")
            raise VirtualFileSystemError(f"Failed to create directory: {e}")

    def create_file(self, name: str):
        """Create an empty file with the same or default extension."""
        if not name or "/" in name or name in [".", ".."]:
            raise VirtualFileSystemError("Invalid file name")
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
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            raise VirtualFileSystemError(f"Failed to create file: {e}")

    def remove(self, name: str):
        """Remove a file or directory."""
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
                else:
                    if node.real_path and os.path.exists(node.real_path):
                        os.remove(node.real_path)

                db.delete(node)
                db.commit()
        except Exception as e:
            logger.error(f"Error removing item: {e}")
            raise VirtualFileSystemError(f"Failed to remove {name}: {e}")

    def read_file(self, name: str) -> str:
        """Read file contents."""
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
                return Path(node.real_path).read_text()
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise VirtualFileSystemError(f"Failed to read file {name}: {e}")

    def complete_path(self, path: str, directories_only: bool = False) -> List[str]:
        """Complete path for tab completion."""
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
            logger.error(f"Error completing path: {e}")
            return []

    def close(self):
        """Close database session."""
        pass  # No session to close, as get_db() manages it

    def __del__(self):
        """Ensure no session cleanup is needed."""
        pass

    def __enter__(self):
        """Support context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """No session cleanup needed."""
        pass