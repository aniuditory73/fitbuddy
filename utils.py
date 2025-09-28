# utils.py

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os
import re
import aiohttp
from sqlalchemy.orm import Session
from database import User, FavoriteFood, Exercise, get_db, Friendship
import json
import matplotlib.pyplot as plt
from datetime import datetime
from aiogram.fsm.context import FSMContext
from aiogram import Bot # Исправленный импорт Bot

class RegistrationStates(StatesGroup):
    waiting_for_age = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_goal = State()
    waiting_for_calorie_target_on_registration = State() # Новое состояние для установки цели калорий во время регистрации

class FoodStates(StatesGroup):
    waiting_for_food_name = State()
    waiting_for_calories = State()
    waiting_for_calories_quantity = State()
    waiting_for_food_selection = State() # Новое состояние для выбора продукта из Nutritionix
    waiting_for_favorite_food_selection = State() # Новое состояние для выбора из любимых блюд

class WorkoutStates(StatesGroup):
    waiting_for_workout_name = State()
    waiting_for_duration = State()
    waiting_for_calories_burned = State()
    waiting_for_workout_type = State()
    waiting_for_muscle_group = State()
    waiting_for_sets = State()
    waiting_for_reps = State()
    waiting_for_weight_used = State()

class WeightStates(StatesGroup):
    waiting_for_new_weight = State()

class ReminderStates(StatesGroup):
    waiting_for_reminder_text = State()
    waiting_for_reminder_time = State()

class CalorieTargetStates(StatesGroup):
    waiting_for_calorie_target = State()

class FavoriteFoodStates(StatesGroup):
    waiting_for_favorite_food_name = State()
    waiting_for_favorite_food_calories = State()
    waiting_for_favorite_food_to_delete = State()

class ExerciseLibraryStates(StatesGroup):
    waiting_for_body_part_selection = State()
    waiting_for_exercise_selection = State()
    waiting_for_page_selection = State() # Новое состояние для пагинации

class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_points_amount = State()

class LeaderboardStates(StatesGroup):
    waiting_for_leaderboard_type = State()

class FriendStates(StatesGroup):
    waiting_for_friend_id = State()
    waiting_for_friend_request_action = State()

class UserStateHistory(StatesGroup):
    history = State()

async def add_state_to_history(state: FSMContext, current_state: str):
    user_data = await state.get_data()
    history = user_data.get("state_history", [])
    # Не добавляем текущее состояние, если оно является частью истории и мы возвращаемся назад
    if not history or history[-1] != current_state:
        history.append(current_state)
    await state.update_data(state_history=history)
    print(f"DEBUG: История состояний: {history}")

async def get_previous_state(state: FSMContext) -> str | None:
    user_data = await state.get_data()
    history = user_data.get("state_history", [])
    if history:
        # Удаляем текущее состояние (последнее в истории) и возвращаем предыдущее
        history.pop() # Удаляем текущее состояние
        previous_state = history.pop() if history else None # Получаем предыдущее состояние
        await state.update_data(state_history=history)
        print(f"DEBUG: Возврат к состоянию: {previous_state}, новая история: {history}")
        return previous_state
    print("DEBUG: История состояний пуста.")
    return None

async def clear_state_history(state: FSMContext):
    await state.update_data(state_history=[])
    print("DEBUG: История состояний очищена.")

async def update_calorie_streak(db: Session, user: User, total_calories_today: int) -> bool:
    """Обновляет серию дней с выполненной нормой калорий."
    Возвращает True, если серия изменилась (увеличилась или сбросилась), иначе False.
    """
    today = datetime.utcnow().date()
    calorie_streak_changed = False
    previous_calorie_streak = user.calorie_streak # Сохраняем предыдущее значение для сравнения

    if user.calorie_target and total_calories_today >= user.calorie_target:
        if user.last_calorie_target_met_date:
            last_met_date = user.last_calorie_target_met_date.date()
            if (today - last_met_date).days == 1: # Если цель была достигнута вчера
                user.calorie_streak = (user.calorie_streak or 0) + 1
            elif (today - last_met_date).days > 1: # Если был пропуск
                user.calorie_streak = 1
            # Если цель достигнута сегодня повторно, серия не меняется
        else: # Первая запись о достижении цели
            user.calorie_streak = 1
        user.last_calorie_target_met_date = datetime.utcnow()
    else:
        # Если цель не достигнута сегодня, сбрасываем серию (если она была)
        if user.last_calorie_target_met_date and (today - user.last_calorie_target_met_date.date()).days > 0: # Если цель не была достигнута сегодня
             user.calorie_streak = 0
        
    if previous_calorie_streak != user.calorie_streak:
        calorie_streak_changed = True

    db.commit()
    db.refresh(user)
    return calorie_streak_changed

