from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    waiting_for_type = State()
    waiting_for_question = State()
    waiting_for_personal_data_agreement_question = State()

    waiting_for_name_free = State()
    waiting_for_phone_free = State()
    waiting_for_description_free = State()
    waiting_for_email_free = State()
    waiting_for_tg_account_free = State()
    waiting_for_personal_data_agreement_free = State()

    waiting_for_name_paid = State()
    waiting_for_phone_paid = State()
    waiting_for_description_paid = State()
    waiting_for_email_paid = State()
    waiting_for_tg_account_paid = State()
    waiting_for_paid_agreement = State()
    waiting_for_personal_data_agreement_paid = State()

    waiting_for_publish_answer = State()
