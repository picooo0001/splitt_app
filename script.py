from sqlalchemy import create_engine, Integer, String, ForeignKey, Numeric, Date, insert, select, update, delete, func
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship, aliased, Session
from datetime import datetime
from pyfiglet import Figlet
import sys
from decimal import Decimal
import requests

engine = create_engine('postgresql+psycopg2://admin:password@localhost/split_db')

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    user_id = mapped_column(Integer, primary_key=True)
    username = mapped_column(String, nullable=False)
    amount_balance = mapped_column(Numeric(10,2), default=0)

    expenses_paid = relationship("Expense", back_populates="payer")
    expenses_participated = relationship("ExpenseParticipant", back_populates="participant")

class Expense(Base):
    __tablename__ = 'expense'
    expense_id = mapped_column(Integer, primary_key=True)
    description = mapped_column(String)
    amount = mapped_column(Numeric(10,2))
    currency = mapped_column(String(3))
    date = mapped_column(Date, default=datetime.now)
    payer_id = mapped_column(Integer, ForeignKey('users.user_id'))

    payer = relationship("User", back_populates="expenses_paid")
    participants = relationship("ExpenseParticipant", back_populates="expense")

class ExpenseParticipant(Base):
    __tablename__ = 'expense_participants'
    expense_id = mapped_column(Integer, ForeignKey('expense.expense_id'), primary_key=True)
    participant_id = mapped_column(Integer, ForeignKey('users.user_id'), primary_key=True)
    share = mapped_column(Numeric(10,2))

    expense = relationship("Expense", back_populates="participants")
    participant = relationship("User", back_populates="expenses_participated")


def display_menu(menu):
    """
    Zuständig für das visuelle Zeigen des Menüs.
    Jeder Menüpunkt beinhaltet eine 'Key'- Funktion im Programm.
    :param menu: Ein 'dictionary' bei dem die Nummern die Menüpunkte repräsentieren.
    """
    f = Figlet(font='slant')
    print(f.renderText('WELCOME TO SPLIT'))
    for k, function in menu.items():
        print(k, function.__name__)

def display_users():
    """
    Zeigt alle User und den dazugehörigen Kontostand an.
    Beinhaltet einen verschachtelte Funktion um die Datenbankanfrage auszuführen.
    """
    print("you have selected menu option one") # Simulate function output.
    input("Press Enter to Continue\n")
    def display_users():
        stmt = select(User.username, User.amount_balance)
        with engine.connect() as conn:
            for row in conn.execute(stmt):
                print(f"{row.username}: {row.amount_balance}")
    display_users()
    input("Press Enter to return to the menu.\n")

def get_exchange_rates(from_currency, to_currency='EUR', api_key='6c6d2cb9b773df7c2f9c4ca0'):
    """
    Ruft die aktuellen Wechselraten mit Hilfe einer API ab.

    :param from_currency: Die Währung die konvertiert werden soll.
    :param to_currency: EUR
    :param api_key: API Key mit dem es möglich ist mit der API zu interagieren.
    :return: Der Wechselkurs als 'float'
    """
    url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
    response = requests.get(url)
    data = response.json()
    return data['rates'][to_currency]

def convert_currency(amount, from_currency, to_currency='EUR', api_key='6c6d2cb9b773df7c2f9c4ca0'):
    """
    Rechnet eine bestimmte eingegebene Summe in EUR um, mithilfe der API.

    :param amount: Geldbetrag der 'Expense', welcher umgerechnet werden soll
    :param from_currency: Das Währungskürzel der Währung die in EUR umgerechnet werden soll
    :param to_currency: EUR
    :param api_key: API Key mit dem es möglich ist mit der API zu interagieren.
    :return: Den umgerechneten Betrag in EUR
    """
    if from_currency == to_currency:
        return amount
    rate = get_exchange_rates(from_currency, to_currency, api_key)
    return amount * rate