async def notify_friends_about_achievement(db: Session, bot: Bot, user: User, message_text: str):
    """Отправляет уведомления всем друзьям пользователя о его достижении."""
    friends_list = db.query(Friendship).filter(
        ((Friendship.requester_id == user.id) | (Friendship.addressee_id == user.id)),
        Friendship.status == "accepted"
    ).all()

    if friends_list:
        user_name_display = user.first_name if user.first_name else (f"@{user.username}" if user.username else f"Пользователь {user.telegram_id}")
        full_notification_message = f"🔔 У вашего друга {user_name_display} новое достижение: {message_text}"
        for friendship in friends_list:
            friend_user_id = None
            if friendship.requester_id == user.id:
                friend_user_id = friendship.addressee.telegram_id
            else:
                friend_user_id = friendship.requester.telegram_id
            
            if friend_user_id:
                try:
                    await bot.send_message(friend_user_id, full_notification_message)
                except Exception as e:
                    print(f"Ошибка при отправке уведомления другу {friend_user_id}: {e}")

def calculate_bmi(weight: float, height: float) -> float:
    """Расчет индекса массы тела."""
    return weight / ((height / 100) ** 2)

def calculate_bmr(weight: float, height: float, age: int, gender: str = "male") -> int:
    """Расчет базального метаболизма (BMR) по формуле Миффлина-Сан-Жеора.
    Упрощенно для примера, без учета пола, для мужчин.
    """
    # BMR для мужчин: (10 * вес в кг) + (6.25 * рост в см) - (5 * возраст в годах) + 5
    # BMR для женщин: (10 * вес в кг) + (6.25 * рост в см) - (5 * возраст в годах) - 161
    # В данной версии упрощено до одной формулы
    return int((10 * weight) + (6.25 * height) - (5 * age) + 5)

