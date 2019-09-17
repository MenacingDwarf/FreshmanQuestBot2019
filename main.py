from pymongo import MongoClient
import telebot
import json
import time

MAX_GROUP_STUDENTS = 1
db = MongoClient()['am-cp']

with open('keys.json', 'r') as file:
    token = json.loads(file.read())['bot_token']

bot = telebot.TeleBot(token)


def keyboard(key):
    x = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for j in key:
        x.add(*[telebot.types.KeyboardButton(i) for i in j])
    return x


def send_message_group(group_number, text):
    group = db['groups'].find_one({'id': group_number})
    users = db['users'].find({'group': group['id']})
    for u in users:
        bot.send_message(u['id'], text)


# Приветственное сообщение
@bot.message_handler(commands=['start'])
def handle_start(message):
    is_open = db['settings'].find_one({'name': 'registration'})['open']
    if is_open:
        bot.send_message(message.chat.id, 'Привет, организатор! Для начала тебе нужно зарегистрироваться. Пиши /reg_org N, где вместо N номер твоей станции. Посмотреть всё станции, чтобы узнать свой номер, ты можешь с помощью команды /free')
    else:
        bot.send_message(message.chat.id, 'Привет, первокурсник! Уже совсем скоро тебе предстоит принять участие в традиционном квесте для первокурсников, и я тебе в этом помогу. Но для начала тебе нужно зарегистрироваться. Пиши /reg_user 1**, где вместо 1** твой номер группы')


# Помощь
@bot.message_handler(commands=['help'])
def handle_help(message):
    user = db['users'].find_one({'id': message.chat.id})
    if not user:
        bot.send_message(message.chat.id, 'Сначала необходимо зарегистрироваться!')
    else:
        if not user['type']:
            bot.send_message(message.chat.id, 'Ты зарегистрирован, как участник!\n'
                                              'Задача твоей группы пройти как можно больше станций и заработать как можно больше опыта. '
                                              'Зарабатывать больше опыта тебе помогут деньги, чем больше денег, тем быстрее растёт твой опыт. '
                                              'Деньги можно заработать с помощью специальных заданий до начала квеста. Не надо отправлять мне видео и фото выполненных заданий! '
                                              'Проверять их будет @menacing_dwarf, ему и отправляйте, не забудьте только указать номер своей группы и номер выполненного задания.\n'
                                              'Доступные тебе команды:\n'
                                              '/info - результаты твоей группы\n'
                                              '/free - список свободных станций\n'
                                              '/take N - забронировать станцию для прохождения (N - номер станции)\n\n'
                                              'Порядок твоих действий: выбираешь станцию из свободных, бронируешь эту станцию, бежишь к нужному месту, выполняешь необходимые задания и получаешь награду. '
                                              'После 17:00 бронирование станции станет недоступным, поторопись!')
        else:
            bot.send_message(message.chat.id, 'Ты зарегистрирован, как организатор! Доступные тебе команды:\n'
                                              '/station - информация о твоей станции\n'
                                              '/free - список станций\n'
                                              '/reward N - выставить оценку за прохождение текущей команде (от 1 до 10)')


# Регистрация участника
@bot.message_handler(commands=['reg_user'])
def handler_user(message):
    try:
        group = int(message.text.split()[1])
    except:
        bot.send_message(message.chat.id, 'Неправильный формат!')
    else:
        x = db['groups'].find_one({'id': group})

        if not x:
            bot.send_message(message.chat.id, 'Неправильный номер группы!')
        else:
            if len(list(db['users'].find({'group': group}))) >= MAX_GROUP_STUDENTS:
                bot.send_message(message.chat.id, 'В выбранную группу уже нельзя зарегистрироваться!')
            else:
                user = db['users'].find_one({'id': message.chat.id})
                if not user:
                    user = {'id': message.chat.id, 'type': 0, 'group': group}
                    db['users'].insert_one(user)

                    keyboards = keyboard([['/info'], ['/free'], ['/help']])
                    bot.send_message(message.chat.id, 'Пользователь группы ' + str(group) + ' зарегистрирован! Введите /help для получения основной информации.',
                                     reply_markup=keyboards)
                else:
                    bot.send_message(message.chat.id, 'Ты уже зарегистрирован, второй раз это делать не нужно 😉')


