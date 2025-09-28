# handlers.py

from aiogram import Router, types, F, Bot # Добавлен импорт Bot напрямую из aiogram
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder # Правильный импорт InlineKeyboardBuilder
from aiogram.types import FSInputFile, InputMediaPhoto, InlineKeyboardButton # Импортируем FSInputFile для отправки файлов и InputMediaPhoto для отправки медиа-групп, InlineKeyboardButton
from aiogram.enums import ParseMode # Исправленный импорт ParseMode
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import os
from aiogram.fsm.state import State # Добавлен импорт State

from database import Meal, Workout, Weight, Reminder, User, get_db, Exercise, Friendship # Добавлен импорт Friendship
from database import FavoriteFood # Добавлено для любимых блюд
from utils import RegistrationStates, FoodStates, WorkoutStates, WeightStates, ReminderStates, CalorieTargetStates, generate_weight_chart, parse_food_input, get_calories_per_100g, get_main_keyboard, search_open_food_facts, register_activity, get_food_menu_keyboard, get_workout_menu_keyboard, get_weight_menu_keyboard, get_rating_menu_keyboard, get_back_keyboard, get_cancel_keyboard, get_leaderboard_keyboard, get_friend_menu_keyboard, get_add_friend_keyboard, get_friend_requests_keyboard # Добавлены клавиатуры для друзей
from utils import FavoriteFoodStates, get_favorite_food_keyboard, add_favorite_food, remove_favorite_food # Добавлено для любимых блюд
from utils import get_workout_history_keyboard # Импортируем BODY_PART_TRANSLATIONS
from utils import ExerciseLibraryStates, LeaderboardStates, FriendStates # Импортируем новые состояния, LeaderboardStates и FriendStates
from utils import add_state_to_history, get_previous_state, clear_state_history, UserStateHistory, update_calorie_streak, notify_friends_about_achievement # Импортируем функции управления историей состояний и UserStateHistory, update_calorie_streak, notify_friends_about_achievement
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json # Добавлен для работы с JSON-строками
from config import ADMIN_ID # Импортируем ADMIN_ID
from utils import AdminStates # Импортируем AdminStates
import logging

router = Router()

logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    db = next(get_db())
    user_id = message.from_user.id
    user = db.query(User).filter(User.telegram_id == user_id).first()

    bot_description = (
        "Привет! Я твой личный FitBuddy – помощник в достижении целей по здоровью и фитнесу.\n\n"
        "Со мной ты сможешь:\n"
        "•   <b>Отслеживать питание:</b> Легко добавляй съеденную еду. Я помогу найти калорийность или ты сможешь ввести ее вручную. Сохраняй любимые блюда для быстрого доступа!\n"
        "•   <b>Фиксировать тренировки:</b> Записывай свои тренировки, указывая детали, и следи за историей своих занятий.\n"
        "•   <b>Контролировать вес:</b> Вноси данные о своем весе, и я построю наглядный график твоего прогресса.\n"
        "•   <b>Получать напоминания:</b> Устанавливай напоминания, чтобы не забывать о важных задачах.\n"
        "•   <b>Следить за прогрессом:</b> Получай актуальную информацию о потребленных калориях, а также зарабатывай очки и достижения за свою активность!\n\n"
        "Давай начнем твою регистрацию!"
    )

    if user:
        await message.answer(f"👋 С возвращением, {message.from_user.first_name}! Твой профиль уже существует.", reply_markup=get_main_keyboard())
    else:
        await message.answer(bot_description, parse_mode="HTML")
        await message.answer("Сколько тебе лет?", reply_markup=get_cancel_keyboard())
        await state.set_state(RegistrationStates.waiting_for_age)
        await add_state_to_history(state, RegistrationStates.waiting_for_age.state) # Добавляем состояние в историю
        # Сохраняем first_name и username при старте регистрации
        await state.update_data(first_name=message.from_user.first_name, username=message.from_user.username)
    db.close()

@router.message(RegistrationStates.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if not (5 < age < 120):
            await message.answer("⚠️ Пожалуйста, введи корректный возраст (от 5 до 120 лет).", reply_markup=get_cancel_keyboard())
            return
        await state.update_data(age=age)
        await message.answer("Какой у тебя рост в сантиметрах?", reply_markup=get_cancel_keyboard())
        await state.set_state(RegistrationStates.waiting_for_height)
        await add_state_to_history(state, RegistrationStates.waiting_for_height.state) # Добавляем состояние в историю
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи возраст числом.", reply_markup=get_cancel_keyboard())

@router.message(RegistrationStates.waiting_for_height)
async def process_height(message: types.Message, state: FSMContext):
    try:
        height = float(message.text)
        if not (50 < height < 250):
            await message.answer("⚠️ Пожалуйста, введи корректный рост в сантиметрах (от 50 до 250).", reply_markup=get_cancel_keyboard())
            return
        await state.update_data(height=height)
        await message.answer("Какой у тебя текущий вес в килограммах?", reply_markup=get_cancel_keyboard())
        await state.set_state(RegistrationStates.waiting_for_weight)
        await add_state_to_history(state, RegistrationStates.waiting_for_weight.state) # Добавляем состояние в историю
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи рост числом.", reply_markup=get_cancel_keyboard())

@router.message(RegistrationStates.waiting_for_weight)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text)
        if not (20 < weight < 300):
            await message.answer("⚠️ Пожалуйста, введи корректный вес в килограммах (от 20 до 300).", reply_markup=get_cancel_keyboard())
            return
        await state.update_data(weight=weight)

        # Предлагаем цели с помощью инлайн-клавиатуры
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Похудеть", callback_data="goal_похудеть")],
                [types.InlineKeyboardButton(text="Набрать массу", callback_data="goal_набрать_массу")],
                [types.InlineKeyboardButton(text="Поддерживать вес", callback_data="goal_поддерживать")],
                [types.InlineKeyboardButton(text="Отмена", callback_data="cancel_registration")] # Кнопка отмены
            ]
        )
        await message.answer("Какова твоя цель?", reply_markup=keyboard)
        await state.set_state(RegistrationStates.waiting_for_goal)
        await add_state_to_history(state, RegistrationStates.waiting_for_goal.state) # Добавляем состояние в историю

    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи вес числом.", reply_markup=get_cancel_keyboard())