def create_expense():
    """
    Handling des User Inputs bei einer neuen Ausgabe.
    Rechnet ggfs. den angegebenen Geldbetrag in EUR um und berechnet die Belastung für die einzelnen User anhand des gegebenen Shares.
    Auch das Handling von falschen Inputs wird hier übernommen.

    :param payer_username: Username des Zahlenden
    :param description: BEschreibung / Titel der Ausgabe
    :param amount: Geldbetrag
    :param currency: gegebene Währung
    """
    print("You have selected menu option two")
    input("Press Enter to Continue\n")
    description = input("Description: ")
    amount = float(input("Amount: "))
    currency = input("Currency: ").upper()

    if currency != 'EUR':
        try:
            amount = convert_currency(amount, currency)
            currency = 'EUR'
        except Exception as e:
            print(f"Failed to convert currency: {str(e)}")
            return

    payer_username = input("Payer username: ")
    payer_id = get_user_id_by_username(payer_username)

    if not payer_id:
        print("Payer username not found.")
        return

    while True:
        participants = []
        total_share_percentage = 0.0

        print("Enter each participant's username and their share percentage. Type 'done' when all participants are entered.")

        while True:
            participant_username = input("Enter participant's username (or type 'done' to finish): ")
            if participant_username.lower() == 'done':
                if total_share_percentage == 1.0:
                    break
                else:
                    print("Error: Total shares must sum up to 100%. Current total: {:.0f}%".format(total_share_percentage * 100))
                    reset_choice = input("Do you want to reset the shares and start over? (yes/no): ")
                    if reset_choice.lower() == 'yes':
                        break
                    else:
                        continue
            else:
                participant_id = get_user_id_by_username(participant_username)
                if not participant_id:
                    print("Participant username not found.")
                    continue

                share_percentage = float(input("Enter this participant's share of the expense as a percentage (e.g., 50 for 50%): "))
                share_percentage /= 100
                if total_share_percentage + share_percentage > 1.0:
                    print("Error: Total share cannot exceed 100%.")
                    continue

                total_share_percentage += share_percentage
                participants.append((participant_id, share_percentage * amount))  # Store monetary value directly

        if total_share_percentage == 1.0:
            break  
    process_expense(description, amount, currency, payer_id, participants)


def get_user_id_by_username(username):
    """
    Ruft die User ID für den gegebenen Nutzernamen ab aus der Datenbank.

    :param username: Nutzername
    :return: Die User ID zu dem Nutzernamen
    """
    with engine.connect() as conn:
        stmt = select(User.user_id).where(User.username == username)
        result = conn.execute(stmt).fetchone()
        return result[0] if result else None

def process_expense(description, amount, currency, payer_id, participants):
    """
    Schreibt eine Ausgabe in die Datenbank und aktualisiert die Kontostände der Nutzer.
    Parameter siehe 'create_expense'
    """
    with Session(engine) as session:
        amount = Decimal(amount)
        expense = Expense(description=description, amount=amount, currency=currency, date=datetime.now(), payer_id=payer_id)
        session.add(expense)
        session.flush() 

        for participant_id, share in participants:
            share = Decimal(share)
            expense_participant = ExpenseParticipant(expense_id=expense.expense_id, participant_id=participant_id, share=share)
            session.add(expense_participant)
            participant = session.get(User, participant_id)
            if participant:
                participant.amount_balance -= share

        payer = session.get(User, payer_id)

        if payer:
            payer.amount_balance += amount

        session.commit()
        print("Expense created successfully.")
        input("Press Enter to return to the menu.\n")

def create_user():
    """
    Erstellt einen Nutzer in der Datenbank.
    """
    print("you have selected menu option three")
    input("Press Enter to Continue\n")
    username = input("Type the new username here: ")

    with engine.connect() as conn:
        if username_exists(username):
            print("This username already exist. Please choose another one.")
            input("Press Enter to return to the menu.\n")
            return
        
        if username == "":
            print("Username cant be blank.")
            input("Press Enter to return to the menu.\n")
        else:
            stmt = insert(User).values(username=username)
            conn.execute(stmt)
            conn.commit()
            print("User created sucessfully")
            input("Press Enter to return to the menu.\n")

def username_exists(username):
    """
    Kontrolliert ob der Nutzer bereits existiert in der Datenbank.

    :param username: Username der gecheckt werden soll
    :return: 'True' wenn der Username existiert, ansonsten 'False'
    """
    with engine.connect() as conn:
        stmt = select(User).where(User.username == username)
        result = conn.execute(stmt).fetchone()
        return bool(result)

