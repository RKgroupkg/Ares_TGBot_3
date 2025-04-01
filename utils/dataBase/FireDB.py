import os
import datetime
import json
import jsonpickle
import firebase_admin
from firebase_admin import db, credentials, exceptions
from utils.log import logger
from config import DB_SESSION_INFO

class FireBaseDB:
    def __init__(self):
        try:
            # Try to load credentials from the config
            cred = credentials.Certificate(DB_SESSION_INFO)
            # Initialize the Firebase app with a unique name to avoid conflicts
            if not firebase_admin._apps:
                app = firebase_admin.initialize_app(cred, {
                    "databaseURL": "https://ares-rkbot-default-rtdb.asia-southeast1.firebasedatabase.app/"
                })
            else:
                app = firebase_admin.get_app()
                
            # Initialize database references
            self.db = db.reference("/users_sessions")
            self.INFO_DB = db.reference("/Blocked_user")
            self.INFO_ADMIN = db.reference("/Admin_users")
            
            # Initialize caches
            self.blocked_users_cache = set()
            self.admins_users = set()
            
            # Load initial data
            self._load_blocked_users()
            self._load_admin_users()
            
            logger.info("FireBaseDB initialized successfully")
        except Exception as e:
            logger.critical(f"Failed to initialize FireBaseDB: {e}")
            raise

    def user_exists(self, userId):
        """Check if a user exists in the database"""
        if not userId:
            logger.error("Cannot check for user with empty userId")
            return False
            
        try:
            return db.reference(f"/users_sessions/{userId}").get()
        except Exception as e:
            logger.error(f"Error while checking for user {userId}: {e}")
            return False

    def create_user(self, userId):
        """Create a new user in the database with default values"""
        if not userId:
            raise ValueError("Cannot create user with empty userId")
            
        user_data = self.user_exists(userId)
        if user_data:
            logger.warning(f"User with ID '{userId}' already exists")
            return False
        
        try:
            now = datetime.datetime.now()
            formatted_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")  # ISO 8601 format

            conversation = {
                "chat_session": jsonpickle.encode({}, True),  # Initialize with empty dict
                "date": formatted_time,
                "system_instruction": "default"
            }
            db.reference(f"/users_sessions").update({f"{userId}": conversation})
            logger.info(f"User {userId} created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create user {userId}: {e}")
            raise ValueError(f"Error creating user: {e}")

    def extract_history(self, userId):
        """Extract chat history for a user"""
        if not userId:
            raise ValueError("Cannot extract history for empty userId")
            
        try:
            user_data = self.user_exists(userId)
            if not user_data:
                logger.warning(f"User with ID '{userId}' not found when extracting history")
                return {}

            chat_session = user_data.get("chat_session")
            if not chat_session:
                logger.warning(f"No chat session found for user {userId}")
                return {}
                
            return jsonpickle.decode(chat_session)
        except Exception as e:
            logger.error(f"Error extracting history for user {userId}: {e}")
            raise ValueError(f"Error accessing user data or conversation: {e}")

    def chat_history_add(self, userId, history=[]):
        """Update chat history for a user"""
        if not userId:
            raise ValueError("Cannot update history for empty userId")
            
        try:
            if not self.user_exists(userId):
                logger.warning(f"Attempting to update history for non-existent user {userId}")
                self.create_user(userId)
                
            encoded_history = jsonpickle.encode(history, True)
            db.reference(f"/users_sessions/{userId}").update({"chat_session": encoded_history})
            logger.debug(f"Chat history updated for user {userId}")
            return True
        except Exception as e:
            logger.error(f"Error updating chat history for user {userId}: {e}")
            raise ValueError(f"Error updating chat history: {e}")
    
    def extract_instruction(self, userId):
        """Extract system instruction for a user"""
        if not userId:
            raise ValueError("Cannot extract instruction for empty userId")
            
        try:
            user_data = self.user_exists(userId)
            if not user_data:
                logger.warning(f"User with ID '{userId}' not found when extracting instruction")
                return "default"

            return user_data.get("system_instruction", "default")
        except Exception as e:
            logger.error(f"Error extracting instruction for user {userId}: {e}")
            return "default"

    def update_instruction(self, userId, new_instruction="default"):
        """Update system instruction for a user"""
        if not userId:
            raise ValueError("Cannot update instruction for empty userId")
            
        try:
            if not self.user_exists(userId):
                logger.warning(f"Attempting to update instruction for non-existent user {userId}")
                self.create_user(userId)
                
            db.reference(f"/users_sessions/{userId}").update({"system_instruction": new_instruction})
            logger.info(f"System instruction updated for user {userId}")
            return True
        except Exception as e:
            logger.error(f"Error updating instruction for user {userId}: {e}")
            return False

    def info(self, userId):
        """Get user information summary"""
        if not userId:
            return "Cannot get info for empty userId"
            
        try:
            user_data = self.user_exists(userId)
            if not user_data:
                return f"User with ID '{userId}' not found"
            
            isadmin = self.is_admin(userId)
            isblocked = self.is_user_blocked(userId)
            
            message = f""" 
♔ User Id:       {userId}
♚ Admin:         {isadmin}
♛ Blocked:       {isblocked}
❀ creation date: {user_data.get("date", "Unknown")}
✿ Prompt:        {user_data.get("system_instruction", "default")}
                """
            return message
        except Exception as e:
            logger.error(f"Error getting info for user {userId}: {e}")
            return f"Error retrieving user info: {e}"

    def get_usernames(self):
        """Get list of all usernames in the database"""
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
        """Load blocked users into cache"""
        try:
            blocked_users = self.INFO_DB.get()
            if blocked_users:
                self.blocked_users_cache = set(blocked_users.keys())
                logger.info(f"Loaded {len(self.blocked_users_cache)} blocked users into cache")
            else:
                self.blocked_users_cache = set()
                logger.info("No blocked users found")
        except Exception as e:
            logger.error(f"Error loading blocked users: {e}")
            self.blocked_users_cache = set()

    def _load_admin_users(self):
        """Load admin users into cache"""
        try:
            admin_users = self.INFO_ADMIN.get()
            if admin_users:
                self.admins_users = set(admin_users.keys())
                logger.info(f"Loaded {len(self.admins_users)} admin users into cache")
            else:
                self.admins_users = set()
                logger.info("No admin users found")
        except Exception as e:
            logger.error(f"Error loading admin users: {e}")
            self.admins_users = set()

    def refresh_caches(self):
        """Refresh both admin and blocked user caches"""
        self._load_blocked_users()
        self._load_admin_users()
        return True

    def is_admin(self, userId):
        """Check if a user is an admin"""
        if not userId:
            logger.warning("Empty userId provided to is_admin check")
            return False
        return userId in self.admins_users

    def add_admin(self, userId):
        """Add a user as admin with verification"""
        if not userId:
            logger.error("Cannot add empty userId as admin")
            return False
            
        try:
            # Check if already an admin
            if self.is_admin(userId):
                logger.info(f"User {userId} is already an admin")
                return True
                
            # Add to Firebase
            self.INFO_ADMIN.update({userId: True})
            
            # Wait a moment for the update to propagate
            import time
            time.sleep(0.5)
            
            # Verify the update by direct database check (not using cache)
            updated = self.INFO_ADMIN.child(userId).get()
            if updated:
                # Update local cache
                self.admins_users.add(userId)
                logger.info(f"User {userId} has been successfully added as admin")
                return True
            else:
                logger.error(f"Failed to add {userId} as admin - database update failed")
                return False
        except Exception as e:
            logger.error(f"Error adding admin user {userId}: {e}")
            return False

    def remove_admin(self, userId):
        """Remove a user from admin role with verification"""
        if not userId:
            logger.error("Cannot remove empty userId from admin")
            return False
            
        try:
            # Check if user is an admin
            if not self.is_admin(userId):
                logger.info(f"User {userId} is not an admin - no action needed")
                return True
                
            # Remove from Firebase
            self.INFO_ADMIN.child(userId).delete()
            
            # Wait a moment for the update to propagate
            import time
            time.sleep(0.5)
            
            # Verify the update by direct database check (not using cache)
            updated = self.INFO_ADMIN.child(userId).get()
            if updated is None:
                # Update local cache
                self.admins_users.discard(userId)
                logger.info(f"User {userId} has been successfully removed from admin")
                return True
            else:
                logger.error(f"Failed to remove {userId} from admin - database update failed")
                return False
        except Exception as e:
            logger.error(f"Error removing admin user {userId}: {e}")
            return False

    def block_user(self, userId):
        """Block a user with verification"""
        if not userId:
            logger.error("Cannot block empty userId")
            return False
            
        try:
            # Ensure user exists in the database before blocking
            user_exists = self.user_exists(userId)
            if not user_exists:
                logger.warning(f"Attempting to block non-existent user {userId}")
                # You might want to create the user first or handle differently
                
            # Check if already blocked
            if self.is_user_blocked(userId):
                logger.info(f"User {userId} is already blocked - no action needed")
                return True
                
            # Block in Firebase
            self.INFO_DB.update({userId: True})
            
            # Wait a moment for the update to propagate
            import time
            time.sleep(0.5)
            
            # Verify the update by direct database check (not using cache)
            updated = self.INFO_DB.child(userId).get()
            if updated:
                # Update local cache
                self.blocked_users_cache.add(userId)
                logger.info(f"User {userId} has been successfully blocked")
                
                # Check if user is admin and warn if they are
                if self.is_admin(userId):
                    logger.warning(f"Blocked user {userId} is also an admin. Consider removing admin privileges.")
                    
                return True
            else:
                logger.error(f"Failed to block {userId} - database update failed")
                return False
        except Exception as e:
            logger.error(f"Error blocking user {userId}: {e}")
            return False

    def unblock_user(self, userId):
        """Unblock a user with verification"""
        if not userId:
            logger.error("Cannot unblock empty userId")
            return False
            
        try:
            # Check if user is blocked
            if not self.is_user_blocked(userId):
                logger.info(f"User {userId} is not blocked - no action needed")
                return True
                
            # Unblock in Firebase
            self.INFO_DB.child(userId).delete()
            
            # Wait a moment for the update to propagate
            import time
            time.sleep(0.5)
            
            # Verify the update by direct database check (not using cache)
            updated = self.INFO_DB.child(userId).get()
            if updated is None:
                # Update local cache
                self.blocked_users_cache.discard(userId)
                logger.info(f"User {userId} has been successfully unblocked")
                return True
            else:
                logger.error(f"Failed to unblock {userId} - database update failed")
                return False
        except Exception as e:
            logger.error(f"Error unblocking user {userId}: {e}")
            return False

    def is_user_blocked(self, userId):
        """Check if a user is blocked"""
        if not userId:
            logger.warning("Empty userId provided to is_user_blocked check")
            return False
            
        # For critical checks, verify directly from database instead of just cache
        try:
            # First check cache for performance
            if userId in self.blocked_users_cache:
                return True
                
            # Double-check with database for certainty
            blocked_status = self.INFO_DB.child(userId).get()
            return blocked_status is not None and blocked_status is True
        except Exception as e:
            logger.error(f"Error checking if user {userId} is blocked: {e}")
            # Fall back to cache in case of database error
            return userId in self.blocked_users_cache

    def refresh_user_status(self, userId):
        """Refresh the status of a specific user (admin and blocked status)"""
        if not userId:
            return False
            
        try:
            # Check admin status directly from database
            admin_status = self.INFO_ADMIN.child(userId).get()
            if admin_status:
                self.admins_users.add(userId)
            else:
                self.admins_users.discard(userId)
                
            # Check blocked status directly from database
            blocked_status = self.INFO_DB.child(userId).get()
            if blocked_status:
                self.blocked_users_cache.add(userId)
            else:
                self.blocked_users_cache.discard(userId)
                
            logger.info(f"Refreshed status for user {userId}: admin={admin_status}, blocked={blocked_status}")
            return True
        except Exception as e:
            logger.error(f"Error refreshing status for user {userId}: {e}")
            return False
# Initialize the database (kept the same for compatibility)
try:
    logger.info("Loading DataBase....")
    DB = FireBaseDB()
    logger.info("DataBase loaded successfully")
except Exception as e:
    logger.critical(f"Failed to initialize DB object: {e}")
    raise