import os
import datetime
import json
import jsonpickle
import firebase_admin
from firebase_admin import db, credentials
from utils.log import logger
from config import DB_SESSION_INFO


class FireBaseDB:
    """Firebase Database Manager for handling user sessions, admin users, and blocked users."""
    
    DATABASE_URL = "https://ares-rkbot-default-rtdb.asia-southeast1.firebasedatabase.app/"
    
    def __init__(self):
        try:
            # Use proper error handling for credential loading
            cred = credentials.Certificate(DB_SESSION_INFO)
            firebase_admin.initialize_app(cred, {"databaseURL": self.DATABASE_URL})
            
            # Initialize database references
            self.db = db.reference("/users_sessions")
            self.INFO_DB = db.reference("/Blocked_user")
            self.INFO_ADMIN = db.reference("/Admin_users")
            
            # Cache for performance
            self.blocked_users_cache = set()
            self.admins_users = set()
            
            # Load user data into cache
            self._load_blocked_users()
            self._load_admin_users()
            logger.info("Firebase Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise RuntimeError(f"Firebase initialization failed: {e}")

    def user_exists(self, userId):
        """Check if a user exists in the database.
        
        Args:
            userId (str): The user ID to check
            
        Returns:
            dict: User data if exists, None otherwise
            
        Raises:
            ValueError: If there's an error checking the user
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        try:
            return db.reference(f"/users_sessions/{userId}").get()
        except Exception as e:
            logger.error(f"Error checking user '{userId}': {e}")
            raise ValueError(f"Error while checking for user: {e}")

    def create_user(self, userId):
        """Create a new user in the database.
        
        Args:
            userId (str): The user ID to create
            
        Raises:
            ValueError: If user already exists or creation fails
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        user_data = self.user_exists(userId)
        if user_data:
            raise ValueError(f"User with ID '{userId}' already exists!")
        
        try:
            now = datetime.datetime.now()
            formatted_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")  # ISO 8601 format

            conversation = {
                "chat_session": "{}",  # Initialize as empty JSON string
                "date": formatted_time,
                "system_instruction": "default"
            }
            
            db.reference("/users_sessions").update({userId: conversation})
            logger.info(f"User '{userId}' created successfully")
        except Exception as e:
            logger.error(f"Failed to create user '{userId}': {e}")
            raise ValueError(f"Error creating user: {e}")
        
    def extract_history(self, userId):
        """Extract chat history for a user.
        
        Args:
            userId (str): The user ID
            
        Returns:
            dict: The chat history
            
        Raises:
            ValueError: If user not found or history extraction fails
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        try:
            user_data = self.user_exists(userId)
            if not user_data:
                raise ValueError(f"User with ID '{userId}' not found")

            chat_session = user_data.get("chat_session")
            if not chat_session:
                return {}  # Return empty dict if no chat session
                
            return jsonpickle.decode(chat_session)
        except Exception as e:
            logger.error(f"Failed to extract history for user '{userId}': {e}")
            raise ValueError(f"Error accessing user data or conversation: {e}")

    def chat_history_add(self, userId, history=None):
        """Update the chat history for a user.
        
        Args:
            userId (str): The user ID
            history (list, optional): The chat history to add. Defaults to empty list.
            
        Raises:
            ValueError: If update fails
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        if history is None:
            history = []
            
        try:
            encoded_history = jsonpickle.encode(history, True)
            db.reference(f"/users_sessions/{userId}").update({"chat_session": encoded_history})
            logger.info(f"Chat history updated for user '{userId}'")
        except Exception as e:
            logger.error(f"Failed to update chat history for user '{userId}': {e}")
            raise ValueError(f"Error updating chat history: {e}")
    
    def extract_instruction(self, userId):
        """Extract system instruction for a user.
        
        Args:
            userId (str): The user ID
            
        Returns:
            str: The system instruction
            
        Raises:
            ValueError: If user not found
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        user_data = self.user_exists(userId)
        if not user_data:
            raise ValueError(f"User with ID '{userId}' not found")

        return user_data.get("system_instruction", "default")

    def update_instruction(self, userId, new_instruction="default"):
        """Update system instruction for a user.
        
        Args:
            userId (str): The user ID
            new_instruction (str, optional): The new instruction. Defaults to "default".
            
        Raises:
            ValueError: If update fails
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        try:
            db.reference(f"/users_sessions/{userId}").update({"system_instruction": new_instruction})
            logger.info(f"Instruction updated for user '{userId}'")
        except Exception as e:
            logger.error(f"Failed to update instruction for user '{userId}': {e}")
            raise ValueError(f"Error updating instruction: {e}")

    def info(self, userId):
        """Get information about a user.
        
        Args:
            userId (str): The user ID
            
        Returns:
            str: Formatted user information
            
        Raises:
            ValueError: If user not found
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        user_data = self.user_exists(userId)
        if not user_data:
            raise ValueError(f"User with ID '{userId}' not found")
            
        isadmin = self.is_admin(userId)
        
        message = f''' 
userID :          {userId}
isAdmin?:         {isadmin}
creation date :   {user_data.get("date", "Unknown")}
Prompt :          {user_data.get("system_instruction", "default")}
'''
        return message

    def get_usernames(self):
        """Get all usernames from the database.
        
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
            blocked_users = self.INFO_DB.get() or {}
            self.blocked_users_cache = set(blocked_users.keys())
            logger.info(f"Loaded {len(self.blocked_users_cache)} blocked users into cache")
        except Exception as e:
            logger.error(f"Error loading blocked users: {e}")
            self.blocked_users_cache = set()

    def _load_admin_users(self):
        """Load admin users into cache."""
        try:
            admin_users = self.INFO_ADMIN.get() or {}
            self.admins_users = set(admin_users.keys())
            logger.info(f"Loaded {len(self.admins_users)} admin users into cache")
        except Exception as e:
            logger.error(f"Error loading admin users: {e}")
            self.admins_users = set()

    def is_admin(self, userId):
        """Check if a user is an admin.
        
        Args:
            userId (str): The user ID
            
        Returns:
            bool: True if user is admin, False otherwise
        """
        return userId in self.admins_users

    def add_admin(self, userId):
        """Add a user as admin.
        
        Args:
            userId (str): The user ID
            
        Raises:
            ValueError: If addition fails
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        try:
            self.INFO_ADMIN.update({userId: True})
            self.admins_users.add(userId)
            logger.info(f"User '{userId}' added as admin")
        except Exception as e:
            logger.error(f"Error adding admin user '{userId}': {e}")
            raise ValueError(f"Failed to add admin: {e}")

    def remove_admin(self, userId):
        """Remove admin status from a user.
        
        Args:
            userId (str): The user ID
            
        Raises:
            ValueError: If removal fails
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        try:
            self.INFO_ADMIN.child(userId).delete()
            self.admins_users.discard(userId)
            logger.info(f"User '{userId}' removed from admin")
        except Exception as e:
            logger.error(f"Error removing admin user '{userId}': {e}")
            raise ValueError(f"Failed to remove admin: {e}")

    def block_user(self, userId):
        """Block a user.
        
        Args:
            userId (str): The user ID
            
        Raises:
            ValueError: If blocking fails
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        try:
            self.INFO_DB.update({userId: True})
            self.blocked_users_cache.add(userId)
            logger.info(f"User '{userId}' blocked")
        except Exception as e:
            logger.error(f"Error blocking user '{userId}': {e}")
            raise ValueError(f"Failed to block user: {e}")

    def unblock_user(self, userId):
        """Unblock a user.
        
        Args:
            userId (str): The user ID
            
        Raises:
            ValueError: If unblocking fails
        """
        if not userId:
            raise ValueError("User ID cannot be empty")
            
        try:
            self.INFO_DB.child(userId).delete()
            self.blocked_users_cache.discard(userId)
            logger.info(f"User '{userId}' unblocked")
        except Exception as e:
            logger.error(f"Error unblocking user '{userId}': {e}")
            raise ValueError(f"Failed to unblock user: {e}")

    def is_user_blocked(self, userId):
        """Check if a user is blocked.
        
        Args:
            userId (str): The user ID
            
        Returns:
            bool: True if user is blocked, False otherwise
        """
        return userId in self.blocked_users_cache


# Initialize database singleton for easy import and use
logger.info("Loading Firebase Database...")
DB = FireBaseDB()