def show_history():
    """
    Listet alle Ausgaben die in der Datenbank sind auf mitsamt den Details
    """
    print("you have selected menu option four")
    input("Press Enter to Continue\n")

    payer = aliased(User, name="payer")
    participant = aliased(User, name="participant")
    expense_participant = aliased(ExpenseParticipant, name="expense_participant")

    stmt = (
        select(
            Expense.expense_id,
            Expense.description,
            Expense.amount,
            Expense.currency,
            Expense.date,
            payer.username.label("payer_name"),
            participant.username.label("participant_name"),
            expense_participant.share.label("participant_share")
        )
        .join(payer, Expense.payer_id == payer.user_id)
        .join(expense_participant, Expense.expense_id == expense_participant.expense_id)
        .join(participant, expense_participant.participant_id == participant.user_id)
        .order_by(Expense.expense_id, Expense.date)
    )

    with engine.connect() as conn:
        results = conn.execute(stmt)
        current_expense_id = None
        expense_details = ""

        for row in results:
            if current_expense_id != row.expense_id:
                if expense_details:
                    print(expense_details)
                expense_details = (f"Expense ID: {row.expense_id} | Description: {row.description} | "
                                   f"Amount: {row.amount} | Currency: {row.currency} | Date: {row.date} | "
                                   f"Payer: {row.payer_name} | Participants: ")
                current_expense_id = row.expense_id

            expense_details += f"{row.participant_name} (Share: {row.participant_share}), "

        if expense_details:
            print(expense_details.rstrip(", "))

    input("Press Enter to return to the menu.\n")

def financial_summery(username):
    """
    Zeigt eine Zusammenfassung der verscheidenen finanziellen Beziehungen zwischen den verschiedenen Nutzern. Wer schuldet wem was?

    :param username: Der Nutzername, aus dessen Sicht die Zusammenfassung gemacht werden soll. 
    """
    with Session(engine) as session:
        user_id = session.execute(select(User.user_id).where(User.username == username)).scalar()
        if not user_id:
            print("User not found.")
            input("Press Enter to return to the menu.\n")
            return
        print(f"Financial relationships for {username}")

        credits = session.execute(
            select(ExpenseParticipant.participant_id, User.username, func.sum(ExpenseParticipant.share).label('total_due'))
            .join(Expense, Expense.expense_id == ExpenseParticipant.expense_id)
            .join(User, User.user_id == ExpenseParticipant.participant_id)
            .where(Expense.payer_id == user_id, ExpenseParticipant.participant_id != user_id)  # Exclude self-debts
            .group_by(ExpenseParticipant.participant_id, User.username)
        ).all()

        debts = session.execute(
            select(Expense.payer_id, User.username, func.sum(ExpenseParticipant.share).label('total_owe'))
            .join(ExpenseParticipant, Expense.expense_id == ExpenseParticipant.expense_id)
            .join(User, User.user_id == Expense.payer_id)
            .where(ExpenseParticipant.participant_id == user_id, Expense.payer_id != user_id)  # Exclude self-debts
            .group_by(Expense.payer_id, User.username)
        ).all()

        if credits:
            print("\nAmounts owed to user:")
            for credit in credits:
                print(f"{credit.username} owes {username} €{credit.total_due:.2f}")
                input("Press Enter to see more information.\n")
        else:
            print("\nNo one owes money to this user.")
            input("Press Enter to see more information.\n")
        if debts:
            print("\nAmounts user owes to others:")
            for debt in debts:
                print(f"{username} owes {debt.username} €{debt.total_owe:.2f}")
                input("Press Enter to see more information.\n")
        else:
            print("\nUser does not owe money to anyone.")
            input("Press Enter to see more information.\n")
        input("Press Enter to return to the main menu.\n")

def exit():
    """
    Beendet das Programm.
    """
    print("Goodbye")
    sys.exit()

def main():
    """
    Die Hauptfunction, die für das Menü zuständig ist und die verschiedenen Punkte mit den dazugehörigen Funktionen verknüpft.
    """
    functions_names = {
        1: display_users,
        2: create_expense,
        3: create_user,
        4: show_history,
        5: financial_summery,
        6: exit
    }

    while True:
        display_menu(functions_names)
        selection = int(input("Please enter your selection number: "))
        if selection not in functions_names:
            print("Invalid selection, please try again.")
            continue

        if functions_names[selection] == financial_summery:
            username = input("Please enter the username to view financial summary: ")
            functions_names[selection](username)
        else:
            functions_names[selection]() 

if __name__ == "__main__":
    main()