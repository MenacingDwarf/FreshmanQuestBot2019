from pymongo import MongoClient
import telebot
import json
import time
import datetime

MAX_GROUP_STUDENTS = 2
db = MongoClient()['am-cp']

with open('keys.json', 'r') as file:
    token = json.loads(file.read())['bot_token']

bot = telebot.TeleBot(token)


def keyboard(key):
    x = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for j in key:
        x.add(*[telebot.types.KeyboardButton(i) for i in j])
    return x


def log_message(message):
    with open('logs.txt', 'a') as logs:
        line = '[' + str(datetime.datetime.now().time()) + ']' + ' ' + \
              str(message.from_user.first_name) + ' ' + \
              str(message.from_user.last_name) + ' ' + \
              '(' + str(message.from_user.username) + '):' + ' ' + \
              message.text
        logs.write(line+'\n')
        print(line)


def send_message_group(group_number, text):
    group = db['groups'].find_one({'id': group_number})
    users = db['users'].find({'group': group['id']})
    for u in users:
        bot.send_message(u['id'], text)


# Приветственное сообщение
@bot.message_handler(commands=['start'])
def handle_start(message):
    log_message(message)
    is_open = db['settings'].find_one({'name': 'registration'})['open']
    if is_open:
        bot.send_message(message.chat.id, 'Привет, организатор 👋🏻\nДля начала тебе нужно зарегистрироваться. Пиши /reg_org N, где вместо N номер твоей станции. Посмотреть всё станции, чтобы узнать свой номер, ты можешь с помощью команды /free')
    else:
        bot.send_message(message.chat.id, 'Привет, первокурсник 👋🏻\nУже совсем скоро тебе предстоит принять участие в традиционном квесте для первокурсников, и я тебе в этом помогу. Но для начала тебе нужно зарегистрироваться. Пиши /reg_user 1**, где вместо 1** твой номер группы')


# Помощь
@bot.message_handler(commands=['help'])
def handle_help(message):
    user = db['users'].find_one({'id': message.chat.id})
    log_message(message)
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
                                              'После 17:00 бронирование станции станет недоступным, поторопись!\n\n'
                                              'По всем дополнительным вопросам обращаться к @menacing_dwarf')
        else:
            bot.send_message(message.chat.id, 'Ты зарегистрирован, как организатор! Доступные тебе команды:\n'
                                              '/station - информация о твоей станции\n'
                                              '/free - список станций\n'
                                              '/reward N - выставить оценку за прохождение текущей команде (от 1 до 10)\n\n'
                                              'По всем дополнительным вопросам обращаться к @menacing_dwarf')


# Регистрация участника
@bot.message_handler(commands=['reg_user'])
def handler_user(message):
    log_message(message)
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
                    user = {
                        'id': message.chat.id,
                        'username': message.from_user.username,
                        'full_name': message.from_user.first_name + ' ' + message.from_user.last_name,
                        'type': 0,
                        'group': group
                    }
                    db['users'].insert_one(user)

                    keyboards = keyboard([['/info'], ['/free'], ['/help']])
                    bot.send_message(message.chat.id, 'Поздравляю! 🎉\n'
                                                      'Теперь ты зарегистрирован как участник группы ' + str(group) + '!\n'
                                                      'Пиши /help для получения основной информации.',
                                     reply_markup=keyboards)
                else:
                    bot.send_message(message.chat.id, 'Ты уже зарегистрирован, второй раз это делать не нужно 😉')


# Информация о результатах группы
@bot.message_handler(commands=['info'])
def handler_info(message):
    log_message(message)
    user = db['users'].find_one({'id': message.chat.id})
    if not user:
        bot.send_message(message.chat.id, 'Сначала необходимо зарегистрироваться!')
    else:
        group_number = user['group']
        group = db['groups'].find_one({'id': group_number})
        current_station = db['stations'].find_one({'id': group['current_station']})['name'] if group['current_station'] != 0 \
            else 'нет текущей станции'
        bot.send_message(message.chat.id, 'Группа номер ' + str(group_number) +
                         '\n🚩Текущая станция: ' + current_station +
                         '\n💰Деньги: ' + str(group['money']) +
                         '\n✨Опыт: ' + str(group['experience']) +
                         '\n⏫Мультипликатор опыта: ' + str(1 + group['money'] / 100))


