from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram.ext import MessageHandler, Filters, CallbackContext
from config import ADMIN_IDS, BOT_TOKEN
from datetime import datetime, timedelta
from rou_models import Pickup, PickupStatus
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)
from peewee import *

updater = Updater(BOT_TOKEN, use_context=True)
job_queue = updater.job_queue
dispatcher = updater.dispatcher
PAGE_SIZE = 3

AD1BUTTON = InlineKeyboardButton('发车说明', url='https://t.me/hezu1/1175909')
AD2BUTTON = InlineKeyboardButton('@hezu1 🤝 奈飞Pro',
                                 url='https://naifei.pro/m/?rid=v02h2&utm_source=tg&utm_medium=rou_bot')

# key format: chat_id:chat_type

chat_id_message_time_dic = {

}

chat_id_message_dic = {

}


def delete_message(context: CallbackContext):
    message_data = context.job.context
    context.bot.delete_message(chat_id=message_data.chat_id, message_id=message_data.message_id)


def get_key_by_chat_id_type(chat_id, pickup_type):
    return str(chat_id) + ':' + pickup_type


def get_list_callback(pickup_type, page_num, list_all):
    return 'list:' + str(pickup_type) + ':' + str(page_num) + ':' + str(int(list_all))


def get_my_callback(driver_id, page_num):
    return 'my:' + str(driver_id) + ':' + str(page_num)


def get_list_reply_markup_by_page(pickup_type, page_num, total_pages, list_all):
    if page_num == 1:
        if total_pages == 1 or total_pages == 0:
            btns = [[AD1BUTTON, AD2BUTTON]]
        else:
            btns = [[AD1BUTTON,
                     InlineKeyboardButton('➡️下一页', callback_data=get_list_callback(pickup_type, 2, list_all))]]
    else:
        if page_num == total_pages:
            btns = [
                [InlineKeyboardButton('⬅️上一页', callback_data=get_list_callback(pickup_type, page_num - 1, list_all)),
                 AD2BUTTON]]
        else:
            btns = [
                [InlineKeyboardButton('⬅️上一页', callback_data=get_list_callback(pickup_type, page_num - 1, list_all)),
                 InlineKeyboardButton('➡️下一页', callback_data=get_list_callback(pickup_type, page_num + 1, list_all))]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=btns)
    return reply_markup


def get_driver_reply_markup_by_page(driver_id, page_num, total_pages):
    if page_num == 1:
        if total_pages == 1 or total_pages == 0:
            btns = [[AD2BUTTON]]
        else:
            btns = [[AD2BUTTON,
                     InlineKeyboardButton('➡️下一页', callback_data=get_my_callback(driver_id, 2))]]
    else:
        if page_num == total_pages:
            btns = [[InlineKeyboardButton('⬅️上一页', callback_data=get_my_callback(driver_id, page_num - 1)),
                     AD2BUTTON]]
        else:
            btns = [[InlineKeyboardButton('⬅️上一页', callback_data=get_my_callback(driver_id, page_num - 1)),
                     InlineKeyboardButton('➡️下一页', callback_data=get_my_callback(driver_id, page_num + 1))]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=btns)
    return reply_markup


def get_list_total_pages(pickup_str, list_all):
    week_ago = datetime.today() - timedelta(days=7)
    if pickup_str == 'all':
        if list_all:
            count = Pickup.select().where(Pickup.post_date >= week_ago).count()
        else:
            count = Pickup.select().where(
                (Pickup.status == PickupStatus.default) & (Pickup.post_date >= week_ago)).count()  # 所有类型
    else:
        pickup_str = pickup_str.lower()
        start_str = '#' + pickup_str
        if list_all:
            count = Pickup.select().where(
                (fn.Lower(Pickup.message).startswith(start_str)) & (Pickup.post_date >= week_ago)).count()
        else:
            count = Pickup.select().where((fn.Lower(Pickup.message).startswith(start_str)) &
                                          (Pickup.status == PickupStatus.default) & (
                                                  Pickup.post_date >= week_ago)).count()
    total_page = (count + PAGE_SIZE - 1) / PAGE_SIZE
    total_page = int(total_page)
    return total_page


def get_driver_total_pages(driver_id):
    count = Pickup.select().where(Pickup.poster == driver_id).count()
    total_page = (count + PAGE_SIZE - 1) / PAGE_SIZE
    total_page = int(total_page)
    return total_page


