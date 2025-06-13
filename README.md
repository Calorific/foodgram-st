# Foodgram

«Фудграм» — сайт, на котором пользователи будут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям также будет доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

## Запуск проекта

### Запуск backend части проекта в dev-режиме
1. Клонируйте репозиторий и перейдите в папку проекта
```commandline
git clone https://github.com/Calorific/foodgram-st.git
cd foodgram-st/backend
```
2. Запустите виртуальное окружение
```commandline
python -m venv env
source ./env/bin/activate
```
3. Установите зависимости
```commandline
pip install -r requirements.txt
```
4. Выполните миграции
```commandline
python manage.py migrate
```
5. Создайте главного пользователя
```commandline
python manage.py createsuperuser
```
6. Запустите проект
```commandline
python ..\backend\manage.py runserver
```
В dev-режиме будет использоваться БД Sqlite3

### Запуск backend части проекта в prod-режиме
Для полного запуска потребуется Docker с Docker compose

1. Аналогично нужно клонировать репозиторий
```commandline
git clone https://github.com/Calorific/foodgram-st.git
cd foodgram-st/backend
```
2. В корне проекта нужно создать .env файл
```
DJANGO_SECRET_KEY=секрктный ключ
DB_ENGINE=django.db.backends.postgresql
POSTGRES_DB=foodgram_db
POSTGRES_USER=название пользователя БД
POSTGRES_PASSWORD=пароль пользователя БД
```
3. Запустите сборку контейнеров 
```commandline
cd ./infra
docker compose up -d --build
```
4. Выполните миграции
```commandline
docker compose exec backend python manage.py migrate
```
5. Создайте главного пользователя
```commandline
docker compose exec backend python manage.py createsureruser
```
6. Загрузите изначальные данные
```commandline
docker compose exec backend python manage.py load_ingredients
```
7. Соберите статические файлы
```commandline
docker compose exec backend python3 manage.py collectstatic
docker compose exec backend cp -r static/. /collected_static/static/
```
Теперь проект полностью запущен

## Автор
### [Calorific](https://github.com/Calorific)