def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Профиль"), KeyboardButton(text="Калории за день")],
            [KeyboardButton(text="Еда"), KeyboardButton(text="Тренировки")],
            [KeyboardButton(text="Вес"), KeyboardButton(text="Напоминание")],
            [KeyboardButton(text="Рейтинг")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_food_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить еду")],
            [KeyboardButton(text="Любимые блюда")],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_workout_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Логировать тренировку")],
            [KeyboardButton(text="История тренировок")],
            [KeyboardButton(text="📚 Библиотека упражнений")],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_workout_history_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="За неделю"), KeyboardButton(text="За месяц")],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_weight_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Ввести вес"), KeyboardButton(text="График веса")],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_rating_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Очки"), KeyboardButton(text="Достижения")],
            [KeyboardButton(text="Таблица лидеров"), KeyboardButton(text="Друзья")],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_leaderboard_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Топ по очкам"), KeyboardButton(text="Топ по сериям")],
            [KeyboardButton(text="Назад к рейтингу")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_friend_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мои друзья"), KeyboardButton(text="Добавить друга")],
            [KeyboardButton(text="Запросы в друзья")],
            [KeyboardButton(text="Назад к рейтингу")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_add_friend_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_friend_requests_keyboard(requests: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if requests:
        for req in requests:
            builder.row(
                InlineKeyboardButton(text=f"✅ {req.requester.first_name} ({req.requester.telegram_id})", callback_data=f"accept_friend_{req.id}"),
                InlineKeyboardButton(text=f"❌ {req.requester.first_name} ({req.requester.telegram_id})", callback_data=f"reject_friend_{req.id}")
            )
    builder.row(InlineKeyboardButton(text="Назад к меню друзей", callback_data="back_to_friend_menu"))
    return builder.as_markup()


def get_back_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Назад к главному меню")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    return keyboard

def get_favorite_food_keyboard(favorite_foods: list[FavoriteFood]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for food in favorite_foods:
        builder.button(text=f"{food.name} ({food.calories_per_100g} ккал/100г)", callback_data=f"select_favorite_food_{food.id}")
    builder.row(InlineKeyboardButton(text="Добавить любимое блюдо", callback_data="add_favorite_food"))
    builder.row(InlineKeyboardButton(text="Удалить любимое блюдо", callback_data="remove_favorite_food_start"))
    builder.row(InlineKeyboardButton(text="Назад", callback_data="back_to_food_menu"))
    return builder.as_markup()

async def add_favorite_food(db: Session, user_id: int, name: str, calories_per_100g: int) -> FavoriteFood:
    new_favorite_food = FavoriteFood(
        user_id=user_id,
        name=name,
        calories_per_100g=calories_per_100g
    )
    db.add(new_favorite_food)
    db.commit()
    db.refresh(new_favorite_food)
    return new_favorite_food

async def remove_favorite_food(db: Session, favorite_food_id: int):
    food_to_delete = db.query(FavoriteFood).filter(FavoriteFood.id == favorite_food_id).first()
    if food_to_delete:
        db.delete(food_to_delete)
        db.commit()


# Простая база данных калорий (может быть расширена)
FOOD_CALORIES_DB = {
    "яблоко": 52,
    "банан": 89,
    "курица": 165,
    "рис": 130,
    "гречка": 343,
    "молоко": 42,
    "хлеб": 265,
    "яйцо": 155,
    "сыр": 404,
    "картофель": 77,
    "макароны": 158,
    "огурец": 15,
    "помидор": 18,
    "апельсин": 47,
    "йогурт": 59,
    "творог": 163,
    "говядина": 250,
    "свинина": 242,
    "рыба": 206, # Среднее значение
}

async def search_open_food_facts(query: str) -> list[dict]:
    """Ищет продукты через Open Food Facts API и возвращает список словарей.
    Каждый словарь содержит название продукта и калорийность на 100г.
    """
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response.raise_for_status()  # Вызывает исключение для ошибок HTTP статуса
                data = await response.json()
                
                results = []
                for product in data.get('products', []):
                    product_name = product.get('product_name')
                    # Open Food Facts хранит калории в поле energy-kcal_100g
                    calories_per_100g = None
                    if 'nutriments' in product and 'energy-kcal_100g' in product['nutriments']:
                        calories_per_100g = product['nutriments']['energy-kcal_100g']
                    
                    if product_name and calories_per_100g is not None:
                        results.append({"food_name": product_name, "calories_per_100g": int(calories_per_100g)})
                
                return results

        except aiohttp.ClientError as e:
            print(f"Ошибка запроса к Open Food Facts API: {e}")
            return []
        except Exception as e:
            print(f"Неизвестная ошибка при работе с Open Food Facts API: {e}")
            return []

def parse_food_input(text: str) -> tuple[str, int | None]:
    """Парсит ввод пользователя для определения продукта и количества.
    Пример: 'яблоко 200 г' -> ('яблоко', 200)
    """
    text = text.lower().strip()
    match = re.search(r'([а-яА-ЯёЁ\s]+)\s+(\d+)\s*(г|грамм|гр|мл|миллилитров|ml|шт|штуки|штук)', text)
    if match:
        food_name = match.group(1).strip()
        quantity = int(match.group(2))
        return food_name, quantity
    
    # Если нет количества, пробуем найти только продукт
    for food_item in FOOD_CALORIES_DB:
        if food_item in text:
            return food_item, None

    return text, None # Возвращаем исходный текст, если ничего не найдено

def get_calories_per_100g(food_name: str) -> int | None:
    """Возвращает калорийность на 100 г продукта из базы данных."""
    return FOOD_CALORIES_DB.get(food_name)


import matplotlib.pyplot as plt
import os
from datetime import datetime

def generate_weight_chart(weights_data: list[tuple[datetime, float]], user_id: int) -> str | None:
    """Генерирует график изменения веса и сохраняет его в файл.
    Возвращает путь к файлу с графиком или None в случае ошибки.
    """
    if not weights_data:
        return None

    dates = [item[0] for item in weights_data]
    weights = [item[1] for item in weights_data]

    plt.figure(figsize=(10, 6))
    plt.plot(dates, weights, marker='o')
    plt.title(f'Прогресс веса пользователя {user_id}')
    plt.xlabel('Дата')
    plt.ylabel('Вес (кг)')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    uploads_dir = "uploads"
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)

    chart_filename = os.path.join(uploads_dir, f"weight_chart_{user_id}.png")
    plt.savefig(chart_filename)
    plt.close() # Закрываем фигуру, чтобы освободить память

    return chart_filename

# ===== Геймификация =====
def award_points(db: Session, user: User, reason: str, base_points: int) -> tuple[int, bool, bool]:
    """Начисляет очки пользователю за действие и обновляет streak, если действие за новый день.
    Возвращает (количество начисленных очков, bool: изменилась ли общая серия, bool: обновилась ли серия калорий).
    """
    now = datetime.utcnow()
    awarded = base_points
    streak_changed = False
    calorie_streak_changed = False # В этой функции не меняем серию калорий, но оставляем для согласованности

    # Обновление серии (streak) по датам в UTC
    last_date = user.last_activity_date.date() if user.last_activity_date else None
    today = now.date()
    if last_date is None:
        user.streak = 1
        streak_changed = True
    else:
        if (today - last_date).days == 0:
            pass
        elif (today - last_date).days == 1:
            user.streak += 1
            streak_changed = True
        else:
            user.streak = 1
            streak_changed = True

    # Бонус за серию: +10% за каждый день серии, максимум +50%
    streak_bonus_multiplier = min(0.5, 0.1 * max(0, user.streak - 1))
    awarded = int(round(base_points * (1 + streak_bonus_multiplier)))

    user.points = (user.points or 0) + awarded
    user.last_activity_date = now
    db.commit()
    db.refresh(user)
    return awarded, streak_changed, calorie_streak_changed

def register_activity(db: Session, telegram_id: int, base_points: int, reason: str) -> tuple[int, int, int, bool, bool]:
    """Удобная обертка: найти пользователя по telegram_id, начислить очки.
    Возвращает (awarded, total_points, streak, streak_changed, calorie_streak_changed).
    """
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return 0, 0, 0, False, False
    awarded, streak_changed, calorie_streak_changed = award_points(db, user, reason, base_points)
    return awarded, user.points, user.streak, streak_changed, calorie_streak_changed

async def load_exercises_from_json(limit: int = None):
    """
    Читает JSON-файл execercises.json из локальной папки exercise_data/
    и вставляет упражнения в таблицу exercises.
    """
    exercises_filepath = "execercises.json"
    images_base_dir = "exercise_data/images" # Базовая папка для изображений

    # os.makedirs(os.path.dirname(exercises_filepath), exist_ok=True) # Удален, так как execercises.json находится в корне
    os.makedirs(images_base_dir, exist_ok=True) # Создаем базовую папку, если ее нет

    db = next(get_db())
    try:
        with open(exercises_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            processed_count = 0
            for exercise_data in data:
                if limit is not None and processed_count >= limit:
                    break # Прекратить обработку после достижения лимита
                
                exercise_id = exercise_data.get("id")
                name_ru = exercise_data.get("name_ru")
                body_part_ru = exercise_data.get("body_part_ru")
                primary_muscles_ru_list = exercise_data.get("primary_muscles_ru", [])
                difficulty_ru = exercise_data.get("difficulty_ru")
                description_ru = exercise_data.get("description_ru")

                # Преобразуем список мышц в JSON-строку
                primary_muscles_ru_json = json.dumps(primary_muscles_ru_list)

                start_image_path = None
                end_image_path = None

                exercise_images_dir = os.path.join(images_base_dir, exercise_id)

                if os.path.exists(exercise_images_dir):
                    for img_name in os.listdir(exercise_images_dir):
                        if img_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                            # Предполагаем, что изображения называются start.<ext> и end.<ext>
                            if img_name.lower().startswith('start.'):
                                start_image_path = os.path.join(exercise_images_dir, img_name)
                            elif img_name.lower().startswith('end.'):
                                end_image_path = os.path.join(exercise_images_dir, img_name)
                # else:
                #     print(f"DEBUG: Папка с изображениями для упражнения {exercise_id} не найдена: {exercise_images_dir}")

                existing_exercise = db.query(Exercise).filter(Exercise.exercise_id == exercise_id).first()
                if existing_exercise:
                    existing_exercise.name_ru = name_ru
                    existing_exercise.body_part_ru = body_part_ru
                    existing_exercise.primary_muscles_ru = primary_muscles_ru_json
                    existing_exercise.difficulty_ru = difficulty_ru
                    existing_exercise.description_ru = description_ru
                    existing_exercise.start_image_path = start_image_path
                    existing_exercise.end_image_path = end_image_path
                    print(f"DEBUG: Упражнение {name_ru} обновлено.")
                else:
                    new_exercise = Exercise(
                        exercise_id=exercise_id,
                        name_ru=name_ru,
                        body_part_ru=body_part_ru,
                        primary_muscles_ru=primary_muscles_ru_json,
                        difficulty_ru=difficulty_ru,
                        description_ru=description_ru,
                        start_image_path=start_image_path,
                        end_image_path=end_image_path
                    )
                    db.add(new_exercise)
                processed_count += 1
        db.commit()
        print("DEBUG: Упражнения из JSON загружены (или обновлены).")
    except FileNotFoundError:
        print(f"WARNING: Файл базы упражнений не найден: {exercises_filepath}")
    except Exception as e:
        print(f"Ошибка при загрузке упражнений из JSON: {e}")
        db.rollback()
    finally:
        db.close()