def handle_list_callback(update, context):
    data = update.callback_query.data
    query = update.callback_query
    _, pickup_type, page_num, list_all = data.split(':')
    pickup_type, page_num, list_all = pickup_type, int(page_num), bool(int(list_all))
    pickup_type = pickup_type.lower()
    total_pages = get_list_total_pages(pickup_type, list_all)
    text = get_text_by_type_page(pickup_type, page_num, total_pages, list_all)
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    reply_markup = get_list_reply_markup_by_page(pickup_type, page_num, total_pages, list_all)
    query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="MarkdownV2")


def handle_driver_callback(update, context):
    data = update.callback_query.data
    query = update.callback_query
    _, driver_id, page_num = data.split(':')
    driver_id, page_num = int(driver_id), int(page_num)
    total_pages = get_driver_total_pages(driver_id)
    text = get_text_by_driver_page(driver_id, page_num, total_pages)
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    reply_markup = get_driver_reply_markup_by_page(driver_id, page_num, total_pages)
    query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="MarkdownV2")


def get_text_by_type_page(pickup_type, page, total_pages, list_all):
    if total_pages == 0:
        return '无相关合租信息或车辆均已满，您可以查看置顶尝试发车'
    all_str = '第' + str(page) + '页/共' + str(total_pages) + '页\n\n'
    week_ago = datetime.today() - timedelta(days=7)
    if pickup_type == 'all':
        if list_all:
            pickups = Pickup.select().where(Pickup.post_date >= week_ago).order_by(
                Pickup.id.desc()).paginate(page, PAGE_SIZE)
        else:
            pickups = Pickup.select().where((Pickup.status == PickupStatus.default) & (
                    Pickup.post_date >= week_ago)).order_by(
                Pickup.id.desc()).paginate(page, PAGE_SIZE)

    else:
        start_str = '#' + pickup_type
        if list_all:
            pickups = Pickup.select().where(
                (fn.Lower(Pickup.message).startswith(start_str)) & (Pickup.post_date >= week_ago)).order_by(
                Pickup.id.desc()).paginate(page, PAGE_SIZE)
        else:
            pickups = Pickup.select().where((fn.Lower(Pickup.message).startswith(start_str)) &
                                            (Pickup.status == PickupStatus.default) & (
                                                    Pickup.post_date >= week_ago)).order_by(
                Pickup.id.desc()).paginate(page, PAGE_SIZE)
    for pickup in pickups:
        all_str = all_str + 'ID:' + str(pickup.id) + ' '
        status_text = '未满🟢 \\(车主私聊机器人改状态\\)' if pickup.status == PickupStatus.default else '已满⛔️'
        all_str = all_str + status_text + '\n'
        all_str = all_str + get_message_markdown_text(pickup)
        all_str = all_str + '\n\n'
    return all_str


def get_text_by_driver_page(driver_id, page, total_pages):
    if total_pages == 0:
        return '无相关合租信息'
    all_str = '第' + str(page) + '页/共' + str(total_pages) + '页\n\n'
    pickups = Pickup.select().where(Pickup.poster == driver_id).order_by(Pickup.id.desc()).paginate(page, PAGE_SIZE)
    for pickup in pickups:
        all_str = all_str + 'ID:' + str(pickup.id) + ' '
        status_text = '未满🟢 \\(车主私聊机器人改状态\\)' if pickup.status == PickupStatus.default else '已满⛔️'
        all_str = all_str + status_text + '\n'
        all_str = all_str + get_message_markdown_text(pickup)
        all_str = all_str + '\n\n'
    return all_str


# 要支持大小写
# 要尽量匹配所有内容
#


def list_command(update, context):
    # list_all = len(context.args) == 2 and context.args[1] == 'all'
    list_all = True
    pickup_type = 'all' if len(context.args) == 0 else context.args[0]
    pickup_type = pickup_type.lower()
    message_key = get_key_by_chat_id_type(update.effective_chat.id, pickup_type)
    now = datetime.now()
    last_message_time = chat_id_message_time_dic.get(message_key)
    if last_message_time:
        delta = now - last_message_time
        if delta.seconds <= 1200: # 20分钟
            last_message_link = chat_id_message_dic.get(message_key)
            btns = [[InlineKeyboardButton('点击查看', url=last_message_link)]]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=btns)
            message = context.bot.send_message(chat_id=update.effective_chat.id, text='近20分钟内已有相关查询，点击查看，本消息10秒后销毁',
                                     parse_mode="MarkdownV2",
                                     reply_markup=reply_markup)
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            context.job_queue.run_once(delete_message, 10, context=message)
            return
    total_pages = get_list_total_pages(pickup_type, list_all)
    all_str = get_text_by_type_page(pickup_type, 1, total_pages, list_all)
    if all_str:
        reply_markup = get_list_reply_markup_by_page(pickup_type, 1, total_pages, list_all)
        message = context.bot.send_message(chat_id=update.effective_chat.id, text=all_str, parse_mode="MarkdownV2",
                                           reply_markup=reply_markup)
        chat_id_message_time_dic[message_key] = now
        chat_id_message_dic[message_key] = message.link
    else:
        message = context.bot.send_message(chat_id=update.effective_chat.id, text='🈚️ 没有找到相关车辆或已过期，快来发车',
                                           parse_mode="Markdown")
        chat_id_message_time_dic[message_key] = now
        chat_id_message_dic[message_key] = message.link


