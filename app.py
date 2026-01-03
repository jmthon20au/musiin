import logging
import asyncio
from telethon import TelegramClient, events, Button

# --- الإعدادات (يجب ملء هذه البيانات من my.telegram.org) ---
API_ID = '24484469'
API_HASH = 'f864ff1bb135fe7faa895d260ce57ba9'
BOT_TOKEN = '7978161922:AAEMIeDCiNUEh1P_lflGoZWEubvZlOZ2ZdQ'

# آيدي المجموعة الثابت
TARGET_GROUP_ID = -1002836920777

# إعداد السجلات
logging.basicConfig(level=logging.INFO)

client = TelegramClient('mention_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# تخزين مؤقت لبيانات الرسالة قيد الإنشاء
user_data = {}

@client.on(events.NewMessage(pattern='/start', func=lambda e: e.is_private))
async def start(event):
    welcome_text = (
        "👋 أهلاً بك في بوت التاكات المطور!\n\n"
        "**المميزات الجديدة:**\n"
        "✅ يمكنك إرسال عدة صور أو ملفات معاً.\n"
        "✅ الإرسال يتم تلقائياً للمجموعة المثبتة.\n"
        "✅ التاكات تظهر أسفل المحتوى المكتوب.\n\n"
        "أرسل الآن المحتوى (نص، صور، ملفات) للبدء:"
    )
    await event.respond(welcome_text, buttons=[Button.inline("بدء إنشاء رسالة 📝", b"start_create")])

@client.on(events.CallbackQuery(data=b"start_create"))
async def start_create(event):
    user_data[event.sender_id] = {
        'text': '', 
        'media_list': [], 
        'buttons': [], 
        'step': 'collecting'
    }
    await event.edit("حسناً، أرسل الآن كل ما تريد (نصوص، صور، فيديوهات، ملفات). يمكنك إرسال أكثر من ملف:")

@client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id in user_data))
async def handle_input(event):
    uid = event.sender_id
    state = user_data[uid].get('step')

    # مرحلة إضافة زر
    if state == 'adding_button':
        try:
            name, url = event.text.split('-', 1)
            user_data[uid]['buttons'].append({'name': name.strip(), 'url': url.strip()})
            user_data[uid]['step'] = 'collecting'
            await event.respond(f"✅ تم إضافة الزر: {name.strip()}", buttons=[
                [Button.inline("إضافة زر آخر 🔗", b"add_btn")],
                [Button.inline("تأكيد الإرسال النهائي ✅", b"confirm_send")]
            ])
        except:
            await event.respond("❌ خطأ في التنسيق. أرسل الزر هكذا:\n`الاسم - الرابط`")
        return

    # مرحلة جمع المحتوى (نصوص ووسائط متعددة)
    if state == 'collecting':
        if event.media:
            user_data[uid]['media_list'].append(event.media)
        
        if event.text and not event.text.startswith('/'):
            # جعل أول سطر غامق إذا كان هناك نص
            if not user_data[uid]['text']:
                lines = event.text.split('\n')
                lines[0] = f"**{lines[0]}**"
                user_data[uid]['text'] = '\n'.join(lines)
            else:
                user_data[uid]['text'] += f"\n{event.text}"

        markup = [
            [Button.inline("إضافة زر شفاف 🔗", b"add_btn")],
            [Button.inline("إرسال للمجموعة الآن 🚀", b"confirm_send")],
            [Button.inline("إلغاء ❌", b"cancel")]
        ]
        
        # رسالة تأكيد استلام القطعة الحالية
        count = len(user_data[uid]['media_list'])
        msg = f"تم استلام المحتوى. (لديك {count} ملفات حالياً).\nيمكنك إرسال المزيد أو الضغط على إرسال."
        await event.respond(msg, buttons=markup)

@client.on(events.CallbackQuery(data=b"add_btn"))
async def ask_button(event):
    uid = event.sender_id
    user_data[uid]['step'] = 'adding_button'
    await event.respond("أرسل بيانات الزر بالشكل التالي:\n`الاسم - الرابط`")

@client.on(events.CallbackQuery(data=b"confirm_send"))
async def final_step(event):
    uid = event.sender_id
    if uid not in user_data: return

    try:
        status_msg = await event.respond("⏳ جاري سحب أعضاء المجموعة وتجهيز التاكات...")
        
        # جلب الأعضاء من الآيدي الثابت
        all_participants = await client.get_participants(TARGET_GROUP_ID)
        
        mentions = ""
        for user in all_participants:
            if user.bot: continue
            name = user.first_name if user.first_name else "مستخدم"
            username = f"@{user.username}" if user.username else "بدون يوزر"
            mentions += f"\n💫 [{name}](tg://user?id={user.id}) ~ {username}"

        user_text = user_data[uid]['text']
        final_text = f"{user_text}\n\n{mentions}"
        
        # تقسيم النص إذا كان طويلاً جداً
        if len(final_text) > 4000:
            final_text = final_text[:3900] + "\n\n...(القائمة طويلة)"

        # تجهيز الأزرار
        msg_buttons = None
        if user_data[uid]['buttons']:
            msg_buttons = [Button.url(b['name'], b['url']) for b in user_data[uid]['buttons']]

        # الإرسال للمجموعة
        # إذا كانت هناك وسائط متعددة، نرسلها كألبوم
        if len(user_data[uid]['media_list']) > 1:
            # نرسل الوسائط أولاً ثم النص مع التاكات في آخر صورة أو كرسالة منفصلة لضمان التنسيق
            await client.send_file(
                TARGET_GROUP_ID,
                user_data[uid]['media_list'],
                caption=final_text,
                buttons=msg_buttons
            )
        else:
            # ملف واحد أو نص فقط
            file = user_data[uid]['media_list'][0] if user_data[uid]['media_list'] else None
            await client.send_message(
                TARGET_GROUP_ID,
                final_text,
                file=file,
                buttons=msg_buttons,
                link_preview=False
            )
        
        await status_msg.edit("✅ تم الإرسال بنجاح إلى المجموعة المثبتة!")
        del user_data[uid]
        
    except Exception as e:
        await event.respond(f"❌ حدث خطأ: {str(e)}")

@client.on(events.CallbackQuery(data=b"cancel"))
async def cancel(event):
    user_data.pop(event.sender_id, None)
    await event.edit("تم إلغاء العملية.")

print("البوت يعمل الآن على الآيدي المثبت...")
client.run_until_disconnected()
