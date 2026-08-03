# Как применить архив

Архив содержит только новые и изменённые файлы относительно ветки `dev`.

1. Переключитесь на `dev` и создайте отдельную ветку:

```bash
git checkout dev
git pull
git checkout -b feature/mvp-completion
```

2. Распакуйте содержимое архива в корень репозитория с заменой файлов.
3. Проверьте изменения:

```bash
git status
git diff
```

4. Создайте `.env`:

```bash
cp .env.example .env
```

Windows:

```cmd
copy .env.example .env
```

5. Запустите:

```bash
docker compose build
docker compose up -d
```

6. Проверьте:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/v1/health
```

7. Запустите smoke-тесты:

```bash
python -m pip install -r requirements-test.txt
pytest
```

8. После проверки сделайте commit:

```bash
git add .
git commit -m "feat: complete trading risk manager MVP"
```