# Информация о результатах группы
@bot.message_handler(commands=['info'])
def handler_info(message):
    user = db['users'].find_one({'id': message.chat.id})
    if not user:
        bot.send_message(message.chat.id, 'Сначала необходимо зарегистрироваться!')
    else:
        group_number = user['group']
        group = db['groups'].find_one({'id': group_number})
        current_station = db['stations'].find_one({'id': group['current_station']})['name'] if group['current_station'] != 0 \
            else 'нет текущей станции'
        bot.send_message(message.chat.id, 'Группа номер ' + str(group_number) +
                         '\nТекущая станция: ' + current_station +
                         '\nДеньги: ' + str(group['money']) +
                         '\nОпыт: ' + str(group['experience']) +
                         '\nМультипликатор опыта: ' + str(1 + group['money'] / 100))


# Свободные станции
@bot.message_handler(commands=['free'])
def handler_free(message):
    is_started = db['settings'].find_one({'name': 'quest'})['is_started']
    is_ended = db['settings'].find_one({'name': 'quest'})['is_ended']
    if not is_started:
        text = 'Квест ещё не начался, потерпи ещё немножко 😉' if not is_ended else 'Квест уже закончен, можешь отдохнуть 😉'
        bot.send_message(message.chat.id, text)
    else:
        stations = list(db['stations'].find({'group': 0}))
        answer = "\n\n".join([str(station["id"]) + '. ' + station["name"] +
                              '\nРасположение: ' + station["geo"] +
                              '\nНаграда: ' + str(station["reward"]) for station in stations])
        bot.send_message(message.chat.id, 'Список свободных станций:\n\n' + answer)


# Взять станцию
@bot.message_handler(commands=['take'])
def handler_take(message):
    user = db['users'].find_one({'id': message.chat.id})
    if not user:
        bot.send_message(message.chat.id, 'Сначала необходимо зарегистрироваться!')
    else:
        is_started = db['settings'].find_one({'name': 'quest'})['is_started']
        is_ended = db['settings'].find_one({'name': 'quest'})['is_ended']
        if not is_started:
            text = 'Квест ещё не начался, потерпи ещё немножко 😉' if not is_ended else 'Квест уже закончен, можешь отдохнуть 😉'
            bot.send_message(message.chat.id, text)
        else:
            group = db['groups'].find_one({'id': user['group']})
            if group['current_station'] != 0:
                bot.send_message(message.chat.id, 'Вы ещё не закончили прохождение предыдущей станции!')
            else:
                try:
                    station_number = int(message.text.split()[1])
                except:
                    bot.send_message(message.chat.id, 'Неправильный формат!')
                else:
                    station = db['stations'].find_one({'id': station_number})
                    if not station:
                        bot.send_message(message.chat.id, 'Неправильный номер станции!')
                    else:
                        group['current_station'] = station_number
                        db['groups'].replace_one({'id': group['id']}, group)

                        station['group'] = group['id']
                        db['stations'].replace_one({'id': station['id']}, station)

                        bot.send_message(message.chat.id, 'Ваша группа успешно зарегистрирована на станцию \"' +
                                                          station['name'] +
                                                          '\"! Организатор ждёт вас в ' + station['geo'])

                        org = db['users'].find_one({'station': station['id']})['id']
                        bot.send_message(org, 'Группа ' + str(group['id']) + ' была зарегистрирована на вашу станцию!')


# Регистрация организатора
@bot.message_handler(commands=['reg_org'])
def handler_reg_org(message):
    is_open = db['settings'].find_one({'name': 'registration'})['open']
    if not is_open:
        bot.send_message(message.chat.id, 'Регистрация организаторов закрыта!')
    else:
        try:
            station = int(message.text.split()[1])
        except:
            bot.send_message(message.chat.id, 'Неправильный формат!')
        else:
            x = db['stations'].find_one({'id': station})

            if not x:
                bot.send_message(message.chat.id, 'Неправильный номер станции!')
            else:
                user = db['users'].find_one({'id': message.chat.id})
                if not user:
                    user = {'id': message.chat.id, 'type': 1, 'station': station}
                    db['users'].insert_one(user)

                    keyboards = keyboard([['/station'], ['/help']])
                    bot.send_message(message.chat.id, 'Организатор станции \"' + x['name'] + '\" зарегистрирован! Введите /help для получения основной информации.',
                                     reply_markup=keyboards)
                else:
                    bot.send_message(message.chat.id, 'Ты уже зарегистрирован, второй раз это делать не нужно 😉')


