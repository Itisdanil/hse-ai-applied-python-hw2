from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import Form
import aiohttp
from config import WEATHER_API_KEY

router = Router()

users = {}


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply(
        "Добро пожаловать! Я ваш бот для расчета калорий и воды.\nВведите /help для списка команд."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "Доступные команды:\n"
        "/set_profile - Настройка профиля 📝\n"
        "/log_water <количество> - Логирование воды 💦\n"
        "/log_food <название продукта> - Логирование еды 🍜\n"
        "/log_workout <тип тренировки> <время (мин)> - Логирование тренировок 💪\n"
        "/check_progress - Проверка прогресса 📊"
    )


@router.message(Command("set_profile"))
async def start_profile_setup(message: Message, state: FSMContext):
    await message.reply("Введите ваш вес (в кг)")
    await state.set_state(Form.weight)


@router.message(Form.weight)
async def process_weight(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users.setdefault(user_id, {})
    users[user_id]["weight"] = int(message.text)
    await message.reply("Введите ваш рост (в см)")
    await state.set_state(Form.height)


@router.message(Form.height)
async def process_height(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id]["height"] = int(message.text)
    await message.reply("Введите ваш возраст")
    await state.set_state(Form.age)


@router.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id]["age"] = int(message.text)
    await message.reply("Сколько минут в день вы активны?")
    await state.set_state(Form.activity_level)


@router.message(Form.activity_level)
async def process_activity_level(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id]["activity"] = int(message.text)
    await message.reply("В каком городе вы находитесь?")
    await state.set_state(Form.city)


@router.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    user_id = message.from_user.id
    users[user_id]["city"] = message.text
    await message.reply("Какова ваша цель по калориям?")
    await state.set_state(Form.calorie_goal)


