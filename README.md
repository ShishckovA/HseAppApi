# Hse App API

Simple python package for authentication and querying students, staff and other things in HSE. 
Copies behaviour of Hse App.

Usage example:

1. Installing dependencies
```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```
2. Using `python3` interpreter, setup credentials
```python
username = "iipetrov@edu.hse.ru"  # Corporate email
password = "p3tr0v_pa$$w0rd"  # Corporate password
client_id = "01234567-89ab-cdef-0123-456789abcdef" # Android app ID
```
3. Create `HseAppApi` instance, setup Bearer token using `HseAppApi.auth()`

```python
from api import HseAppApi

api = HseAppApi(username=username, password=password, client_id=client_id)
api.auth()
```
4. Use methods to execute queries
```python
student = api.search("Шишков Алексей", type_="student", count=1)
print(student[0])
# Output: {'id': 'lk13349', 'full_name': 'Шишков Алексей Алексеевич', ...
```

## ToDo:
1. Support methods for schedule
2. Add manual to find a application `client_id`