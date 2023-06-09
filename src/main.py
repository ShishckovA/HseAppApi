import os
from api import HseAppApi


def main():
    username = os.getenv("HSE_USERNAME")  # Corporate email, i.e. iipetrov@edu.hse.ru
    password = os.getenv("HSE_PASSWORD")  # Corporate password
    client_id = os.getenv("CLIENT_ID")  # Android app ID
    api = HseAppApi(username=username, password=password, client_id=client_id)
    api.auth()
    student = api.search("Шишков Алексей", type_="student", count=1)
    student_email = student[0]["email"]
    student_extended = api.search_by_email(student_email)
    print(student_extended)


if __name__ == "__main__":
    main()