# Свободные станции
@bot.message_handler(commands=['free'])
def handler_free(message):
    log_message(message)
    is_started = db['settings'].find_one({'name': 'quest'})['is_started']
    is_ended = db['settings'].find_one({'name': 'quest'})['is_ended']
    is_open = db['settings'].find_one({'name': 'registration'})['open']
    if not is_started and not is_open:
        text = 'Квест ещё не начался, потерпи ещё немножко 😉' if not is_ended else 'Квест уже закончен, можешь отдохнуть 😉'
        bot.send_message(message.chat.id, text)
    else:
        stations = list(db['stations'].find({'group': 0}))
        user = db['users'].find_one({'id': message.chat.id})
        if user:
            if not user['type']:
                group = db['groups'].find_one({'id': user['group']})
                stations = list(filter(lambda station: station['name'] not in group['stations'], stations))
        answer = "\n\n".join([str(station["id"]) + '. ' + station["name"] +
                              '\n📍Расположение: ' + station["geo"] +
                              '\n🎁Награда: ' + str(station["reward"]) for station in stations]) if len(stations) > 0 \
            else "Нет свободных станций"
        bot.send_message(message.chat.id, 'Список свободных станций:\n\n' + answer)


# Взять станцию
@bot.message_handler(commands=['take'])
def handler_take(message):
    user = db['users'].find_one({'id': message.chat.id})
    log_message(message)
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
                        if station['name'] in group['stations']:
                            bot.send_message(message.chat.id, 'Вы уже прошли эту станцию!')
                            return
                        group['current_station'] = station_number
                        db['groups'].replace_one({'id': group['id']}, group)

                        station['group'] = group['id']
                        db['stations'].replace_one({'id': station['id']}, station)

                        bot.send_message(message.chat.id, 'Ваша группа успешно зарегистрирована на станцию \"' +
                                                          station['name'] +
                                                          '\"! Организатор ждёт вас в следующем месте:\n📍' +
                                                          station['geo'])

                        org = db['users'].find_one({'station': station['id']})['id']
                        bot.send_message(org, 'Группа ' + str(group['id']) + ' была зарегистрирована на вашу станцию!')


# Регистрация организатора
@bot.message_handler(commands=['reg_org'])
def handler_reg_org(message):
    log_message(message)
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
                    user = {
                        'id': message.chat.id,
                        'username': str(message.from_user.username),
                        'full_name': str(message.from_user.first_name) + ' ' + str(message.from_user.last_name),
                        'type': 1,
                        'station': station
                    }
                    db['users'].insert_one(user)

                    keyboards = keyboard([['/station'], ['/help']])
                    bot.send_message(message.chat.id, 'Организатор станции \"' + x['name'] + '\" зарегистрирован! Введите /help для получения основной информации.',
                                     reply_markup=keyboards)
                else:
                    bot.send_message(message.chat.id, 'Ты уже зарегистрирован, второй раз это делать не нужно 😉')


# Информация о станции
@bot.message_handler(commands=['station'])
def handler_station(message):
    log_message(message)
    user = db['users'].find_one({'id': message.chat.id})
    if not user:
        bot.send_message(message.chat.id, 'Организатор не зарегистрирован!')
    else:
        if user['type'] != 1:
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
    log_message(message)
    if not user:
        bot.send_message(message.chat.id, 'Организатор не зарегистрирован!')
    else:
        if user['type'] != 1:
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
                    group['stations'].append(station['name'])
                    db['groups'].replace_one({'id': group['id']}, group)

                    station['group'] = 0
                    db['stations'].replace_one({'id': station['id']}, station)

                    bot.send_message(message.chat.id, 'Группе ' + str(group['id']) + ' успешно начисленны баллы!')

                    send_message_group(group['id'], 'Станция \"' + station['name'] + '\" успешно пройдена! 🎉'
                                                    '\nОрганизатор поставил вам ' + str(points) + ' баллов.'
                                                    '\nВам было начисленно ' + str(reward) + ' опыта.'
                                                    '\nВыберите новую станцию из списка свободных.')


