from passlib.context import CryptContext
from api.models.user import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def authenticate_user(user: User, password: str) -> bool:
    """Authenticate a user"""
    if not user.is_active:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return True
