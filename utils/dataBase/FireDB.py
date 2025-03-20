import os
import datetime
import json
import jsonpickle
import firebase_admin
from firebase_admin import db, credentials
from utils.log import logger
from config import DB_SESSION_INFO


class FireBaseDB:
    """
    Firebase database interface for managing user sessions, admin users, and blocked users.
    Provides methods for user management, chat history, and system instruction handling.
    """
    
    # Database references
    DB_URL = "https://ares-rkbot-default-rtdb.asia-southeast1.firebasedatabase.app/"
    
    def __init__(self):
        """Initialize Firebase connection and load user caches."""
        try:
            # Initialize with credentials from config
            cred = credentials.Certificate(DB_SESSION_INFO)
            firebase_admin.initialize_app(cred, {"databaseURL": self.DB_URL})
            
            # Set up database references
            self.db = db.reference("/users_sessions")
            self.blocked_users_db = db.reference("/Blocked_user")
            self.admin_users_db = db.reference("/Admin_users")
            
            # Initialize caches
            self.blocked_users_cache = set()
            self.admin_users_cache = set()
            
            # Load initial data
            self._load_blocked_users()
            self._load_admin_users()
            logger.info("Firebase DB initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise ConnectionError(f"Could not connect to Firebase: {e}")

    def user_exists(self, user_id):
        """
        Check if a user exists in the database.
        
        Args:
            user_id (str): The user ID to check
            
        Returns:
            dict or None: User data if exists, None otherwise
        
        Raises:
            ValueError: If there's an error checking the user
        """
        try:
            return db.reference(f"/users_sessions/{user_id}").get()
        except Exception as e:
            logger.error(f"Error checking if user {user_id} exists: {e}")
            raise ValueError(f"Error checking for user: {e}")

    def create_user(self, user_id):
        """
        Create a new user in the database.
        
        Args:
            user_id (str): The user ID to create
            
        Raises:
            ValueError: If user already exists or creation fails
        """
        try:
            user_data = self.user_exists(user_id)
            if user_data:
                logger.warning(f"Attempted to create existing user: {user_id}")
                raise ValueError(f"User with ID '{user_id}' already exists!")
            
            # Create user with ISO 8601 timestamp
            now = datetime.datetime.now()
            formatted_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            conversation = {
                "chat_session": "{}",  # Initialize as empty JSON string
                "date": formatted_time,
                "system_instruction": "default"
            }
            
            db.reference("/users_sessions").update({user_id: conversation})
            logger.info(f"Created new user: {user_id}")
        except Exception as e:
            if not isinstance(e, ValueError):
                logger.error(f"Failed to create user {user_id}: {e}")
                raise ValueError(f"Failed to create user: {e}")
            raise

    def extract_history(self, user_id):
        """
        Extract chat history for a user.
        
        Args:
            user_id (str): The user ID
            
        Returns:
            dict: The chat history
            
        Raises:
            ValueError: If user not found or data access error
        """
        try:
            user_data = self.user_exists(user_id)
            if not user_data:
                logger.warning(f"Attempted to extract history for non-existent user: {user_id}")
                raise ValueError(f"User with ID '{user_id}' not found")

            chat_session = user_data.get("chat_session")
            if not chat_session:
                logger.info(f"Empty chat history for user {user_id}")
                return {}
                
            return jsonpickle.decode(chat_session)
        except Exception as e:
            if not isinstance(e, ValueError):
                logger.error(f"Error extracting history for user {user_id}: {e}")
                raise ValueError(f"Error accessing user data or conversation: {e}")
            raise

    def chat_history_add(self, user_id, history=None):
        """
        Update chat history for a user.
        
        Args:
            user_id (str): The user ID
            history (list): The chat history to store, defaults to empty list
            
        Raises:
            ValueError: If update fails
        """
        if history is None:
            history = []
            
        try:
            encoded_history = jsonpickle.encode(history, unpicklable=True)
            db.reference(f"/users_sessions/{user_id}").update({"chat_session": encoded_history})
            logger.debug(f"Updated chat history for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating chat history for user {user_id}: {e}")
            raise ValueError(f"Error updating chat history: {e}")
    
    def extract_instruction(self, user_id):
        """
        Get the system instruction for a user.
        
        Args:
            user_id (str): The user ID
            
        Returns:
            str: The system instruction
            
        Raises:
            ValueError: If user not found
        """
        try:
            user_data = self.user_exists(user_id)
            if not user_data:
                logger.warning(f"Attempted to extract instruction for non-existent user: {user_id}")
                raise ValueError(f"User with ID '{user_id}' not found")

            return user_data.get("system_instruction", "default")
        except Exception as e:
            if not isinstance(e, ValueError):
                logger.error(f"Error extracting instruction for user {user_id}: {e}")
                raise ValueError(f"Error accessing user instruction: {e}")
            raise

    def update_instruction(self, user_id, new_instruction="default"):
        """
        Update the system instruction for a user.
        
        Args:
            user_id (str): The user ID
            new_instruction (str): The new system instruction
            
        Raises:
            ValueError: If update fails
        """
        try:
            db.reference(f"/users_sessions/{user_id}").update({"system_instruction": new_instruction})
            logger.info(f"Updated instruction for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating instruction for user {user_id}: {e}")
            raise ValueError(f"Error updating instruction: {e}")

    def info(self, user_id):
        """
        Get formatted information about a user.
        
        Args:
            user_id (str): The user ID
            
        Returns:
            str: Formatted user information
            
        Raises:
            ValueError: If user not found
        """
        try:
            user_data = self.user_exists(user_id)
            if not user_data:
                logger.warning(f"Attempted to get info for non-existent user: {user_id}")
                raise ValueError(f"User with ID '{user_id}' not found")
            
            is_admin = self.is_admin(user_id)
            is_blocked = self.is_user_blocked(user_id)
            
            return f"""
User Information:
----------------
User ID:         {user_id}
Admin Status:    {"Yes" if is_admin else "No"}
Blocked Status:  {"Yes" if is_blocked else "No"}
Creation Date:   {user_data.get("date", "Unknown")}
System Prompt:   {user_data.get("system_instruction", "default")}
"""
        except Exception as e:
            if not isinstance(e, ValueError):
                logger.error(f"Error getting info for user {user_id}: {e}")
                raise ValueError(f"Error retrieving user information: {e}")
            raise

    def get_usernames(self):
        """
        Get all usernames from the database.
        
        Returns:
            list: List of usernames
        """
        try:
            users_sessions = self.db.get()
            if users_sessions:
                usernames = list(users_sessions.keys())
                logger.info(f"Retrieved {len(usernames)} usernames")
                return usernames
            else:
                logger.info("No user sessions found")
                return []
        except Exception as e:
            logger.error(f"Error retrieving usernames: {e}")
            return []

    def _load_blocked_users(self):
        """Load blocked users into cache."""
        try:
            blocked_users = self.blocked_users_db.get() or {}
            self.blocked_users_cache = set(blocked_users.keys())
            logger.info(f"Loaded {len(self.blocked_users_cache)} blocked users into cache")
        except Exception as e:
            logger.error(f"Error loading blocked users: {e}")
            self.blocked_users_cache = set()

    def _load_admin_users(self):
        """Load admin users into cache."""
        try:
            admin_users = self.admin_users_db.get() or {}
            self.admin_users_cache = set(admin_users.keys())
            logger.info(f"Loaded {len(self.admin_users_cache)} admin users into cache")
        except Exception as e:
            logger.error(f"Error loading admin users: {e}")
            self.admin_users_cache = set()

    def is_admin(self, user_id):
        """
        Check if a user is an admin.
        
        Args:
            user_id (str): The user ID
            
        Returns:
            bool: True if admin, False otherwise
        """
        return user_id in self.admin_users_cache

    def add_admin(self, user_id):
        """
        Add a user as admin.
        
        Args:
            user_id (str): The user ID to add as admin
        """
        try:
            self.admin_users_db.update({user_id: True})
            self.admin_users_cache.add(user_id)
            logger.info(f"Added user {user_id} as admin")
        except Exception as e:
            logger.error(f"Error adding admin user {user_id}: {e}")
            raise ValueError(f"Failed to add admin: {e}")

    def remove_admin(self, user_id):
        """
        Remove admin privileges from a user.
        
        Args:
            user_id (str): The user ID to remove from admins
        """
        try:
            self.admin_users_db.child(user_id).delete()
            self.admin_users_cache.discard(user_id)
            logger.info(f"Removed user {user_id} from admins")
        except Exception as e:
            logger.error(f"Error removing admin user {user_id}: {e}")
            raise ValueError(f"Failed to remove admin: {e}")

    def block_user(self, user_id):
        """
        Block a user.
        
        Args:
            user_id (str): The user ID to block
        """
        try:
            self.blocked_users_db.update({user_id: True})
            self.blocked_users_cache.add(user_id)
            logger.info(f"Blocked user {user_id}")
        except Exception as e:
            logger.error(f"Error blocking user {user_id}: {e}")
            raise ValueError(f"Failed to block user: {e}")

    def unblock_user(self, user_id):
        """
        Unblock a user.
        
        Args:
            user_id (str): The user ID to unblock
        """
        try:
            self.blocked_users_db.child(user_id).delete()
            self.blocked_users_cache.discard(user_id)
            logger.info(f"Unblocked user {user_id}")
        except Exception as e:
            logger.error(f"Error unblocking user {user_id}: {e}")
            raise ValueError(f"Failed to unblock user: {e}")

    def is_user_blocked(self, user_id):
        """
        Check if a user is blocked.
        
        Args:
            user_id (str): The user ID to check
            
        Returns:
            bool: True if blocked, False otherwise
        """
        return user_id in self.blocked_users_cache

    def refresh_caches(self):
        """Refresh both admin and blocked user caches."""
        self._load_blocked_users()
        self._load_admin_users()
        logger.info("User caches refreshed")


# Initialize database singleton for easy import and use
logger.info("Initializing Firebase Database...")
DB = FireBaseDB()