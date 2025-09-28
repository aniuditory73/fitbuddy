# database.py

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from sqlalchemy import text
import json # Добавлен для работы с JSON-строками
from sqlalchemy import inspect # Для отладки

DATABASE_URL = "sqlite:///./fitbuddy.db"
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    first_name = Column(String, nullable=True) # Добавлено поле для имени пользователя
    username = Column(String, unique=True, nullable=True, index=True) # Добавлено поле для username
    age = Column(Integer)
    height = Column(Float)
    weight = Column(Float)
    goal = Column(String)
    calorie_target = Column(Integer, nullable=True) # Цель по калориям
    created_at = Column(DateTime, default=datetime.utcnow)
    # Геймификация
    points = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime, nullable=True)
    last_calorie_target_met_date = Column(DateTime, nullable=True) # Новое поле: дата последнего дня с выполненной нормой калорий
    calorie_streak = Column(Integer, default=0) # Новое поле: серия дней с выполненной нормой калорий

    meals = relationship("Meal", back_populates="user")
    workouts = relationship("Workout", back_populates="user")
    weights = relationship("Weight", back_populates="user")
    reminders = relationship("Reminder", back_populates="user")
    favorite_foods = relationship("FavoriteFood", back_populates="user")
    
    # Новые отношения для друзей
    sent_friend_requests = relationship("Friendship", foreign_keys="[Friendship.requester_id]", back_populates="requester")
    received_friend_requests = relationship("Friendship", foreign_keys="[Friendship.addressee_id]", back_populates="addressee")

class Meal(Base):
    __tablename__ = "meals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    calories = Column(Integer)
    date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="meals")

class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    duration = Column(Integer) # in minutes
    calories_burned = Column(Integer)
    workout_type = Column(String, nullable=True) # например, 'кардио', 'силовая'
    muscle_group = Column(String, nullable=True) # например, 'грудь', 'ноги', 'все тело'
    sets = Column(Integer, nullable=True)
    reps = Column(String, nullable=True) # может быть '10-12', 'до отказа'
    weight_used = Column(Float, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="workouts")

class Weight(Base):
    __tablename__ = "weights"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    weight = Column(Float)
    date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="weights")

class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    text = Column(String)
    time = Column(DateTime) # specific time for reminder
    job_id = Column(String, nullable=True) # for apscheduler
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reminders")

class FavoriteFood(Base):
    __tablename__ = "favorite_foods"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    calories_per_100g = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="favorite_foods")

class Exercise(Base):
    __tablename__ = "exercises"
    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Text, unique=True, index=True, nullable=False)
    name_ru = Column(Text, nullable=False) # Русское название, обязательно
    body_part_ru = Column(Text, nullable=False) # Русская часть тела, обязательно
    primary_muscles_ru = Column(Text, nullable=False) # Русские основные мышцы, обязательно
    difficulty_ru = Column(Text, nullable=False) # Русский уровень сложности, обязательно
    description_ru = Column(Text, nullable=False) # Русское описание, обязательно
    start_image_path = Column(Text, nullable=True) # Путь к изображению начальной позиции
    end_image_path = Column(Text, nullable=True) # Путь к изображению конечной позиции

class Friendship(Base):
    __tablename__ = "friendships"
    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    addressee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending") # pending, accepted, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requester = relationship("User", foreign_keys="[Friendship.requester_id]", back_populates="sent_friend_requests")
    addressee = relationship("User", foreign_keys="[Friendship.addressee_id]", back_populates="received_friend_requests")


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Простая миграция: создаем все таблицы, если они не существуют, и добавляем недостающие колонки
def create_tables_if_not_exists():
    print("DEBUG: Вызвана create_tables_if_not_exists().")
    
    # Временно: удалить таблицу Exercise, если она существует, для гарантированного обновления схемы
    # Это нужно только для отладки, потом уберем.
    inspector = inspect(engine)

    if inspector.has_table("exercises"):
        print("DEBUG: Таблица 'exercises' найдена. Удаляю ее.")
        Base.metadata.tables['exercises'].drop(engine)
    else:
        print("DEBUG: Таблица 'exercises' не найдена.")

    Base.metadata.create_all(engine)
    print("DEBUG: Base.metadata.create_all(engine) выполнен.")

    # Дополнительная отладка: проверка столбцов
    inspector = inspect(engine)
    columns = inspector.get_columns('exercises')
    print("DEBUG: Столбцы таблицы 'exercises' после создания:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")

    with engine.connect() as conn:
        # Проверка, есть ли таблица exercises после создания
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='exercises';"))
        if result.fetchone():
            print("DEBUG: Таблица 'exercises' существует в базе данных после create_all.")
        else:
            print("ERROR: Таблица 'exercises' НЕ существует в базе данных после create_all.")

        conn.commit() # commit для DDL операций в некоторых случаях может быть полезен, хотя create_all обычно сам управляет транзакциями

    print("DEBUG: create_tables_if_not_exists() завершена.")
