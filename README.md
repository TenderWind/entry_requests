# В проекте использовалось:
* Python 2.7.15rc1
* [Tornado](http://www.tornadoweb.org/en/stable/)
* [Motor](https://motor.readthedocs.io/en/stable/)
* mongoDB

# В описание API:
1. POST /api/v1/registration/
    ```
    {
     "username": <username>,
     "password": <password>
    }
    ```
    Параметры username и password являются обязательными.
    
    Пользователь с таким именем уже зарегистрирован в системе:
    ```
    {"message": "Username <username> already registered in the system"}
    ```
    Пользователь успешно зарегистрирован:
    ```
    {"message": "User successfully registered"}
    ```
1. POST /api/v1/login/
    ```
    {
     "username": <username>,
     "password": <password>
    }
    ```
    Параметры username и password являются обязательными.
    
    Пользователь с таким именем не найден в системе:
    ```
    {"message": "Username not registered in the system"}
    ```
    Неверный пароль:
    ```
    {"message": "Invalid password"}
    ```
    Успешная авторизация. Токен используется для дальнейших операций в системе:
    ```
    {"token": <token>}
    ```
1. POST /api/v1/logout/
    ```
    {
        "token": <token>
    }
    ```
    Параметр token является обязательным.
    
    Токен успешно удален из системы:
    ```
    {"message": ""}
    ```
1. GET /api/v1/<token>/set_manager/ и GET /api/v1/<token>/remove_manager/
    
    Функции заглушка для установки и удаления менеджерских прав пользователю. В случае установки менеджерских 
    прав пользователь получает разрешение на вход.
    Параметр token является обязательным.
    
    Установка прав:
    ```
    {"message": "User <username> is manager"}
    ```
    Удаление прав:
    ```
    {"message": "User <username> is not manager"}
    ```
1. POST /api/v1/send_request/
    ```
    {
        "token": <token>
    }
    ```
    Параметр token является обязательным.
    
    Пользователь уже обладает разрешением на вход:
    ```
    {"message": "User <username> already has permission for entry"}
    ```
    Пользователь уже отправил запрос который не находится в статусе rejected:
    
    ```
    {"message": "User <username> already has submitted request"}
    ```
    Запрос отправлен:
    ```
    {"message": "Request has been sent"}
    ```
1. POST /api/v1/requests/
    ```
    {
        "token": <token>
    }
    ```
    Параметр token является обязательным.
    
    Если пользователь является менеджером.
    
    Заявок нет:
    ```
    {"message": "No requests"}
    ```
        
    Список всех заявок во всех статусах, кроме заявок пользователя:
    ```
    {
        "username": <username>,
        "status": <status>,
        "id": <request_id>
    }{
        "username": <username>,
        "status": <status>,
        "id": <request_id>
    }
    ```
    Если это обычный пользователь.
    
    Заявок нет:
    ```
    {"message": "User <username> does not have any requests"}
    ```   
    Последняя заявка пользователя:
    ```
    {
        "status": <status>,
        "id": <request_id>
    }
    ```
1. POST /api/v1/requests/<request_id>/accept/ и POST /api/v1/requests/<request_id>/reject/
    ```
    {
        "token": <token>
    }
    ```
    Параметры token и request_id являются обязательными.
    
    Пользователь не является менеджером:
    ```
    {"message": "User <username> does not have permission for this action"}
    ```
    Менеджер подтверждает разрешение на вход:
    ```
    {"message": "User {username} has received a entry permit"}
    ```
    Менеджер отклоняет разрешение на вход:
    ```
    {"message": "User {username} application was rejected"}
    ```