# Начисление денег
@bot.message_handler(commands=['pay'])
def handler_pay(message):
    user = db['users'].find_one({'id': message.chat.id})
    log_message(message)
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
    log_message(message)
    if user['type'] == 2:
        try:
            text = ' '.join(message.text.split()[1:])
        except:
            bot.send_message(message.chat.id, 'Неправильный формат!')
        else:
            users = db['users'].find({})
            for u in users:
                bot.send_message(u['id'], text)


# Открыть регистрацию организаторов
@bot.message_handler(commands=['open'])
def handler_open(message):
    log_message(message)
    user = db['users'].find_one({'id': message.chat.id})
    if user['type'] == 2:
        open_settings = db['settings'].find_one({'name': 'registration'})
        open_settings['open'] = True
        db['settings'].replace_one({'name': 'registration'}, open_settings)

        bot.send_message(message.chat.id, 'Регистрация успешно открыта!')


# Закрыть регистрацию организаторов
@bot.message_handler(commands=['close'])
def handler_close(message):
    log_message(message)
    user = db['users'].find_one({'id': message.chat.id})
    if user['type'] == 2:
        open_settings = db['settings'].find_one({'name': 'registration'})
        open_settings['open'] = False
        db['settings'].replace_one({'name': 'registration'}, open_settings)

        bot.send_message(message.chat.id, 'Регистрация успешно закрыта!!')


# Начать квест
@bot.message_handler(commands=['begin'])
def handler_begin(message):
    log_message(message)
    user = db['users'].find_one({'id': message.chat.id})
    if user['type'] == 2:
        quest_settings = db['settings'].find_one({'name': 'quest'})
        quest_settings['is_started'] = True
        quest_settings['is_ended'] = False
        db['settings'].replace_one({'name': 'quest'}, quest_settings)

        bot.send_message(message.chat.id, 'Квест успешно запущен!')

        users = db['users'].find({})
        text = 'Квест только что начался, а значит вы уже можете выбирать станции, выполнять задания и ' \
               'зарабатывать опыт, необходимый для победы!\n' \
               'Поспешите, а то другие группы вас обойдут! 😏'
        for u in users:
            bot.send_message(u['id'], text)


# Закончить квест
@bot.message_handler(commands=['end'])
def handler_end(message):
    user = db['users'].find_one({'id': message.chat.id})
    if user['type'] == 2:
        quest_settings = db['settings'].find_one({'name': 'quest'})
        quest_settings['is_started'] = False
        quest_settings['is_ended'] = True
        db['settings'].replace_one({'name': 'quest'}, quest_settings)

        bot.send_message(message.chat.id, 'Квест успешно закончен!')

        users = db['users'].find({})
        text = 'Наш квест подощёл к концу, заканчивайте выполнение текущей станции и ждите результатов, ' \
               'которые будут объявлены в клубе! Кстати, вы до сих пор можете приобрести билетики на самую отвязную вечеринку нашего факультета, поспешите 😉\n' \
               'А мне пора с вами прощаться и уходить на заслуженный отдых. Было круто проводить с вами время, до новых встреч!!!'
        for u in users:
            bot.send_message(u['id'], text)


# Статистика по всем группам
@bot.message_handler(commands=['stats'])
def handler_stats(message):
    log_message(message)
    user = db['users'].find_one({'id': message.chat.id})
    if user['type'] == 2:
        groups = db['groups'].find({})
        text = 'Рейтинг групп:'
        place = 1
        for group in sorted(groups, key=lambda g: g['experience'], reverse=True):
            text += '\n\n' + str(place) + '. Группа ' + str(group['id']) + \
                    '\nКоличество опыта: ' + str(group['experience']) + \
                    '\nКоличество денег: ' + str(group['money'])
            place += 1

        bot.send_message(message.chat.id, text)
    print('User \"' + message.from_user.username + '\" send message ' + message.text)


# Левое сообщение
@bot.message_handler(content_types=['text'])
def handle_message(message):
    log_message(message)
    bot.send_message(message.chat.id, 'К сожалению, я слишком глупый, чтобы поболтать с тобой 😟')


if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(e)
            time.sleep(5)
