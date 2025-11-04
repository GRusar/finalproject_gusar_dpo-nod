from datetime import datetime

from hashlib import sha256

class User:
    """Пользователь в системе"""
    _user_id: int # уникальный идентификатор пользователя.
    _username: str # имя пользователя.
    _hashed_password: str # пароль в зашифрованном виде.
    _salt: str # уникальная соль для пользователя.
    _registration_date: datetime # дата регистрации пользователя.

    def __init__(self, user_id: int, username: str, password: str):
        pass

    def get_user_info(self):
        """Выводит информацию о пользователе (без пароля)."""
        pass
    
    def change_password(self, new_password: str):
        """изменяет пароль пользователя, с хешированием нового пароля."""
        pass
    
    def verify_password(self, password: str):
        """проверяет введённый пароль на совпадение."""
        pass
    
    @property
    def user_id(self):
        """Возвращает уникальный идентификатор пользователя."""
        pass

    @property
    def username(self):
        """Возвращает имя пользователя."""
        pass
    @username.setter
    def username(self, new_username: str):
        """Устанавливает новое имя пользователя."""
        pass
    
    
class Wallet:
    """Кошелёк пользователя для одной конкретной валюты"""
    currency_code: str # код валюты (например, "USD", "BTC").
    _balance: float # баланс в данной валюте (по умолчанию 0.0).

    def __init__(self, currency_code: str, initial_balance: float = 0.0):
        pass

    def deposit(self, amount: float):
        """пополнение баланса."""
        # amount положительное число.
        pass
    def withdraw(self, amount: float):
        """ — снятие средств (если баланс позволяет)."""
        #  проверять, что сумма снятия не превышает баланс.
        # amount положительное число.
        pass
    
    def get_balance_info(self):
        """ — вывод информации о текущем балансе.  """
        pass
    
    @property
    def balance(self):
        """Возвращает текущий баланс."""
        pass
    
    @balance.setter
    def balance(self, value: float):
        """Устанавливает новый баланс."""
        #  запрещает отрицательные значения и некорректные типы данных.
        pass

class Portfolio:
    """управление всеми кошельками одного пользователя""" 
    _user_id: int # уникальный идентификатор пользователя.
    _wallets: dict[str, Wallet] # словарь кошельков, где ключ — код валюты, значение — объект Wallet.

    def __init__(self) -> None:
        pass

    def add_currency(self, currency_code: str):
        """добавляет новый кошелёк в портфель (если его ещё нет)."""
        # проверять, что код валюты уникален.
        pass

    def get_total_value(self, base_currency='USD'):
        """возвращает общую стоимость всех валют пользователя в указанной базовой валюте (по курсам, полученным из API или фиктивным данным)."""
        #  конвертирует балансы всех валют в base_currency (для упрощения можно задать фиксированные курсы в словаре exchange_rates).
        pass

    def get_wallet(self, currency_code):
        """возвращает объект Wallet по коду валюты."""
        pass
    
    @property
    def user(self) -> User:
        """геттер, который возвращает объект пользователя (без возможности перезаписи)."""
        return User(1, "", "")
    
    @property
    def wallets(self) -> dict[str, Wallet]:
        """ геттер, который возвращает копию словаря кошельков."""
        return {}
        