# Обработчик для коллбэков от кнопок цели
@router.callback_query(F.data.startswith("goal_"), RegistrationStates.waiting_for_goal)
async def process_goal_callback(callback_query: types.CallbackQuery, state: FSMContext):
    goal = callback_query.data.split("_")[1]
    await state.update_data(goal=goal)

    user_data = await state.get_data()
    user_id = callback_query.from_user.id
    db = next(get_db())

    new_user = User(
        telegram_id=user_id,
        first_name=user_data.get('first_name'), # Получаем first_name из состояния
        username=user_data.get('username'), # Получаем username из состояния
        age=user_data['age'],
        height=user_data['height'],
        weight=user_data['weight'],
        goal=goal,
        calorie_target=None # Цель по калориям будет установлена на следующем шаге
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()

    await callback_query.message.answer("🎉 Отлично! Регистрация завершена. Теперь укажи свою ежедневную цель по калориям (например: 2000).")
    await state.set_state(RegistrationStates.waiting_for_calorie_target_on_registration)
    await add_state_to_history(state, RegistrationStates.waiting_for_calorie_target_on_registration.state) # Добавляем состояние в историю
    await callback_query.answer() # Отвечаем на callback, чтобы убрать индикатор загрузки

@router.message(RegistrationStates.waiting_for_goal) # Добавляем этот обработчик, если пользователь введет текст вместо нажатия кнопки
async def process_goal_text_fallback(message: types.Message):
    await message.answer("⚠️ Пожалуйста, выбери цель из предложенных вариантов или используй кнопки.", reply_markup=get_main_keyboard())

@router.message(RegistrationStates.waiting_for_calorie_target_on_registration)
async def process_calorie_target_on_registration(message: types.Message, state: FSMContext):
    db = next(get_db())
    try:
        calorie_target = int(message.text)
        if calorie_target <= 0:
            await message.answer("⚠️ Цель по калориям должна быть положительным числом.", reply_markup=get_main_keyboard())
            return
        
        user_id = message.from_user.id
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.calorie_target = calorie_target
            db.commit()
            db.refresh(user)
            await message.answer(f"✅ Твоя ежедневная цель по калориям установлена на {calorie_target} ккал. Регистрация завершена!", reply_markup=get_main_keyboard())
            await state.clear()
            await clear_state_history(state) # Очищаем историю состояний
        else:
            await message.answer("Пользователь не найден. Пожалуйста, зарегистрируйтесь через /start.", reply_markup=get_main_keyboard())

    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи цель по калориям числом.", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"Произошла ошибка при сохранении цели: {e}", reply_markup=get_main_keyboard())
    finally:
        db.close()
        await state.clear()
        await clear_state_history(state)

@router.message(F.text == "Отмена", State("*")) # Обработчик для текстовой кнопки "Отмена" во всех состояниях
@router.callback_query(F.data == "cancel_registration", State("*")) # Обработчик для инлайн кнопки "Отмена" во всех состояниях
async def cmd_cancel(callback_or_message: types.CallbackQuery | types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        if isinstance(callback_or_message, types.CallbackQuery):
            await callback_or_message.message.edit_text("Нет активных действий для отмены.", reply_markup=None)
            await callback_or_message.message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
            await callback_or_message.answer()
        else:
            await callback_or_message.answer("Нет активных действий для отмены.", reply_markup=get_main_keyboard())
        return
    
    await state.clear()
    await clear_state_history(state) # Очищаем историю состояний при отмене
    if isinstance(callback_or_message, types.CallbackQuery):
        await callback_or_message.message.edit_text("🚫 Действие отменено.", reply_markup=None)
        await callback_or_message.message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
        await callback_or_message.answer()
    else:
        await callback_or_message.answer("🚫 Действие отменено.", reply_markup=get_main_keyboard())

@router.message(F.text == "Профиль")
async def handle_profile_button(message: types.Message):
    await cmd_profile(message)

@router.message(F.text == "Калории за день")
async def handle_today_button(message: types.Message, state: FSMContext):
    await cmd_today(message, state)

# Обработчики для новых кнопок главного меню
@router.message(F.text == "Еда")
async def handle_food_menu(message: types.Message, state: FSMContext):
    await message.answer("🍎 Меню еды:", reply_markup=get_food_menu_keyboard())
    await add_state_to_history(state, FoodStates.waiting_for_food_name.state) # Добавляем состояние для FoodStates

@router.message(F.text == "Тренировки")
async def handle_workout_menu(message: types.Message, state: FSMContext):
    await message.answer("💪 Меню тренировок:", reply_markup=get_workout_menu_keyboard())
    await add_state_to_history(state, WorkoutStates.waiting_for_workout_name.state) # Добавляем состояние для WorkoutStates

@router.message(F.text == "Вес")
async def handle_weight_menu(message: types.Message, state: FSMContext):
    await message.answer("⚖️ Меню веса:", reply_markup=get_weight_menu_keyboard())
    await add_state_to_history(state, WeightStates.waiting_for_new_weight.state) # Добавляем состояние для WeightStates

@router.message(F.text == "Напоминание")
async def handle_reminder_button(message: types.Message, state: FSMContext):
    await cmd_reminder(message, state)

@router.message(F.text == "Рейтинг")
async def handle_rating_menu(message: types.Message, state: FSMContext):
    await message.answer("🌟 Меню рейтинга:", reply_markup=get_rating_menu_keyboard())
    await add_state_to_history(state, UserStateHistory.history.state) # Состояние для меню рейтинга

@router.message(F.text == "Друзья")
async def handle_friends_menu_button(message: types.Message, state: FSMContext):
    await message.answer("👥 Меню друзей:", reply_markup=get_friend_menu_keyboard())
    await add_state_to_history(state, UserStateHistory.history.state) # Общее состояние для меню друзей

@router.message(F.text == "Таблица лидеров")
async def handle_leaderboard_menu(message: types.Message, state: FSMContext):
    await message.answer("🏆 Таблица лидеров:", reply_markup=get_leaderboard_keyboard())
    await state.set_state(LeaderboardStates.waiting_for_leaderboard_type)
    await add_state_to_history(state, LeaderboardStates.waiting_for_leaderboard_type.state)

@router.message(F.text == "Назад")
@router.message(F.text == "Назад к главному меню")
async def handle_back_to_main_menu(message: types.Message, state: FSMContext):
    print(f"DEBUG (handle_back_to_main_menu): Message text: {message.text}")
    previous_state_name = await get_previous_state(state) # Получаем предыдущее состояние из истории
    print(f"DEBUG (handle_back_to_main_menu): Previous state from history: {previous_state_name}")

    if previous_state_name:
        # Определяем, куда вернуться, исходя из previous_state_name
        if "WorkoutStates" in previous_state_name or "ExerciseLibraryStates" in previous_state_name:
            await message.answer("Возвращаемся в меню тренировок.", reply_markup=get_workout_menu_keyboard())
            await state.set_state(WorkoutStates.waiting_for_workout_name) 
        elif "FoodStates" in previous_state_name or "FavoriteFoodStates" in previous_state_name:
            await message.answer("Возвращаемся в меню еды.", reply_markup=get_food_menu_keyboard())
            await state.set_state(FoodStates.waiting_for_food_name) 
        elif "WeightStates" in previous_state_name:
            await message.answer("Возвращаемся в меню веса.", reply_markup=get_weight_menu_keyboard())
            await state.set_state(WeightStates.waiting_for_new_weight) 
        elif "ReminderStates" in previous_state_name:
            await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard()) 
            await state.clear()
            await clear_state_history(state)
        elif "LeaderboardStates" in previous_state_name:
            await message.answer("Возвращаемся в меню рейтинга.", reply_markup=get_rating_menu_keyboard())
            await state.clear()
            await clear_state_history(state)
        elif "FriendStates" in previous_state_name: # Если это было меню друзей
            await message.answer("Возвращаемся в меню рейтинга.", reply_markup=get_rating_menu_keyboard())
            await state.clear()
            await clear_state_history(state)
        elif "UserStateHistory" in previous_state_name: # Если это было меню рейтинга или другое общее меню
            await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
            await state.clear() # Очищаем состояние, так как вернулись в главное меню
            await clear_state_history(state)
        else:
            await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
            await state.clear()
            await clear_state_history(state)
    else:
        print("DEBUG (handle_back_to_main_menu): История состояний пуста, возвращаемся в главное меню.")
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
        await state.clear()
        await clear_state_history(state)

@router.message(F.text == "Любимые блюда")
async def handle_favorite_foods_menu(message: types.Message):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    db.close()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.")
        db.close()
        return
    favorite_foods = db.query(FavoriteFood).filter(FavoriteFood.user_id == user.id).all()
    db.close()

    if favorite_foods:
        await message.answer("❤️ Твои любимые блюда:", reply_markup=get_favorite_food_keyboard(favorite_foods))
    else:
        keyboard = InlineKeyboardBuilder()
        keyboard.row(types.InlineKeyboardButton(text="Добавить любимое блюдо", callback_data="add_favorite_food"))
        keyboard.row(types.InlineKeyboardButton(text="Назад", callback_data="back_to_food_menu"))
        await message.answer("У тебя пока нет любимых блюд. Добавь первое!", reply_markup=keyboard.as_markup())

@router.callback_query(F.data == "back_to_food_menu")
async def handle_back_to_food_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("Возвращаемся в меню еды.", reply_markup=None)
    await callback_query.message.answer("Меню еды:", reply_markup=get_food_menu_keyboard())
    await callback_query.answer()

@router.callback_query(F.data == "add_favorite_food")
async def handle_add_favorite_food_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("➕ Введи название любимого блюда (например, 'Овсянка'):")
    await state.set_state(FavoriteFoodStates.waiting_for_favorite_food_name)
    await add_state_to_history(state, FavoriteFoodStates.waiting_for_favorite_food_name.state)
    await callback_query.answer()

@router.message(FavoriteFoodStates.waiting_for_favorite_food_name)
async def process_favorite_food_name(message: types.Message, state: FSMContext):
    favorite_food_name = message.text.strip()
    if not favorite_food_name:
        await message.answer("⚠️ Пожалуйста, введи название блюда.", reply_markup=get_food_menu_keyboard())
        return
    await state.update_data(favorite_food_name=favorite_food_name)
    await message.answer("Сколько калорий на 100г в этом блюде? (Например, 150)")
    await state.set_state(FavoriteFoodStates.waiting_for_favorite_food_calories)
    await add_state_to_history(state, FavoriteFoodStates.waiting_for_favorite_food_calories.state)
    await callback_query.answer()

@router.message(FavoriteFoodStates.waiting_for_favorite_food_calories)
async def process_favorite_food_calories(message: types.Message, state: FSMContext):
    db = next(get_db())
    try:
        calories_per_100g = int(message.text)
        if calories_per_100g <= 0:
            await message.answer("⚠️ Калории должны быть положительным числом.", reply_markup=get_food_menu_keyboard())
            return
        user_data = await state.get_data()
        user_id = db.query(User).filter(User.telegram_id == message.from_user.id).first().id
        
        new_favorite = await add_favorite_food(db, user_id, user_data['favorite_food_name'], calories_per_100g)
        db.close()
        await message.answer(f"✅ Любимое блюдо '{new_favorite.name}' ({new_favorite.calories_per_100g} ккал/100г) добавлено!", reply_markup=get_food_menu_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи калории числом.", reply_markup=get_food_menu_keyboard())
        db.close()
    except Exception as e:
        await message.answer(f"Произошла ошибка при добавлении любимого блюда: {e}", reply_markup=get_food_menu_keyboard())
        db.close()
        await state.clear()
        await clear_state_history(state)

@router.callback_query(F.data == "remove_favorite_food_start")
async def handle_remove_favorite_food_start(callback_query: types.CallbackQuery):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == callback_query.from_user.id).first()
    if not user:
        await callback_query.message.edit_text("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=None)
        await callback_query.message.answer("Возвращаемся в меню еды.", reply_markup=get_food_menu_keyboard())
        db.close()
        await callback_query.answer()
        return
    favorite_foods = db.query(FavoriteFood).filter(FavoriteFood.user_id == user.id).all()
    db.close()

    if favorite_foods:
        builder = InlineKeyboardBuilder()
        for food in favorite_foods:
            builder.button(text=f"❌ {food.name}", callback_data=f"delete_favorite_food_{food.id}")
        builder.row(types.InlineKeyboardButton(text="Отмена", callback_data="back_to_food_menu"))
        await callback_query.message.edit_text("🗑️ Выбери блюдо для удаления:", reply_markup=builder.as_markup())
    else:
        await callback_query.message.edit_text("У тебя нет любимых блюд для удаления.", reply_markup=None)
        await callback_query.message.answer("Меню еды:", reply_markup=get_food_menu_keyboard())
    await callback_query.answer()

@router.callback_query(F.data.startswith("delete_favorite_food_"))
async def handle_delete_favorite_food(callback_query: types.CallbackQuery):
    db = next(get_db())
    favorite_food_id = int(callback_query.data.split("_")[3])
    await remove_favorite_food(db, favorite_food_id)
    db.close()
    await callback_query.answer("✅ Блюдо удалено.")
    # Обновляем список любимых блюд после удаления
    await handle_favorite_foods_menu(callback_query.message) # Перезагружаем меню любимых блюд

@router.callback_query(F.data.startswith("select_favorite_food_"))
async def handle_select_favorite_food(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer() # Убираем индикатор загрузки
    db = next(get_db())
    favorite_food_id = int(callback_query.data.split("_")[3])
    selected_favorite_food = db.query(FavoriteFood).filter(FavoriteFood.id == favorite_food_id).first()
    db.close()

    if selected_favorite_food:
        await state.update_data(selected_food={
            'food_name': selected_favorite_food.name,
            'calories_per_100g': selected_favorite_food.calories_per_100g
        })
        await callback_query.message.edit_text(f"✅ Выбран: '{selected_favorite_food.name}' ({selected_favorite_food.calories_per_100g} ккал/100г). Сколько грамм ты съел?", reply_markup=None)
        await state.set_state(FoodStates.waiting_for_calories_quantity)
    else:
        await callback_query.message.edit_text("⚠️ Не удалось найти выбранное любимое блюдо.", reply_markup=get_food_menu_keyboard())
        await state.clear()

# Изменение существующих обработчиков для использования вложенных клавиатур
@router.message(F.text == "Добавить еду")
async def handle_add_food_button(message: types.Message, state: FSMContext):
    await cmd_food(message, state)

@router.message(F.text == "Логировать тренировку")
async def handle_log_workout_button(message: types.Message, state: FSMContext):
    await cmd_workout(message, state)

@router.message(F.text == "Ввести вес")
async def handle_enter_weight_button(message: types.Message, state: FSMContext):
    await cmd_weight(message, state)

@router.message(F.text == "График веса")
async def handle_weight_chart_button(message: types.Message, state: FSMContext):
    await cmd_weight_chart(message, state)

@router.message(F.text == "Напоминание")
async def handle_reminder_button(message: types.Message, state: FSMContext):
    await cmd_reminder(message, state)

@router.message(F.text == "Очки")
async def handle_points_button(message: types.Message, state: FSMContext):
    await cmd_points(message, state)

@router.message(F.text == "Достижения")
async def handle_achievements_button(message: types.Message, state: FSMContext):
    await cmd_achievements(message, state)

@router.message(F.text == "История тренировок")
async def handle_workout_history_menu(message: types.Message):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    db.close()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_workout_menu_keyboard())
        return
    
    await message.answer("Показать историю тренировок за:", reply_markup=get_workout_history_keyboard())

@router.message(F.text == "За неделю")
async def handle_weekly_workout_history(message: types.Message):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_workout_history_keyboard())
        db.close()
        return

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(weeks=1)

    workouts = db.query(Workout).filter(
        Workout.user_id == user.id,
        func.date(Workout.date) >= start_date,
        func.date(Workout.date) <= end_date
    ).order_by(Workout.date.desc()).all()
    db.close()

    if workouts:
        history_text = f"<b>🗓️ История тренировок за неделю ({start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}):</b>\n\n"
        for workout in workouts:
            history_text += f"• {workout.name} ({workout.duration} мин, {workout.calories_burned} ккал сожжено) - {workout.date.strftime('%Y-%m-%d')}\n"
        await message.answer(history_text, parse_mode="HTML", reply_markup=get_workout_history_keyboard())
    else:
        await message.answer("🙁 За последнюю неделю тренировок не найдено.", reply_markup=get_workout_history_keyboard())

@router.message(F.text == "За месяц")
async def handle_monthly_workout_history(message: types.Message):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_workout_history_keyboard())
        db.close()
        return

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=30) # Приблизительно месяц

    workouts = db.query(Workout).filter(
        Workout.user_id == user.id,
        func.date(Workout.date) >= start_date,
        func.date(Workout.date) <= end_date
    ).order_by(Workout.date.desc()).all()
    db.close()

    if workouts:
        history_text = f"<b>🗓️ История тренировок за месяц ({start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}):</b>\n\n"
        for workout in workouts:
            history_text += f"• {workout.name} ({workout.duration} мин, {workout.calories_burned} ккал сожжено) - {workout.date.strftime('%Y-%m-%d')}\n"
        await message.answer(history_text, parse_mode="HTML", reply_markup=get_workout_history_keyboard())
    else:
        await message.answer("🙁 За последний месяц тренировок не найдено.", reply_markup=get_workout_history_keyboard())

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if user:
        await message.answer(
            f"<b>📝 Твой профиль:</b>\n"
            f"Возраст: {user.age} лет\n"
            f"Рост: {user.height} см\n"
            f"Вес: {user.weight} кг\n"
            f"Цель: {user.goal}\n"
            f"Цель по калориям: {user.calorie_target if user.calorie_target else 'Не установлена'} ккал\n"
            f"Очки: {user.points or 0}\n"
            f"Серия: {user.streak or 0} дней",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
    db.close()

@router.message(Command("food"))
async def cmd_food(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    db.close()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        return

    await message.answer("❓ Что ты съел? (Например: 'Яблоко 200 г' или просто 'Яблоко')", reply_markup=get_food_menu_keyboard())
    await state.set_state(FoodStates.waiting_for_food_name)
    await add_state_to_history(state, FoodStates.waiting_for_food_name.state)

@router.message(FoodStates.waiting_for_food_name)
async def process_food_name(message: types.Message, state: FSMContext):
    food_input = message.text.strip()
    if not food_input:
        await message.answer("⚠️ Пожалуйста, введи название продукта.", reply_markup=get_food_menu_keyboard())
        return

    await state.update_data(raw_food_input=food_input)
    await message.answer(f"🔍 Ищу '{food_input}' в базе Open Food Facts...")

    open_food_facts_results = await search_open_food_facts(food_input)

    if open_food_facts_results:
        if len(open_food_facts_results) > 1:
            keyboard_builder = InlineKeyboardBuilder()
            for i, food in enumerate(open_food_facts_results[:5]):
                keyboard_builder.button(text=f"{food['food_name']} ({food['calories_per_100g']} ккал/100г)", callback_data=f"select_off_food_{i}")
            keyboard_builder.adjust(1)
            keyboard_builder.row(InlineKeyboardButton(text="Отмена", callback_data="back_to_food_menu")) # Добавляем кнопку отмены
            await state.update_data(open_food_facts_options=open_food_facts_results)
            await message.answer("Я нашел несколько вариантов. Выбери один:", reply_markup=keyboard_builder.as_markup())
            await state.set_state(FoodStates.waiting_for_food_selection)
            await add_state_to_history(state, FoodStates.waiting_for_food_selection.state)
        else:
            selected_food = open_food_facts_results[0]
            await state.update_data(selected_food=selected_food)
            await message.answer(f"Я нашел '{selected_food['food_name']}' ({selected_food['calories_per_100g']} ккал/100г). Сколько грамм ты съел?", reply_markup=get_food_menu_keyboard())
            await state.set_state(FoodStates.waiting_for_calories_quantity)
            await add_state_to_history(state, FoodStates.waiting_for_calories_quantity.state)
    else:
        # Если Open Food Facts API ничего не нашел, возвращаемся к старому процессу
        food_name, quantity = parse_food_input(food_input)
        if food_name and quantity is not None:
            calories_per_100g = get_calories_per_100g(food_name)
            if calories_per_100g:
                total_calories = int((calories_per_100g / 100) * quantity)
                
                db_session = next(get_db())
                user_id = db_session.query(User).filter(User.telegram_id == message.from_user.id).first().id
                new_meal = Meal(
                    user_id=user_id,
                    name=f"{food_name} ({quantity} г)",
                    calories=total_calories
                )
                db_session.add(new_meal)
                db_session.commit()
                db_session.refresh(new_meal)

                # Проверяем достижение цели по калориям и обновляем серию
                user_for_target_check = db_session.query(User).filter(User.telegram_id == message.from_user.id).first()
                if user_for_target_check and user_for_target_check.calorie_target:
                    today = datetime.utcnow().date()
                    total_calories_today = db_session.query(func.sum(Meal.calories)).filter(
                        Meal.user_id == user_id,
                        func.date(Meal.date) == today
                    ).scalar()
                    if total_calories_today is None: total_calories_today = 0

                    calorie_streak_changed = await update_calorie_streak(db_session, user_for_target_check, total_calories_today) # Обновляем калорийную серию

                    if total_calories_today >= user_for_target_check.calorie_target:
                        message_text = f"🎉 Поздравляю! Вы достигли своей ежедневной цели в {user_for_target_check.calorie_target} ккал!\nВаша серия калорий: {user_for_target_check.calorie_streak} дней."
                        await message.answer(message_text, reply_markup=get_food_menu_keyboard())
                        if calorie_streak_changed:
                            await notify_friends_about_achievement(db_session, bot, user_for_target_check, f"достиг цели по калориям {user_for_target_check.calorie_streak} дней подряд ({user_for_target_check.calorie_target} ккал)!")
                    else:
                        await message.answer(f"Вы потребили {total_calories_today} из {user_for_target_check.calorie_target} ккал. Осталось: {user_for_target_check.calorie_target - total_calories_today} ккал.", reply_markup=get_food_menu_keyboard())

                # Геймификация: начисляем очки за добавление еды
                awarded, total_points, streak, streak_changed, _ = register_activity(db_session, message.from_user.id, 10, "meal_logged")
                if awarded > 0:
                    message_text = f"🌟 +{awarded} очков за запись питания. Серия: {streak} дн., всего: {total_points} очков."
                    await message.answer(message_text)
                    if streak_changed:
                        await notify_friends_about_achievement(db_session, bot, user_for_target_check, f"достиг серии активности {streak} дней подряд!")

                db_session.close()

                await message.answer(f"✅ Добавлено: {food_name} ({quantity} г) - {total_calories} ккал.", reply_markup=get_food_menu_keyboard())
                await state.clear()
                await clear_state_history(state) # Очищаем историю состояний
                return
            else:
                await message.answer(f"❓ Я не знаю калорийность для '{food_name}'. Пожалуйста, введи калории вручную.", reply_markup=get_food_menu_keyboard())
                await state.update_data(food_name=food_name)
                await message.answer("Сколько калорий в этой еде?", reply_markup=get_food_menu_keyboard())
                await state.set_state(FoodStates.waiting_for_calories)
                await add_state_to_history(state, FoodStates.waiting_for_calories.state)
                return
        elif food_name:
            calories_per_100g = get_calories_per_100g(food_name)
            if calories_per_100g:
                await state.update_data(food_name=food_name, calories_per_100g=calories_per_100g) # Сохраняем калории на 100г
                await message.answer(f"Я нашел '{food_name}' ({calories_per_100g} ккал на 100г). Сколько грамм ты съел?", reply_markup=get_food_menu_keyboard())
                await state.set_state(FoodStates.waiting_for_calories_quantity)
                await add_state_to_history(state, FoodStates.waiting_for_calories_quantity.state)
                return
            else:
                await message.answer(f"❓ Я не знаю калорийность для '{food_name}'. Пожалуйста, введи калории вручную.", reply_markup=get_food_menu_keyboard())
                await state.update_data(food_name=food_name)
                await message.answer("Сколько калорий в этой еде?", reply_markup=get_food_menu_keyboard())
                await state.set_state(FoodStates.waiting_for_calories)
                await add_state_to_history(state, FoodStates.waiting_for_calories.state)
                return

        await state.update_data(food_name=food_input)
        await message.answer("Сколько калорий в этой еде?", reply_markup=get_food_menu_keyboard())
        await state.set_state(FoodStates.waiting_for_calories)
        await add_state_to_history(state, FoodStates.waiting_for_calories.state)

@router.callback_query(F.data.startswith("select_off_food_"), FoodStates.waiting_for_food_selection)
async def process_open_food_facts_selection(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer() # Убираем индикатор загрузки
    selected_index = int(callback_query.data.split("_")[3])
    user_data = await state.get_data()
    open_food_facts_options = user_data.get('open_food_facts_options')

    if open_food_facts_options and 0 <= selected_index < len(open_food_facts_options):
        selected_food = open_food_facts_options[selected_index]
        await state.update_data(selected_food=selected_food)
        await callback_query.message.edit_text(f"✅ Выбран: '{selected_food['food_name']}' ({selected_food['calories_per_100g']} ккал/100г). Сколько грамм ты съел?", reply_markup=None)
        await state.set_state(FoodStates.waiting_for_calories_quantity)
        await add_state_to_history(state, FoodStates.waiting_for_calories_quantity.state)
    else:
        await callback_query.message.edit_text("⚠️ Неверный выбор продукта. Пожалуйста, попробуй снова.", reply_markup=None)
        await state.clear()
        await clear_state_history(state)

@router.message(FoodStates.waiting_for_calories_quantity)
async def process_calories_quantity(message: types.Message, state: FSMContext, bot: Bot):
    db_session = next(get_db())
    try:
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("⚠️ Количество должно быть положительным числом.", reply_markup=get_food_menu_keyboard())
            return
        user_data = await state.get_data()
        selected_food = user_data.get('selected_food')

        if selected_food and selected_food.get('calories_per_100g') is not None:
            food_name = selected_food['food_name']
            calories_per_100g = selected_food['calories_per_100g']
            total_calories = int((calories_per_100g / 100) * quantity)
            
            user_id = db_session.query(User).filter(User.telegram_id == message.from_user.id).first().id
            new_meal = Meal(
                user_id=user_id,
                name=f"{food_name} ({quantity} г)",
                calories=total_calories
            )
            db_session.add(new_meal)
            db_session.commit()
            db_session.refresh(new_meal)

            # Проверяем достижение цели по калориям и обновляем серию
            user_for_target_check = db_session.query(User).filter(User.telegram_id == message.from_user.id).first()
            if user_for_target_check and user_for_target_check.calorie_target:
                today = datetime.utcnow().date()
                total_calories_today = db_session.query(func.sum(Meal.calories)).filter(
                    Meal.user_id == user_id,
                    func.date(Meal.date) == today
                ).scalar()
                if total_calories_today is None: total_calories_today = 0

                calorie_streak_changed = await update_calorie_streak(db_session, user_for_target_check, total_calories_today) # Обновляем калорийную серию

                if total_calories_today >= user_for_target_check.calorie_target:
                    message_text = f"🎉 Поздравляю! Вы достигли своей ежедневной цели в {user_for_target_check.calorie_target} ккал!\nВаша серия калорий: {user_for_target_check.calorie_streak} дней."
                    await message.answer(message_text, reply_markup=get_food_menu_keyboard())
                    if calorie_streak_changed:
                        await notify_friends_about_achievement(db_session, bot, user_for_target_check, f"достиг цели по калориям {user_for_target_check.calorie_streak} дней подряд ({user_for_target_check.calorie_target} ккал)!")
                else:
                    await message.answer(f"Вы потребили {total_calories_today} из {user_for_target_check.calorie_target} ккал. Осталось: {user_for_target_check.calorie_target - total_calories_today} ккал.", reply_markup=get_food_menu_keyboard())

            # Геймификация: начисляем очки за добавление еды
            awarded, total_points, streak, streak_changed, _ = register_activity(db_session, message.from_user.id, 10, "meal_logged")
            if awarded > 0:
                message_text = f"🌟 +{awarded} очков за запись питания. Серия: {streak} дн., всего: {total_points} очков."
                await message.answer(message_text)
                if streak_changed:
                    await notify_friends_about_achievement(db_session, bot, user_for_target_check, f"достиг серии активности {streak} дней подряд!")

            db_session.close()

            await message.answer(f"✅ Добавлено: {food_name} ({quantity} г) - {total_calories} ккал.", reply_markup=get_food_menu_keyboard())
            await state.clear()
            await clear_state_history(state) # Очищаем историю состояний
            return
        else:
            # Fallback к старому поведению, если selected_food не найден или нет калорий
            food_name = user_data.get('food_name', user_data.get('raw_food_input', 'продукт'))
            await message.answer(f"⚠️ Не удалось получить калорийность для '{food_name}'. Пожалуйста, введи калории вручную.", reply_markup=get_food_menu_keyboard())
            await state.update_data(food_name=food_name)
            await message.answer("Сколько калорий в этой еде?", reply_markup=get_food_menu_keyboard())
            await state.set_state(FoodStates.waiting_for_calories)
            await add_state_to_history(state, FoodStates.waiting_for_calories.state)
    except ValueError:
        await message.answer("⚠️ Количество должно быть положительным числом.", reply_markup=get_food_menu_keyboard())
    except Exception as e:
        await message.answer(f"Произошла ошибка при сохранении: {e}", reply_markup=get_food_menu_keyboard())
        db_session.close()
        await state.clear()
        await clear_state_history(state) # Очищаем историю состояний

@router.message(FoodStates.waiting_for_calories)
async def process_calories(message: types.Message, state: FSMContext, bot: Bot):
    db_session = next(get_db())
    try:
        calories = int(message.text)
        if calories <= 0:
            await message.answer("⚠️ Калории должны быть положительным числом.", reply_markup=get_food_menu_keyboard())
            return
        user_data = await state.get_data()
        user_id = db_session.query(User).filter(User.telegram_id == message.from_user.id).first().id

        new_meal = Meal(
            user_id=user_id,
            name=user_data['food_name'],
            calories=calories
        )

        db_session.add(new_meal)
        db_session.commit()
        db_session.refresh(new_meal)

        # Проверяем достижение цели по калориям и обновляем серию
        user_for_target_check = db_session.query(User).filter(User.telegram_id == message.from_user.id).first()
        if user_for_target_check and user_for_target_check.calorie_target:
            today = datetime.utcnow().date()
            total_calories_today = db_session.query(func.sum(Meal.calories)).filter(
                Meal.user_id == user_id,
                func.date(Meal.date) == today
            ).scalar()
            if total_calories_today is None: total_calories_today = 0

            calorie_streak_changed = await update_calorie_streak(db_session, user_for_target_check, total_calories_today) # Обновляем калорийную серию

            if total_calories_today >= user_for_target_check.calorie_target:
                message_text = f"🎉 Поздравляю! Вы достигли своей ежедневной цели в {user_for_target_check.calorie_target} ккал!\nВаша серия калорий: {user_for_target_check.calorie_streak} дней."
                await message.answer(message_text, reply_markup=get_food_menu_keyboard())
                if calorie_streak_changed:
                    await notify_friends_about_achievement(db_session, bot, user_for_target_check, f"достиг цели по калориям {user_for_target_check.calorie_streak} дней подряд ({user_for_target_check.calorie_target} ккал)!")
            else:
                await message.answer(f"Вы потребили {total_calories_today} из {user_for_target_check.calorie_target} ккал. Осталось: {user_for_target_check.calorie_target - total_calories_today} ккал.", reply_markup=get_food_menu_keyboard())

        # Геймификация: очки за запись еды
        awarded, total_points, streak, streak_changed, _ = register_activity(db_session, message.from_user.id, 10, "meal_logged")
        if awarded > 0:
            message_text = f"🌟 +{awarded} очков за запись питания. Серия: {streak} дн., всего: {total_points} очков."
            await message.answer(message_text)
            if streak_changed:
                await notify_friends_about_achievement(db_session, bot, user_for_target_check, f"достиг серии активности {streak} дней подряд!")

        db_session.close()

        await message.answer(f"✅ Добавлено: {user_data['food_name']} - {calories} ккал.", reply_markup=get_food_menu_keyboard())
        await state.clear()
        await clear_state_history(state) # Очищаем историю состояний
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи калории числом.", reply_markup=get_food_menu_keyboard())
    except Exception as e:
        await message.answer(f"Произошла ошибка при сохранении: {e}", reply_markup=get_food_menu_keyboard())
        db_session.close()
        await state.clear()
        await clear_state_history(state) # Очищаем историю состояний

@router.message(Command("today"))
async def cmd_today(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        db.close()
        return

    today = datetime.utcnow().date()
    meals_today = db.query(Meal).filter(Meal.user_id == user.id, func.date(Meal.date) == today).all()
    total_calories = sum(meal.calories for meal in meals_today)

    calorie_target = user.calorie_target # Получаем цель по калориям пользователя
    response_text = f"🗓️ Сегодня Вы потребили: {total_calories} ккал.\n"

    if calorie_target:
        percentage = (total_calories / calorie_target) * 100 if calorie_target > 0 else 0
        response_text += f"Ваша цель: {calorie_target} ккал.\n"
        response_text += f"Выполнено: {percentage:.2f}% от нормы.\n"
        response_text += f"Серия калорий: {user.calorie_streak or 0} дней."
    else:
        response_text += "Цель по калориям не установлена. Используйте /set_calorie_target для установки цели."

    await message.answer(response_text, reply_markup=get_main_keyboard())
    await add_state_to_history(state, UserStateHistory.history.state) # Добавляем состояние для cmd_today
    db.close()

@router.message(Command("set_calorie_target"))
async def cmd_set_calorie_target(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    db.close()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        return

    await message.answer("🎯 Введи свою ежедневную цель по калориям (например: 2000):", reply_markup=get_cancel_keyboard())
    await state.set_state(CalorieTargetStates.waiting_for_calorie_target)
    await add_state_to_history(state, CalorieTargetStates.waiting_for_calorie_target.state)

@router.message(CalorieTargetStates.waiting_for_calorie_target)
async def process_calorie_target(message: types.Message, state: FSMContext):
    db = next(get_db())
    try:
        calorie_target = int(message.text)
        if calorie_target <= 0:
            await message.answer("⚠️ Цель по калориям должна быть положительным числом.", reply_markup=get_main_keyboard())
            return
        user_id = message.from_user.id
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.calorie_target = calorie_target
            db.commit()
            db.refresh(user)
            await message.answer(f"✅ Твоя ежедневная цель по калориям установлена на {calorie_target} ккал.", reply_markup=get_main_keyboard())
            await state.clear()
            await clear_state_history(state)
        else:
            await message.answer("Пользователь не найден. Пожалуйста, зарегистрируйтесь через /start.", reply_markup=get_main_keyboard())
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи цель по калориям числом.", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"Произошла ошибка при сохранении цели: {e}", reply_markup=get_main_keyboard())
    finally:
        db.close()
        await state.clear()
        await clear_state_history(state)

@router.message(Command("workout"))
async def cmd_workout(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    db.close()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        return

    await message.answer("🏋️ Введи название для своей тренировки:", reply_markup=get_workout_menu_keyboard())
    await state.set_state(WorkoutStates.waiting_for_workout_name)
    await add_state_to_history(state, WorkoutStates.waiting_for_workout_name.state)

@router.message(WorkoutStates.waiting_for_workout_name)
async def process_workout_name(message: types.Message, state: FSMContext):
    workout_name = message.text.strip()
    if not workout_name:
        await message.answer("⚠️ Пожалуйста, введи название тренировки.", reply_markup=get_workout_menu_keyboard())
        return
    await state.update_data(workout_name=workout_name)
    await message.answer("⏱️ Сколько минут длилась тренировка?", reply_markup=get_workout_menu_keyboard())
    await state.set_state(WorkoutStates.waiting_for_duration)
    await add_state_to_history(state, WorkoutStates.waiting_for_duration.state)

@router.message(WorkoutStates.waiting_for_duration)
async def process_duration(message: types.Message, state: FSMContext):
    try:
        duration = int(message.text)
        if duration <= 0:
            await message.answer("⚠️ Длительность должна быть положительным числом.", reply_markup=get_workout_menu_keyboard())
            return
        await state.update_data(duration=duration)
        await message.answer("🔥 Сколько калорий ты сжег во время тренировки? (Можно ввести 0, если неизвестно)", reply_markup=get_workout_menu_keyboard())
        await state.set_state(WorkoutStates.waiting_for_calories_burned)
        await add_state_to_history(state, WorkoutStates.waiting_for_calories_burned.state)
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи длительность числом.", reply_markup=get_workout_menu_keyboard())

@router.message(WorkoutStates.waiting_for_calories_burned)
async def process_calories_burned(message: types.Message, state: FSMContext, bot: Bot):
    try:
        calories_burned = int(message.text)
        if calories_burned < 0:
            await message.answer("⚠️ Количество сожженных калорий должно быть положительным числом или 0.", reply_markup=get_workout_menu_keyboard())
            return
        await state.update_data(calories_burned=calories_burned)
        
        # Спрашиваем тип тренировки (опционально)
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="Кардио", callback_data="workout_type_кардио")],
                [types.InlineKeyboardButton(text="Силовая", callback_data="workout_type_силовая")],
                [types.InlineKeyboardButton(text="Другое", callback_data="workout_type_другое")],
                [types.InlineKeyboardButton(text="Пропустить", callback_data="workout_type_пропустить")],
                [types.InlineKeyboardButton(text="Отмена", callback_data="cancel_workout")] # Кнопка отмены
            ]
        )
        await message.answer("❓ Какой был тип тренировки? (Например: 'Кардио', 'Силовая')", reply_markup=keyboard)
        await state.set_state(WorkoutStates.waiting_for_workout_type)
        await add_state_to_history(state, WorkoutStates.waiting_for_workout_type.state)

    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи количество сожженных калорий числом.", reply_markup=get_workout_menu_keyboard())

# Обработчик для коллбэков типа тренировки
@router.callback_query(F.data.startswith("workout_type_"), WorkoutStates.waiting_for_workout_type)
async def process_workout_type_callback(callback_query: types.CallbackQuery, state: FSMContext):
    workout_type = callback_query.data.split("_")[2] if "пропустить" not in callback_query.data else None
    await state.update_data(workout_type=workout_type)
    
    await callback_query.message.answer("💪 На какую группу мышц была тренировка? (Например: 'Ноги', 'Грудь', 'Все тело'. Или '-' чтобы пропустить)", reply_markup=get_workout_menu_keyboard())
    await state.set_state(WorkoutStates.waiting_for_muscle_group)
    await add_state_to_history(state, WorkoutStates.waiting_for_muscle_group.state)
    await callback_query.answer() # Отвечаем на callback, чтобы убрать индикатор загрузки

@router.message(WorkoutStates.waiting_for_workout_type) # Запасной обработчик для текстового ввода типа тренировки
async def process_workout_type_text_fallback(message: types.Message, state: FSMContext):
    workout_type = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(workout_type=workout_type)
    await message.answer("💪 На какую группу мышц была тренировка? (Например: 'Ноги', 'Грудь', 'Все тело'. Или '-' чтобы пропустить)", reply_markup=get_workout_menu_keyboard())
    await state.set_state(WorkoutStates.waiting_for_muscle_group)
    await add_state_to_history(state, WorkoutStates.waiting_for_muscle_group.state)

@router.message(WorkoutStates.waiting_for_muscle_group)
async def process_muscle_group(message: types.Message, state: FSMContext):
    muscle_group = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(muscle_group=muscle_group)
    await message.answer("🔢 Сколько было подходов? (Введите число, или '-' чтобы пропустить)", reply_markup=get_workout_menu_keyboard())
    await state.set_state(WorkoutStates.waiting_for_sets)
    await add_state_to_history(state, WorkoutStates.waiting_for_sets.state)

@router.message(WorkoutStates.waiting_for_sets)
async def process_sets(message: types.Message, state: FSMContext):
    try:
        sets = int(message.text) if message.text.strip() != '-' else None
        if sets is not None and sets <= 0:
            await message.answer("⚠️ Количество подходов должно быть положительным числом или '-'.", reply_markup=get_workout_menu_keyboard())
            return
        await state.update_data(sets=sets)
        await message.answer("🔄 Сколько было повторений? (Например: '3x10', 'до отказа'. Или '-' чтобы пропустить)", reply_markup=get_workout_menu_keyboard())
        await state.set_state(WorkoutStates.waiting_for_reps)
        await add_state_to_history(state, WorkoutStates.waiting_for_reps.state)
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи количество подходов числом или '-'.", reply_markup=get_workout_menu_keyboard())

@router.message(WorkoutStates.waiting_for_reps)
async def process_reps(message: types.Message, state: FSMContext):
    reps = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(reps=reps)
    await message.answer("🏋️ Какой вес использовался? (Введите число в кг, или '-' чтобы пропустить)", reply_markup=get_workout_menu_keyboard())
    await state.set_state(WorkoutStates.waiting_for_weight_used)
    await add_state_to_history(state, WorkoutStates.waiting_for_weight_used.state)

@router.message(WorkoutStates.waiting_for_weight_used)
async def process_weight_used(message: types.Message, state: FSMContext):
    db = next(get_db())
    try:
        weight_used = float(message.text) if message.text.strip() != '-' else None
        if weight_used is not None and weight_used <= 0:
            await message.answer("⚠️ Использованный вес должен быть положительным числом или '-'.", reply_markup=get_workout_menu_keyboard())
            return
        await state.update_data(weight_used=weight_used)

        user_data = await state.get_data()
        user_id = db.query(User).filter(User.telegram_id == message.from_user.id).first().id

        new_workout = Workout(
            user_id=user_id,
            name=user_data['workout_name'],
            duration=user_data['duration'],
            calories_burned=user_data['calories_burned'],
            workout_type=user_data.get('workout_type'),
            muscle_group=user_data.get('muscle_group'),
            sets=user_data.get('sets'),
            reps=user_data.get('reps'),
            weight_used=user_data.get('weight_used')
        )

        db.add(new_workout)
        db.commit()
        db.refresh(new_workout)
        # Геймификация: очки за тренировку (больше, чем за еду)
        awarded, total_points, streak, streak_changed, _ = register_activity(db, message.from_user.id, 20, "workout_logged")
        if awarded > 0:
            message_text = f"🌟 +{awarded} очков за тренировку. Серия: {streak} дн., всего: {total_points} очков."
            await message.answer(message_text)
            if streak_changed:
                user_for_notification = db.query(User).filter(User.telegram_id == message.from_user.id).first()
                await notify_friends_about_achievement(db, bot, user_for_notification, f"достиг серии активности {streak} дней подряд!")

        db.close()

        await message.answer(f"✅ Добавлена тренировка: {user_data['workout_name']} - {user_data['calories_burned']} ккал сожжено.", reply_markup=get_workout_menu_keyboard())
        await state.clear()
        await clear_state_history(state) # Очищаем историю состояний
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи использованный вес числом или '-'.", reply_markup=get_workout_menu_keyboard())
    except Exception as e:
        await message.answer(f"Произошла ошибка при сохранении: {e}", reply_markup=get_workout_menu_keyboard())
        db.close()
        await state.clear()
        await clear_state_history(state) # Очищаем историю состояний

@router.message(Command("weight"))
async def cmd_weight(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    db.close()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        return

    await message.answer("⚖️ Введи свой текущий вес в килограммах.", reply_markup=get_weight_menu_keyboard())
    await state.set_state(WeightStates.waiting_for_new_weight)
    await add_state_to_history(state, WeightStates.waiting_for_new_weight.state)

@router.message(WeightStates.waiting_for_new_weight)
async def process_new_weight(message: types.Message, state: FSMContext, bot: Bot):
    db = next(get_db())
    try:
        new_weight = float(message.text)
        if not (20 < new_weight < 300):
            await message.answer("⚠️ Пожалуйста, введи корректный вес в килограммах (от 20 до 300).", reply_markup=get_weight_menu_keyboard())
            return
        user_id = db.query(User).filter(User.telegram_id == message.from_user.id).first().id

        new_weight_entry = Weight(
            user_id=user_id,
            weight=new_weight
        )

        # Обновляем текущий вес пользователя
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        user.weight = new_weight
        
        db.add(new_weight_entry)
        db.commit()
        db.refresh(new_weight_entry)
        # Геймификация: очки за запись веса
        awarded, total_points, streak, streak_changed, _ = register_activity(db, message.from_user.id, 5, "weight_logged")
        if awarded > 0:
            message_text = f"🌟 +{awarded} очков за запись веса. Серия: {streak} дн., всего: {total_points} очков."
            await message.answer(message_text)
            if streak_changed:
                user_for_notification = db.query(User).filter(User.telegram_id == message.from_user.id).first()
                await notify_friends_about_achievement(db, bot, user_for_notification, f"достиг серии активности {streak} дней подряд!")

        db.close()

        await message.answer(f"✅ Твой новый вес ({new_weight} кг) сохранен.", reply_markup=get_weight_menu_keyboard())
        await state.clear()
        await clear_state_history(state) # Очищаем историю состояний
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи вес числом.", reply_markup=get_weight_menu_keyboard())
    except Exception as e:
        await message.answer(f"Произошла ошибка при сохранении: {e}", reply_markup=get_weight_menu_keyboard())
        db.close()
        await state.clear()
        await clear_state_history(state) # Очищаем историю состояний

@router.message(Command("progress"))
async def cmd_weight_chart(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        db.close()
        return

    weights_data = db.query(Weight.date, Weight.weight).filter(Weight.user_id == user.id).order_by(Weight.date).all()
    db.close()

    if not weights_data:
        await message.answer("🙁 У тебя пока нет записей о весе. Используй команду /weight, чтобы добавить первый вес.", reply_markup=get_weight_menu_keyboard())
        return

    chart_path = generate_weight_chart(weights_data, user.telegram_id)

    if chart_path:
        await message.answer_photo(FSInputFile(chart_path), caption="📈 Твой прогресс веса:", reply_markup=get_weight_menu_keyboard())
        os.remove(chart_path) # Удаляем файл после отправки
    else:
        await message.answer("⚠️ Не удалось построить график веса.", reply_markup=get_weight_menu_keyboard())
    await add_state_to_history(state, UserStateHistory.history.state) # Добавляем состояние для cmd_weight_chart

@router.message(Command("remind"))
async def cmd_reminder(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    db.close()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        return

    await message.answer("🔔 Что тебе напомнить?", reply_markup=get_cancel_keyboard())
    await state.set_state(ReminderStates.waiting_for_reminder_text)
    await add_state_to_history(state, ReminderStates.waiting_for_reminder_text.state)

@router.message(ReminderStates.waiting_for_reminder_text)
async def process_reminder_text(message: types.Message, state: FSMContext):
    reminder_text = message.text.strip()
    if not reminder_text:
        await message.answer("⚠️ Пожалуйста, введи текст напоминания.", reply_markup=get_main_keyboard())
        return
    await state.update_data(reminder_text=reminder_text)
    await message.answer("⏰ Когда тебе напомнить? Введи дату и время в формате ГГГГ-ММ-ДД ЧЧ:ММ (например, 2025-12-31 18:30)", reply_markup=get_cancel_keyboard())
    await state.set_state(ReminderStates.waiting_for_reminder_time)
    await add_state_to_history(state, ReminderStates.waiting_for_reminder_time.state)

async def send_reminder(bot, chat_id: int, text: str, reminder_id: int, scheduler):
    db = next(get_db())
    try:
        await bot.send_message(chat_id, f"🔔 Напоминание: {text}", reply_markup=get_main_keyboard())
        # Удаляем напоминание из базы данных после отправки
        reminder_to_delete = db.query(Reminder).filter(Reminder.id == reminder_id).first()
        if reminder_to_delete:
            db.delete(reminder_to_delete)
            db.commit()
    except Exception as e:
        print(f"Ошибка при отправке напоминания {reminder_id}: {e}")
    finally:
        db.close()

@router.message(ReminderStates.waiting_for_reminder_time)
async def process_reminder_time(message: types.Message, state: FSMContext, bot, scheduler: AsyncIOScheduler):
    db = next(get_db())
    try:
        reminder_time_str = message.text.strip()
        reminder_time = datetime.strptime(reminder_time_str, '%Y-%m-%d %H:%M')

        if reminder_time <= datetime.utcnow():
            await message.answer("⚠️ Время напоминания должно быть в будущем.", reply_markup=get_main_keyboard())
            return

        user_data = await state.get_data()
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        user_id_db = user.id

        new_reminder = Reminder(
            user_id=user_id_db,
            text=user_data['reminder_text'],
            time=reminder_time,
            job_id=None # Будет обновлено после добавления в планировщик
        )

        db.add(new_reminder)
        db.commit()
        db.refresh(new_reminder)

        # Добавляем задачу в APScheduler
        job_id = scheduler.add_job(
            send_reminder,
            'date',
            run_date=reminder_time,
            args=[bot, message.from_user.id, user_data['reminder_text'], new_reminder.id, scheduler],
            id=f"reminder_{new_reminder.id}"
        ).id

        new_reminder.job_id = job_id
        db.commit()
        db.close()

        await message.answer(f"✅ Напоминание '{user_data['reminder_text']}' установлено на {reminder_time.strftime('%Y-%m-%d %H:%M')}.", reply_markup=get_main_keyboard())
        await state.clear()
        await clear_state_history(state) # Очищаем историю состояний
    except ValueError:
        await message.answer("⚠️ Неверный формат даты/времени. Пожалуйста, используй ГГГГ-ММ-ДД ЧЧ:ММ.", reply_markup=get_main_keyboard())
    except Exception as e:
        await message.answer(f"Произошла ошибка при сохранении напоминания: {e}", reply_markup=get_main_keyboard())
        db.close()
        await state.clear()
        await clear_state_history(state) # Очищаем историю состояний

@router.message(Command("points"))
async def cmd_points(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        db.close()
        return
    await message.answer(f"🌟 Твои очки: <b>{user.points or 0}</b>\nТвоя серия: <b>{user.streak or 0}</b> дней", parse_mode="HTML", reply_markup=get_rating_menu_keyboard())
    await add_state_to_history(state, UserStateHistory.history.state) # Добавляем состояние для cmd_points
    db.close()

@router.message(Command("achievements"))
async def cmd_achievements(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        db.close()
        return

    today = datetime.utcnow().date()
    meals_count = db.query(func.count(Meal.id)).filter(Meal.user_id == user.id).scalar() or 0
    workouts_count = db.query(func.count(Workout.id)).filter(Workout.user_id == user.id).scalar() or 0
    weights_count = db.query(func.count(Weight.id)).filter(Weight.user_id == user.id).scalar() or 0

    # Простые достижения
    achievements = []
    if meals_count >= 1:
        achievements.append("Первый прием пищи записан")
    if meals_count >= 50:
        achievements.append("50 приемов пищи")
    if workouts_count >= 1:
        achievements.append("Первая тренировка")
    if workouts_count >= 20:
        achievements.append("20 тренировок")
    if weights_count >= 5:
        achievements.append("5 записей веса")
    if (user.points or 0) >= 500:
        achievements.append("500 очков")
    if (user.streak or 0) >= 7:
        achievements.append("Серия 7 дней")

    # Новые достижения за серию калорий
    if (user.calorie_streak or 0) >= 1:
        achievements.append("Первый день с выполненной целью по калориям")
    if (user.calorie_streak or 0) >= 3:
        achievements.append("3 дня подряд с выполненной целью по калориям")
    if (user.calorie_streak or 0) >= 7:
        achievements.append("7 дней подряд с выполненной целью по калориям")
    if (user.calorie_streak or 0) >= 14:
        achievements.append("14 дней подряд с выполненной целью по калориям")
    if (user.calorie_streak or 0) >= 30:
        achievements.append("30 дней подряд с выполненной целью по калориям")

    if not achievements:
        achievements_text = "Пока нет достижений. Продолжай!"
    else:
        achievements_text = "\n".join([f"• {a}" for a in achievements])

    text = (
        f"🏆 <b>Достижения</b>\n\n"
        f"Очки: <b>{user.points or 0}</b>\nСерия: <b>{user.streak or 0}</b> дней\n\n"
        f"{achievements_text}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_rating_menu_keyboard())
    await add_state_to_history(state, UserStateHistory.history.state) # Добавляем состояние для cmd_achievements
    db.close()

@router.message(F.text == "📚 Библиотека упражнений")
async def handle_exercise_library_menu(message: types.Message, state: FSMContext):
    db = next(get_db())
    body_parts_raw = db.query(Exercise.body_part_ru).distinct().all()
    db.close()

    if body_parts_raw:
        builder = InlineKeyboardBuilder()
        for part_tuple in body_parts_raw:
            part_name_ru = part_tuple[0]
            builder.button(text=part_name_ru, callback_data=f"select_body_part_{part_name_ru}")
        builder.adjust(2) # Размещаем кнопки по 2 в ряд
        builder.row(types.InlineKeyboardButton(text="Назад к меню тренировок", callback_data="back_to_workout_menu")) # Кнопка "Назад"
        await message.answer("🏋️ Выбери часть тела:", reply_markup=builder.as_markup())
        await state.set_state(ExerciseLibraryStates.waiting_for_body_part_selection)
        await add_state_to_history(state, ExerciseLibraryStates.waiting_for_body_part_selection.state)
    else:
        await message.answer("⚠️ Библиотека упражнений пуста. Загрузите упражнения.", reply_markup=get_workout_menu_keyboard())

@router.callback_query(F.data == "back_to_workout_menu")
async def handle_back_to_workout_menu_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("Возвращаемся в меню тренировок.", reply_markup=None)
    await callback_query.message.answer("💪 Меню тренировок:", reply_markup=get_workout_menu_keyboard())
    await state.clear()
    await clear_state_history(state) # Очищаем историю состояний
    await callback_query.answer()

@router.callback_query(F.data.startswith("select_body_part_"), ExerciseLibraryStates.waiting_for_body_part_selection)
async def handle_body_part_selection(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    body_part_ru = callback_query.data.split("select_body_part_")[1]
    await state.update_data(selected_body_part_ru=body_part_ru, current_page=0)

    db = next(get_db())
    all_exercises = db.query(Exercise).filter(Exercise.body_part_ru == body_part_ru).order_by(Exercise.name_ru).all() # Получаем все упражнения
    db.close()

    if all_exercises:
        await state.update_data(all_exercises=[{"id": e.id, "name_ru": e.name_ru} for e in all_exercises]) # Сохраняем только нужные данные
        await send_paginated_exercises(callback_query.message, state) # Отправляем первую страницу
        await state.set_state(ExerciseLibraryStates.waiting_for_page_selection)
        await add_state_to_history(state, ExerciseLibraryStates.waiting_for_page_selection.state)
    else:
        await callback_query.message.edit_text(f"🙁 Для части тела \'{body_part_ru}\' упражнений не найдено.", reply_markup=None)
        await handle_exercise_library_menu(callback_query.message, state) # Возвращаемся к выбору частей тела

@router.callback_query(F.data == "back_to_body_parts")
async def handle_back_to_body_parts_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("Возвращаемся к выбору части тела.", reply_markup=None)
    await handle_exercise_library_menu(callback_query.message, state) # Возвращаемся к выбору частей тела
    await state.clear()
    await clear_state_history(state) # Очищаем историю состояний
    await callback_query.answer()

EXERCISES_PER_PAGE = 10 # Количество упражнений на странице

async def send_paginated_exercises(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    all_exercises = user_data.get('all_exercises', [])
    current_page = user_data.get('current_page', 0)
    selected_body_part_ru = user_data.get('selected_body_part_ru', 'Неизвестно')

    start_index = current_page * EXERCISES_PER_PAGE
    end_index = start_index + EXERCISES_PER_PAGE
    exercises_to_display = all_exercises[start_index:end_index]

    total_pages = (len(all_exercises) + EXERCISES_PER_PAGE - 1) // EXERCISES_PER_PAGE

    builder = InlineKeyboardBuilder()
    for exercise in exercises_to_display:
        builder.button(text=exercise['name_ru'], callback_data=f"select_exercise_{exercise['id']}")
    builder.adjust(1)

    # Кнопки навигации
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_page"))
    if current_page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data="next_page"))
    
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(types.InlineKeyboardButton(text="Назад к частям тела", callback_data="back_to_body_parts"))

    await message.edit_text( # ИЗМЕНЕНО: Используем edit_text вместо answer
        f"📚 Упражнения для '{selected_body_part_ru}' (Страница {current_page + 1}/{total_pages}):", 
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "prev_page", ExerciseLibraryStates.waiting_for_page_selection)
async def handle_prev_page_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer() # Убираем индикатор загрузки
    user_data = await state.get_data()
    current_page = user_data.get('current_page', 0)
    if current_page > 0:
        await state.update_data(current_page=current_page - 1)
        await send_paginated_exercises(callback_query.message, state) # Отправляем новую страницу с упражнениями
    else:
        await callback_query.message.answer("Вы уже на первой странице.", reply_markup=callback_query.message.reply_markup)

@router.callback_query(F.data == "next_page", ExerciseLibraryStates.waiting_for_page_selection)
async def handle_next_page_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer() # Убираем индикатор загрузки
    user_data = await state.get_data()
    all_exercises = user_data.get('all_exercises', [])
    current_page = user_data.get('current_page', 0)
    total_pages = (len(all_exercises) + EXERCISES_PER_PAGE - 1) // EXERCISES_PER_PAGE
    if current_page < total_pages - 1:
        await state.update_data(current_page=current_page + 1)
        await send_paginated_exercises(callback_query.message, state) # Отправляем новую страницу с упражнениями
    else:
        await callback_query.message.answer("Вы уже на последней странице.", reply_markup=callback_query.message.reply_markup)

@router.callback_query(F.data.startswith("select_exercise_"), ExerciseLibraryStates.waiting_for_page_selection)
async def handle_exercise_selection(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback_query.answer()
    exercise_db_id = int(callback_query.data.split("select_exercise_")[1])

    db = next(get_db())
    exercise = db.query(Exercise).filter(Exercise.id == exercise_db_id).first()
    db.close()

    if exercise:
        primary_muscles_list_ru = json.loads(exercise.primary_muscles_ru) if exercise.primary_muscles_ru else []
        
        caption = (
            f"<b>{exercise.name_ru}</b>\n\n"
            f"<b>Часть тела:</b> {exercise.body_part_ru}\n"
            f"<b>Основные мышцы:</b> {', '.join(primary_muscles_list_ru)}\n"
            f"<b>Сложность:</b> {exercise.difficulty_ru}\n\n"
            f"{exercise.description_ru}"
        )

        media_group = []

        if exercise.start_image_path and os.path.exists(exercise.start_image_path):
            media_group.append(InputMediaPhoto(media=FSInputFile(exercise.start_image_path)))
        
        if exercise.end_image_path and os.path.exists(exercise.end_image_path):
            media_group.append(InputMediaPhoto(media=FSInputFile(exercise.end_image_path)))

        if media_group:
            await callback_query.message.answer_media_group(media=media_group)
        
        # Отправляем текст отдельным сообщением
        await callback_query.message.answer(caption, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardBuilder().add(types.InlineKeyboardButton(text="Назад к упражнениям", callback_data="back_to_exercises_menu")).as_markup())
        await add_state_to_history(state, ExerciseLibraryStates.waiting_for_exercise_selection.state) # Добавляем состояние для выбранного упражнения
    else:
        await callback_query.message.edit_text("⚠️ Упражнение не найдено.", reply_markup=None)
        await send_paginated_exercises(callback_query.message, state) # Возвращаемся к текущей странице упражнений

@router.callback_query(F.data == "back_to_exercises_menu")
async def handle_back_to_exercises_menu_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("Возвращаемся к библиотеке упражнений.", reply_markup=None)
    await send_paginated_exercises(callback_query.message, state) # Возвращаемся к текущей странице упражнений
    await state.set_state(ExerciseLibraryStates.waiting_for_page_selection)
    await add_state_to_history(state, ExerciseLibraryStates.waiting_for_page_selection.state) # Возвращаем предыдущее состояние
    await callback_query.answer()

# --- Функции администратора ---
@router.message(Command("add_points"))
async def cmd_admin_add_points(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У тебя нет прав для выполнения этой команды.", reply_markup=get_main_keyboard())
        return

    await message.answer("Введите Telegram ID пользователя, которому нужно добавить очки: ", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_user_id)
    await add_state_to_history(state, AdminStates.waiting_for_user_id.state)

@router.message(AdminStates.waiting_for_user_id)
async def process_admin_user_id(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У тебя нет прав для выполнения этой команды.", reply_markup=get_main_keyboard())
        return
    try:
        target_user_id = int(message.text)
        db = next(get_db())
        user = db.query(User).filter(User.telegram_id == target_user_id).first()
        db.close()

        if not user:
            await message.answer(f"Пользователь с ID {target_user_id} не найден.", reply_markup=get_main_keyboard())
            await state.clear()
            await clear_state_history(state)
            return

        await state.update_data(target_user_id=target_user_id)
        await message.answer("Введите количество очков для добавления: ", reply_markup=get_cancel_keyboard())
        await state.set_state(AdminStates.waiting_for_points_amount)
        await add_state_to_history(state, AdminStates.waiting_for_points_amount.state)

    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи ID пользователя числом.", reply_markup=get_cancel_keyboard())
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}", reply_markup=get_cancel_keyboard())
        await state.clear()
        await clear_state_history(state)

@router.message(AdminStates.waiting_for_points_amount)
async def process_admin_points_amount(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У тебя нет прав для выполнения этой команды.", reply_markup=get_main_keyboard())
        return
    try:
        points_to_add = int(message.text)
        if points_to_add <= 0:
            await message.answer("⚠️ Количество очков должно быть положительным числом.", reply_markup=get_cancel_keyboard())
            return

        user_data = await state.get_data()
        target_user_id = user_data.get("target_user_id")
        
        if not target_user_id:
            await message.answer("Ошибка: ID пользователя не найден в состоянии.", reply_markup=get_main_keyboard())
            await state.clear()
            await clear_state_history(state)
            return

        db = next(get_db())
        target_user = db.query(User).filter(User.telegram_id == target_user_id).first()

        if target_user:
            awarded, total_points, streak = register_activity(db, target_user_id, points_to_add, "admin_awarded")
            await message.answer(f"✅ {points_to_add} очков успешно добавлено пользователю {target_user_id}. Новое количество очков: {total_points}.", reply_markup=get_main_keyboard())
            db.close()
            await state.clear()
            await clear_state_history(state)
        else:
            await message.answer(f"Пользователь с ID {target_user_id} не найден (во время начисления очков).", reply_markup=get_main_keyboard())
            db.close()
            await state.clear()
            await clear_state_history(state)

    except ValueError:
        await message.answer("⚠️ Пожалуйста, введи количество очков числом.", reply_markup=get_cancel_keyboard())
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}", reply_markup=get_cancel_keyboard())
        await state.clear()
        await clear_state_history(state)

@router.message(F.text == "Назад к рейтингу", LeaderboardStates.waiting_for_leaderboard_type)
async def handle_back_to_rating_menu(message: types.Message, state: FSMContext):
    await message.answer("Возвращаемся в меню рейтинга.", reply_markup=get_rating_menu_keyboard())
    await state.clear()
    await clear_state_history(state)

@router.message(F.text == "Топ по очкам", LeaderboardStates.waiting_for_leaderboard_type)
async def cmd_leaderboard_points(message: types.Message, state: FSMContext):
    db = next(get_db())
    users_by_points = db.query(User).order_by(User.points.desc()).limit(10).all()
    db.close()

    if users_by_points:
        leaderboard_text = "🏆 <b>Топ-10 по очкам:</b>\n\n"
        for i, user in enumerate(users_by_points):
            # Используем имя пользователя из Telegram, если first_name не установлен в базе
            user_name = user.first_name if user.first_name else f"Пользователь {user.telegram_id}"
            leaderboard_text += f"{i+1}. {user_name} - {user.points or 0} очков\n"
    else:
        leaderboard_text = "Пока нет пользователей в таблице лидеров по очкам."

    await message.answer(leaderboard_text, parse_mode="HTML", reply_markup=get_leaderboard_keyboard())
    await add_state_to_history(state, LeaderboardStates.waiting_for_leaderboard_type.state)

@router.message(F.text == "Топ по сериям", LeaderboardStates.waiting_for_leaderboard_type)
async def cmd_leaderboard_streak(message: types.Message, state: FSMContext):
    db = next(get_db())
    users_by_streak = db.query(User).order_by(User.streak.desc()).limit(10).all()
    db.close()

    if users_by_streak:
        leaderboard_text = "🔥 <b>Топ-10 по сериям:</b>\n\n"
        for i, user in enumerate(users_by_streak):
            # Используем имя пользователя из Telegram, если first_name не установлен в базе
            user_name = user.first_name if user.first_name else f"Пользователь {user.telegram_id}"
            leaderboard_text += f"{i+1}. {user_name} - {user.streak or 0} дней\n"
    else:
        leaderboard_text = "Пока нет пользователей в таблице лидеров по сериям."

    await message.answer(leaderboard_text, parse_mode="HTML", reply_markup=get_leaderboard_keyboard())
    await add_state_to_history(state, LeaderboardStates.waiting_for_leaderboard_type.state)

@router.message(F.text == "Назад к меню друзей", FriendStates.waiting_for_friend_id) # Добавлен обработчик для кнопки "Назад к меню друзей"
@router.message(F.text == "Назад к меню друзей", FriendStates.waiting_for_friend_request_action)
async def handle_back_to_friend_menu(message: types.Message, state: FSMContext):
    await message.answer("Возвращаемся в меню друзей.", reply_markup=get_friend_menu_keyboard())
    await state.clear()
    await clear_state_history(state)

@router.message(F.text == "Мои друзья")
async def handle_my_friends_button(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        db.close()
        return

    # Получаем друзей, где текущий пользователь является либо отправителем, либо получателем, и статус 'accepted'
    friends_list = db.query(Friendship).filter(
        ((Friendship.requester_id == user.id) | (Friendship.addressee_id == user.id)),
        Friendship.status == "accepted"
    ).join(User, Friendship.requester_id == User.id).all() # Присоединяем User для получения first_name

    if friends_list:
        friends_text = "🤝 <b>Твои друзья:</b>\n\n"
        for friendship in friends_list:
            friend_user = None
            if friendship.requester_id == user.id: # Текущий пользователь отправил запрос
                friend_user = friendship.addressee
            else: # Текущий пользователь получил запрос
                friend_user = friendship.requester
            
            if friend_user:
                friend_name = friend_user.first_name if friend_user.first_name else (f"@{friend_user.username}" if friend_user.username else f"Пользователь {friend_user.telegram_id}")
                friends_text += f"• {friend_name} (Очки: {friend_user.points or 0}, Серия: {friend_user.streak or 0} дней)\n"
    else:
        friends_text = "У тебя пока нет друзей. Отправь кому-нибудь запрос в друзья!"

    await message.answer(friends_text, parse_mode="HTML", reply_markup=get_friend_menu_keyboard())
    await add_state_to_history(state, UserStateHistory.history.state) # Общее состояние для меню друзей

@router.message(F.text == "Добавить друга")
async def handle_add_friend_button(message: types.Message, state: FSMContext):
    await message.answer("Введите Telegram ID или username друга (например, '123456789' или '@myfriend'): ", reply_markup=get_add_friend_keyboard())
    await state.set_state(FriendStates.waiting_for_friend_id)
    await add_state_to_history(state, FriendStates.waiting_for_friend_id.state)

@router.message(FriendStates.waiting_for_friend_id)
async def process_add_friend_id(message: types.Message, state: FSMContext, bot: Bot):
    db = next(get_db())
    try:
        identifier = message.text.strip()
        requester_user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        addressee_user = None

        if not requester_user:
            await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
            await state.clear()
            await clear_state_history(state)
            return
        
        # Попытка найти пользователя по ID
        try:
            target_telegram_id = int(identifier)
            addressee_user = db.query(User).filter(User.telegram_id == target_telegram_id).first()
        except ValueError:
            # Если не число, пробуем найти по username
            # Удаляем '@' если он есть
            username_to_search = identifier.lstrip('@')
            addressee_user = db.query(User).filter(User.username == username_to_search).first()

        if not addressee_user:
            await message.answer(f"Пользователь с идентификатором '{identifier}' не найден. Убедитесь, что он зарегистрирован в боте и ввел свой username, если вы ищете по нему.", reply_markup=get_add_friend_keyboard())
            return

        if requester_user.id == addressee_user.id:
            await message.answer("Ты не можешь отправить запрос в друзья самому себе.", reply_markup=get_add_friend_keyboard())
            return

        # Проверка на существующий запрос или уже друзей
        existing_friendship = db.query(Friendship).filter(
            ((Friendship.requester_id == requester_user.id) & (Friendship.addressee_id == addressee_user.id)) |
            ((Friendship.requester_id == addressee_user.id) & (Friendship.addressee_id == requester_user.id))
        ).first()

        if existing_friendship:
            if existing_friendship.status == "pending":
                addressee_name = addressee_user.first_name if addressee_user.first_name else addressee_user.username
                await message.answer(f"Запрос в друзья к {addressee_name} уже отправлен и ожидает подтверждения.", reply_markup=get_friend_menu_keyboard())
            elif existing_friendship.status == "accepted":
                addressee_name = addressee_user.first_name if addressee_user.first_name else addressee_user.username
                await message.answer(f"Вы уже друзья с {addressee_name}.", reply_markup=get_friend_menu_keyboard())
            await state.clear()
            await clear_state_history(state)
            return

        new_friendship = Friendship(
            requester_id=requester_user.id,
            addressee_id=addressee_user.id,
            status="pending"
        )
        db.add(new_friendship)
        db.commit()
        db.refresh(new_friendship)

        addressee_name = addressee_user.first_name if addressee_user.first_name else addressee_user.username
        requester_name = requester_user.first_name if requester_user.first_name else requester_user.username
        await message.answer(f"✅ Запрос в друзья успешно отправлен {addressee_name}.", reply_markup=get_friend_menu_keyboard())
        # Уведомить получателя о новом запросе
        await bot.send_message(addressee_user.telegram_id, f"🔔 У вас новый запрос в друзья от {requester_name}!", reply_markup=get_friend_menu_keyboard())

        await state.clear()
        await clear_state_history(state)

    except Exception as e:
        await message.answer(f"Произошла ошибка при отправке запроса: {e}", reply_markup=get_add_friend_keyboard())
    finally:
        db.close()

@router.message(F.text == "Запросы в друзья")
async def handle_friend_requests_button(message: types.Message, state: FSMContext):
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

    if not user:
        await message.answer("Ты еще не зарегистрирован. Используй команду /start для регистрации.", reply_markup=get_main_keyboard())
        db.close()
        return

    pending_requests = db.query(Friendship).filter(
        Friendship.addressee_id == user.id,
        Friendship.status == "pending"
    ).join(User, Friendship.requester_id == User.id).all() # Присоединяем User для получения first_name

    if pending_requests:
        await message.answer("✉️ Входящие запросы в друзья:", reply_markup=get_friend_requests_keyboard(pending_requests))
        await state.set_state(FriendStates.waiting_for_friend_request_action)
        await add_state_to_history(state, FriendStates.waiting_for_friend_request_action.state)
    else:
        await message.answer("У тебя нет новых запросов в друзья.", reply_markup=get_friend_menu_keyboard())
    db.close()

@router.callback_query(F.data.startswith("accept_friend_"), FriendStates.waiting_for_friend_request_action)
async def handle_accept_friend_request(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    db = next(get_db())
    friendship_id = int(callback_query.data.split("_")[2])
    friendship = db.query(Friendship).filter(Friendship.id == friendship_id).first()

    if friendship and friendship.status == "pending":
        friendship.status = "accepted"
        db.commit()
        db.refresh(friendship)
        requester_name = friendship.requester.first_name if friendship.requester.first_name else friendship.requester.username
        addressee_name = friendship.addressee.first_name if friendship.addressee.first_name else friendship.addressee.username
        await callback_query.message.edit_text(f"✅ Запрос от {requester_name} принят!", reply_markup=None)
        await callback_query.message.answer("Возвращаемся в меню друзей.", reply_markup=get_friend_menu_keyboard())
        await bot.send_message(friendship.requester.telegram_id, f"🎉 {addressee_name} принял ваш запрос в друзья!")
    else:
        await callback_query.message.edit_text("⚠️ Запрос уже неактивен или не найден.", reply_markup=None)
        await callback_query.message.answer("Возвращаемся в меню друзей.", reply_markup=get_friend_menu_keyboard())
    
    await state.clear()
    await clear_state_history(state)
    db.close()
    await callback_query.answer()

@router.callback_query(F.data.startswith("reject_friend_"), FriendStates.waiting_for_friend_request_action)
async def handle_reject_friend_request(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    db = next(get_db())
    friendship_id = int(callback_query.data.split("_")[2])
    friendship = db.query(Friendship).filter(Friendship.id == friendship_id).first()

    if friendship and friendship.status == "pending":
        friendship.status = "rejected"
        db.commit()
        db.refresh(friendship)
        requester_name = friendship.requester.first_name if friendship.requester.first_name else friendship.requester.username
        addressee_name = friendship.addressee.first_name if friendship.addressee.first_name else friendship.addressee.username
        await callback_query.message.edit_text(f"❌ Запрос от {requester_name} отклонен.", reply_markup=None)
        await callback_query.message.answer("Возвращаемся в меню друзей.", reply_markup=get_friend_menu_keyboard())
        await bot.send_message(friendship.requester.telegram_id, f"😔 {addressee_name} отклонил ваш запрос в друзья.")
    else:
        await callback_query.message.edit_text("⚠️ Запрос уже неактивен или не найден.", reply_markup=None)
        await callback_query.message.answer("Возвращаемся в меню друзей.", reply_markup=get_friend_menu_keyboard())

    await state.clear()
    await clear_state_history(state)
    db.close()
    await callback_query.answer()
