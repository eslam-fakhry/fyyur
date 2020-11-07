Fyyur
-----

## Development Setup

1. **Initialize and activate a virtualenv using:**
```
python -m virtualenv env
source env/bin/activate
```
>**Note** - In Windows, the `env` does not have a `bin` directory. Therefore, you'd use the analogous command shown below:
```
source env/bin/activate
```

2. **Install the dependencies:**
```
pip install -r requirements.txt
```
3. **Create database:**
```
createdb fyyur_db -U postgres
```

3. **Run migrations**
```
flask db upgrade
```

4. **Run Seeds**
```
python3 seed.py
```

5. **Run the development server:**
```
export FLASK_APP=app
export FLASK_ENV=development # enables debug mode
python3 app.py
```

6. **Verify on the Browser**<br>
Navigate to project homepage [http://127.0.0.1:5000/](http://127.0.0.1:5000/) or [http://localhost:5000](http://localhost:5000) 