def get_message_markdown_text(pickup):
    message = pickup.message
    escape_symobls = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for symbol in escape_symobls:
        if symbol in message:
            message = message.replace(symbol, '\\' + symbol)

    if not pickup.poster:
        return message

    split_res = message.rsplit('@', 1)
    if len(split_res) == 1:
        # 没有at, 手动加上
        message = message + ' [联系车主](tg://user?id=' + pickup.poster + ')'
        return message
    else:
        # 把后面的替换掉
        joined_front = ''.join(split_res[:-1])
        return joined_front + '[@' + split_res[-1] + '](tg://user?id=' + pickup.poster + ')'


def help_command(update, context):
    from_user_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    if from_user_id != chat_id:
        return
    context.bot.send_message(chat_id=update.effective_chat.id, text='''合租机器人beta

当前支持的命令列表:

\- `/cx` 查询 @hezu2 频道近一周的审核车，默认只显示未满车辆
\- `/cx pattern` 查询某一类型的审核车，如`/cx netflix`

 车主标记已满步骤：
第一步：\- `/my` 查询我发布的所有车辆，记住ID号！
第二步：\- `/mark ID号 1`
将某一个ID的车辆状态改变，其中0为未满 1为已满。
此命令仅限车主使用。

\- `/help` 帮助
    ''', parse_mode="MarkdownV2")


def my_command(update, context):
    from_user_id = update.message.from_user.id
    total_pages = get_driver_total_pages(from_user_id)
    all_str = get_text_by_driver_page(from_user_id, 1, total_pages)
    if all_str:
        reply_markup = get_driver_reply_markup_by_page(from_user_id, 1, total_pages)
        context.bot.send_message(chat_id=update.effective_chat.id, text=all_str, parse_mode="MarkdownV2",
                                 reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='🈚️ 无相关合租信息或车辆均已满，您可以查看置顶尝试发车',
                                 parse_mode="Markdown")


def mark_command(update, context):
    if len(context.args) < 2:
        return
    from_user_id = update.message.from_user.id
    pickup_id = int(context.args[0])
    pickup_status = int(context.args[1])
    p = Pickup.select().where(Pickup.id == pickup_id).first()
    if not p:
        return
    if (from_user_id not in ADMIN_IDS) and (from_user_id != int(p.poster)):
        context.bot.send_message(chat_id=update.effective_chat.id, text='只有管理员和车主能编辑此车状态', parse_mode="Markdown")
        return
    if pickup_status > 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text='状态代码错误', parse_mode="Markdown")
    if p:
        p.status = pickup_status
        p.save()
        context.bot.send_message(chat_id=update.effective_chat.id, text='本辆车状态已更新', parse_mode="Markdown")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='未找到，请检查ID', parse_mode="Markdown")


def error_callback(update, context):
    try:
        raise context.error
    except Unauthorized:
        print(context.error)
        # remove update.message.chat_id from conversation list
    except BadRequest:
        print(context.error)
        # handle malformed requests - read more below!
    except TimedOut:
        print(context.error)
        # handle slow connection problems
    except NetworkError:
        print(context.error)
        # handle other connection problems
    except ChatMigrated as e:
        print(context.error)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        print(context.error)
        # handle all other telegram related errors


list_handler = CommandHandler('cx', list_command)
dispatcher.add_handler(list_handler)
my_handler = CommandHandler('my', my_command)
dispatcher.add_handler(my_handler)
mark_handler = CommandHandler('mark', mark_command)
dispatcher.add_handler(mark_handler)
help_handler = CommandHandler('help', help_command)
dispatcher.add_handler(help_handler)
callback_query_handler = CallbackQueryHandler(handle_list_callback, pattern='^list:')
dispatcher.add_handler(callback_query_handler)
my_callback_query_handler = CallbackQueryHandler(handle_driver_callback, pattern='^my:')
dispatcher.add_handler(my_callback_query_handler)
dispatcher.add_error_handler(error_callback)
updater.start_polling()
