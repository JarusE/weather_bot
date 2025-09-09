from sqlalchemy.engine import row
import aiosqlite
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)

async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

DB_PATH = "weather.db"

@dataclass
class User(Base):
    """
    Represents a user in the system.

    This class defines the `User` entity with associated attributes reflecting
    user-specific information. It is used for persistence and interaction
    with the database table `users`. The class inherits from the `Base`
    class to utilize SQLAlchemy ORM functionality.

    :ivar id: Unique identifier for the user.
    :type id: int
    :ivar city: Current city of the user, if provided.
    :type city: str or None
    :ivar unit: Unit or designation of the user, if provided.
    :type unit: str or None
    :ivar last_city: Last known city of the user, if provided.
    :type last_city: str or None
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    last_city = Column(String, nullable=True)

async def get_user(user_id: int):
    """
    Retrieve a user by their ID asynchronously.

    This function queries the database asynchronously using an
    active session and retrieves a user object that matches the
    specified user ID.

    :param user_id: The ID of the user to retrieve.
    :type user_id: int
    :return: The user object corresponding to the given user ID, or None
        if no user is found.
    :rtype: User or None
    """
    async with async_session() as session:
        return await session.get(User, user_id)

async def set_user(user_id: int, city=None, unit=None, last_city=None):
    """
    Updates or creates a user entry in the database. If a user with the given
    ID does not exist, it creates a new user with the provided details. If
    the user exists, it updates any non-None values in the database record.

    :param user_id: The unique identifier for the user.
    :type user_id: int
    :param city: The current city of the user. Default is None.
    :type city: str, optional
    :param unit: The preferred unit (e.g., metric or imperial) of the user.
        Default is None.
    :type unit: str, optional
    :param last_city: The last known city of the user. Default is None.
    :type last_city: str, optional
    :return: None
    :rtype: None
    """
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            user = User(id=user_id, city=city, unit=unit, last_city=last_city)
            session.add(user)
        else:
            if city is not None:
                user.city = city
            if unit is not None:
                user.unit = unit
            if last_city is not None:
                user.last_city = last_city
        await session.commit()

async def get_all_users():
    """
    Fetches all users from the database asynchronously.

    This coroutine retrieves all user records from the database using an
    SQLAlchemy session.

    :return: A list of user objects retrieved from the database.
    :rtype: List[User]
    """
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(User))
        return list(result.scalars())

async def init_db():
    """
    Initializes the database by creating all tables defined in the metadata.

    This function establishes an asynchronous connection with the database
    engine and ensures that all tables specified in the `Base.metadata`
    are created. It leverages the provided database engine to run the
    synchronous table creation within an asynchronous context.

    :return: None
    :rtype: None
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
