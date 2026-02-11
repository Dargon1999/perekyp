from PyQt6.QtCore import QObject, pyqtSignal

class LocalizationManager(QObject):
    _instance = None
    language_changed = pyqtSignal(str)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalizationManager, cls).__new__(cls)
            cls._instance.init_manager()
        return cls._instance

    def init_manager(self):
        super().__init__()
        self.current_lang = 'ru'
        self.translations = {
            'ru': {
                'feedback_title': 'Обратная связь',
                'feedback_subtitle': 'Мы ценим ваше мнение! Пожалуйста, опишите вашу проблему или предложение.',
                'topic': 'Тема:',
                'message_lbl': 'Сообщение:',
                'topic_bug': 'Баг (Bug)',
                'topic_feature': 'Предложение (Feature)',
                'topic_question': 'Вопрос (Question)',
                'topic_other': 'Другое (Other)',
                'msg_placeholder': 'Опишите ваш отзыв (минимум 10 символов)...',
                'screenshot_btn': '📷 Скриншот',
                'attach_file': 'Прикрепить скриншот',
                'no_file': 'Нет файла',
                'tech_data': 'Прикрепить тех. данные',
                'attach_logs': 'Прикрепить технические данные',
                'tech_data_tooltip': 'Версия ОС, версия приложения, логи (без персональных данных)',
                'send_btn': 'Отправить отзыв',
                'sending': 'Отправка...',
                'success_msg': 'Отзыв успешно отправлен!',
                'err_validation': 'Ошибка валидации данных.',
                'err_rate_limit': 'Слишком много запросов. Попробуйте позже.',
                'err_server': 'Ошибка сервера: {}',
                'err_network': 'Ошибка сети. Проверьте подключение.',
                'err_internal': 'Внутренняя ошибка: {}',
                'err_short': 'Текст отзыва слишком короткий (минимум 10 символов)',
                'err_long': 'Текст отзыва слишком длинный (максимум 1000 символов)',
                'wait_msg': 'Подождите {} сек. перед повторной отправкой',
                
                # Settings Tab
                'tab_main': 'Основные',
                'tab_update': 'Обновление',
                'tab_tabs': 'Управление вкладками',
                'tab_feedback': 'Обратная связь',
                'tab_advanced': 'Дополнительные настройки',

                # Mining Tab
                'harvest.price_comparison_title': 'Стоимость сдачи (100% качество)',
                'harvest.price_comparison_animal': 'Животное',
                'harvest.price_comparison_buyer': 'Цена у скупщика',
                'harvest.price_comparison_rednecks': 'Цена в Rednecks',
                'harvest.price_comparison_rabbit': 'Кролик',
                'harvest.price_comparison_boar': 'Кабан',
                'harvest.price_comparison_deer': 'Олень',
                'harvest.price_comparison_coyote': 'Койот',
                'harvest.price_comparison_cougar': 'Пума',
                'harvest.price_comparison_integrity_info': 'Каждые -10% целостности шкуры снижают её стоимость на 10%.',
                'codes_header': 'Коды доступа',
                'admin_code': 'Код администратора:',
                'admin_code_ph': 'Введите код администратора',
                'extra_code': 'Дополнительный код:',
                'extra_code_ph': 'Введите второй код',
                'err_alphanum': 'Код должен содержать только буквы и цифры.',
                'err_min_len': 'Код слишком короткий (минимум 4 символа).'
            },
            'en': {
                'feedback_title': 'Feedback',
                'feedback_subtitle': 'We value your opinion! Please describe your issue or suggestion.',
                'topic': 'Topic:',
                'message_lbl': 'Message:',
                'topic_bug': 'Bug',
                'topic_feature': 'Feature Request',
                'topic_question': 'Question',
                'topic_other': 'Other',
                'msg_placeholder': 'Describe your feedback (min 10 chars)...',
                'screenshot_btn': '📷 Screenshot',
                'attach_file': 'Attach Screenshot',
                'no_file': 'No file',
                'tech_data': 'Attach tech data',
                'attach_logs': 'Attach technical data',
                'tech_data_tooltip': 'OS version, app version, logs (no PII)',
                'send_btn': 'Send Feedback',
                'sending': 'Sending...',
                'success_msg': 'Feedback sent successfully!',
                'err_validation': 'Validation error.',
                'err_rate_limit': 'Too many requests. Try again later.',
                'err_server': 'Server error: {}',
                'err_network': 'Network error. Check connection.',
                'err_internal': 'Internal error: {}',
                'err_short': 'Text too short (min 10 chars)',
                'err_long': 'Text too long (max 1000 chars)',
                'wait_msg': 'Wait {} sec before retrying',

                # Settings Tab
                'tab_main': 'General',
                'tab_update': 'Update',
                'tab_tabs': 'Tab Management',
                'tab_feedback': 'Feedback',
                'tab_advanced': 'Advanced Settings',
                'codes_header': 'Access Codes',
                'admin_code': 'Admin Code:',
                'admin_code_ph': 'Enter admin code',
                'extra_code': 'Extra Code:',
                'extra_code_ph': 'Enter second code',
                'err_alphanum': 'Code must be alphanumeric.',
                'err_min_len': 'Code too short (min 4 chars).'
            }
        }

    def get(self, key):
        return self.translations.get(self.current_lang, {}).get(key, key)

    def set_language(self, lang):
        if lang in self.translations and lang != self.current_lang:
            self.current_lang = lang
            self.language_changed.emit(lang)