@router.message(Form.calorie_goal)
async def process_calorie_goal(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        users[user_id]["calorie_goal"] = int(message.text)
        user_data = users[user_id]
        await message.reply(
            f"Профиль настроен:\nВес: {user_data['weight']} кг\n"
            f"Рост: {user_data['height']} см\n"
            f"Возраст: {user_data['age']} лет\n"
            f"Уровень активности: {user_data['activity']} минут\n"
            f"Город: {user_data['city']}\n"
            f"Цель по калориям: {user_data['calorie_goal']}\n"
        )
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите число для цели по калориям.")


@router.message(Command("log_water"))
async def log_water(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await message.reply(
            "Пожалуйста, завершите настройку профиля перед использованием этой команды."
        )
        return

    user_id = message.from_user.id
    if user_id in users:
        try:
            args = message.text.split()
            if len(args) != 2:
                raise ValueError("Не указано количество воды")

            amount = int(args[1])

            weight = users[user_id]["weight"]
            activity = users[user_id]["activity"]
            city = users[user_id]["city"]

            base_water = weight * 30
            additional_water = (activity // 30) * 500

            # Получаем текущую температуру через OpenWeatherMap API
            async with aiohttp.ClientSession() as session:
                weather_response = await session.get(
                    f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
                )
                weather_data = await weather_response.json()

                if weather_data.get("main"):
                    temperature = weather_data["main"]["temp"]
                    if temperature > 25:
                        additional_water += 750

                    total_water_goal = base_water + additional_water
                    users[user_id]["water_goal"] = total_water_goal

                    users[user_id]["logged_water"] = (
                        users[user_id].get("logged_water", 0) + amount
                    )

                    remaining_water = total_water_goal - users[user_id]["logged_water"]

                    await message.reply(
                        f"Вы выпили {amount} мл воды.\n"
                        f"Ваша норма воды на сегодня: {total_water_goal} мл\n"
                        f"Осталось выпить: {remaining_water} мл"
                    )
                else:
                    await message.reply(
                        "Не удалось получить данные о погоде. Пожалуйста, проверьте, правильно ли указан город."
                    )
        except ValueError:
            await message.reply(
                "Пожалуйста, используйте правильный формат команды:\n"
                "/log_water <количество>\n"
                "Например: /log_water 500"
            )
        except Exception as e:
            await message.reply(f"Произошла ошибка: {str(e)}")
    else:
        await message.reply("Сначала настройте профиль с помощью команды /set_profile.")


@router.message(Command("log_food"))
async def log_food(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await message.reply(
            "Пожалуйста, завершите настройку профиля перед использованием этой команды."
        )
        return

    user_id = message.from_user.id
    try:
        command_parts = message.text.split(maxsplit=1)
        if len(command_parts) != 2:
            raise ValueError("Неверный формат команды")

        food_item = command_parts[1]

        # Получаем продукт через OpenFoodFacts API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={food_item}&json=true"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    products = data.get("products", [])
                    if products:
                        first_product = products[0]
                        product_name = first_product.get("product_name", "Неизвестно")
                        calories_per_100g = first_product.get("nutriments", {}).get(
                            "energy-kcal_100g", 0
                        )

                        await message.reply(
                            f"{product_name} — {calories_per_100g} ккал на 100 г. Сколько грамм вы съели?"
                        )

                        users[user_id]["temp_food_data"] = {
                            "product_name": product_name,
                            "calories_per_100g": calories_per_100g,
                        }
                    else:
                        await message.reply(
                            "Простите, я не смог найти информацию о продукте."
                        )
                else:
                    await message.reply(
                        "Произошла ошибка при поиске продукта. Попробуйте позже."
                    )
    except ValueError:
        await message.reply(
            "Пожалуйста, используйте правильный формат команды:\n"
            "/log_food <название продукта>\n"
            "Например: /log_food банан"
        )
    except Exception as e:
        await message.reply(f"Произошла ошибка: {str(e)}")


@router.message(lambda message: message.text.isdigit())
async def process_food_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in users and "temp_food_data" in users[user_id]:
        try:
            amount = int(message.text)
            food_data = users[user_id]["temp_food_data"]

            calories = (food_data["calories_per_100g"] * amount) / 100

            users[user_id]["logged_calories"] = (
                users[user_id].get("logged_calories", 0) + calories
            )

            await message.reply(
                f"Добавлено: {food_data['product_name']}\n"
                f"Количество: {amount} г\n"
                f"Калорий: {calories:.1f}\n"
                f"Всего калорий за сегодня: {users[user_id]['logged_calories']:.1f}"
            )

            del users[user_id]["temp_food_data"]

        except ValueError:
            await message.reply("Пожалуйста, введите корректное число грамм.")


@router.message(Command("log_workout"))
async def log_workout(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await message.reply(
            "Пожалуйста, завершите настройку профиля перед использованием этой команды."
        )
        return

    user_id = message.from_user.id
    try:
        command_parts = message.text.split()
        if len(command_parts) != 3:
            raise ValueError("Неверный формат команды")

        workout_type = command_parts[1]
        duration = int(command_parts[2])

        if user_id in users:
            burned_calories = duration * 10
            users[user_id]["burned_calories"] = (
                users[user_id].get("burned_calories", 0) + burned_calories
            )

            additional_water = (duration // 30) * 200
            users[user_id]["logged_water"] = (
                users[user_id].get("logged_water", 0) + additional_water
            )

            await message.reply(
                f"Тренировка записана:\n"
                f"Тип: {workout_type}\n"
                f"Длительность: {duration} минут\n"
                f"Сожжено калорий: {burned_calories}\n"
                f"Добавлено воды: {additional_water} мл"
            )
        else:
            await message.reply(
                "Сначала настройте профиль с помощью команды /set_profile."
            )
    except ValueError:
        await message.reply(
            "Пожалуйста, используйте правильный формат команды:\n"
            "/log_workout <тип> <время в минутах>\n"
            "Например: /log_workout бег 30"
        )
    except Exception as e:
        await message.reply(f"Произошла ошибка: {str(e)}")


@router.message(Command("check_progress"))
async def check_progress(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await message.reply(
            "Пожалуйста, завершите настройку профиля перед использованием этой команды."
        )
        return

    user_id = message.from_user.id
    if user_id in users:
        user_data = users[user_id]
        await message.reply(
            f"Ваш текущий прогресс:\n"
            f"Вода: {user_data.get('logged_water', 0)} мл из {user_data.get('water_goal', 0)} мл\n"
            f"Калории: {user_data.get('logged_calories', 0)} из {user_data.get('calorie_goal', 0)} калорий\n"
            f"Сожженные калории: {user_data.get('burned_calories', 0)}"
        )
    else:
        await message.reply("Сначала настройте профиль с помощью команды /set_profile.")


def setup_handlers(dp):
    dp.include_router(router)