# Информация о станции
@bot.message_handler(commands=['station'])
def handler_station(message):
    user = db['users'].find_one({'id': message.chat.id})
    if not user:
        bot.send_message(message.chat.id, 'Организатор не зарегистрирован!')
    else:
        if not user['type']:
            bot.send_message(message.chat.id, 'Вы не организатор!')
        else:
            station = db['stations'].find_one({'id': user['station']})
            group = db['groups'].find_one({'current_station': user['station']})
            current_group = str(group['id']) if group else 'пусто'

            bot.send_message(message.chat.id, str(station["id"]) + '. ' + station['name'] +
                                              '\nРасположение: ' + station['geo'] +
                                              '\nТекущая группа: ' + current_group)


# Начислить баллы
@bot.message_handler(commands=['reward'])
def handler_reward(message):
    user = db['users'].find_one({'id': message.chat.id})
    if not user:
        bot.send_message(message.chat.id, 'Организатор не зарегистрирован!')
    else:
        if not user['type']:
            bot.send_message(message.chat.id, 'Вы не организатор!')
        else:
            station = db['stations'].find_one({'id': user['station']})
            group = db['groups'].find_one({'current_station': user['station']})
            if not group:
                bot.send_message(message.chat.id, 'На вашей станции никого нет!')
            else:
                try:
                    points = int(message.text.split()[1])
                    if points < 1 or points > 10:
                        raise Exception
                except:
                    bot.send_message(message.chat.id, 'Неправильный формат!')
                else:
                    reward = station['reward'] * points / 10 * (1 + group['money'] / 100)
                    group['experience'] += reward
                    group['current_station'] = 0
                    db['groups'].replace_one({'id': group['id']}, group)

                    station['group'] = 0
                    db['stations'].replace_one({'id': station['id']}, station)

                    bot.send_message(message.chat.id, 'Группе ' + str(group['id']) + ' успешно начисленны баллы!')

                    send_message_group(group['id'], 'Станция \"' + station['name'] + '\" успешно пройдена! '
                                                    '\nОрганизатор поставил вам ' + str(points) + ' баллов.'
                                                    '\nВам было начисленно ' + str(reward) + ' опыта.'
                                                    '\nВыберите новую станцию из списка свободных.')


# Начисление денег
@bot.message_handler(commands=['pay'])
def handler_pay(message):
    user = db['users'].find_one({'id': message.chat.id})
    if user['type'] == 2:
        try:
            group_number = int(message.text.split()[1])
            amount = int(message.text.split()[2])
        except:
            bot.send_message(message.chat.id, 'Неправильный формат!')
        else:
            group = db['groups'].find_one({'id': group_number})
            group['money'] += amount
            db['groups'].replace_one({'id': group_number}, group)

            bot.send_message(message.chat.id, 'Деньги успешно начилены.')
            send_message_group(group_number, 'Поздравляем! Твоей группе было начислено ' + str(amount) + ' монет! Да вы богаты 💰💰💰')


# Рассылка сообщения
@bot.message_handler(commands=['mailing'])
def handler_mailing(message):
    user = db['users'].find_one({'id': message.chat.id})
    if user['type'] == 2:
        try:
            text = ' '.join(message.text.split()[1:])
        except:
            bot.send_message(message.chat.id, 'Неправильный формат!')
        else:
            users = db['users'].find({})
            for u in users:
                bot.send_message(u['id'], text)


# Начать квест
@bot.message_handler(commands='/begin')
def handler_begin(message):
    user = db['users'].find_one({'id': message.chat.id})
    if user['type'] == 2:
        quest_settings = db['settings'].find_one({'name': 'quest'})
        quest_settings['is_started'] = True
        quest_settings['is_ended'] = False
        db['settings'].replace_one({'name': 'quest'}, quest_settings)

        bot.send_message(message.chat.id, 'Квест успешно запущен!')

        users = db['users'].find({})
        text = 'Квест только что начался, а значит вы уже можете выбирать станции, выполнять задания и зарабатывать опыт, необходимый для победы!'
        for u in users:
            bot.send_message(u['id'], text)


# Закончить квест
@bot.message_handler(commands='/end')
def handler_end(message):
    user = db['users'].find_one({'id': message.chat.id})
    if user['type'] == 2:
        quest_settings = db['settings'].find_one({'name': 'quest'})
        quest_settings['is_started'] = False
        quest_settings['is_ended'] = True
        db['settings'].replace_one({'name': 'quest'}, quest_settings)

        bot.send_message(message.chat.id, 'Квест успешно закончен!')

        users = db['users'].find({})
        text = 'Наш квест подощёл к концу, заканчивайте выполнение текущей станции и ждите результатов, которые будут объявлены в клубе! До новых встреч!!!'
        for u in users:
            bot.send_message(u['id'], text)


if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(e)
            time.sleep(5)
