from flask import Flask, jsonify, request, make_response
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime, timedelta
import jwt
import flask_bcrypt



app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://qvqytilckgpibv:e00592735c7339346de40cda68b9bded1ed7b814aef0b09c44f62c250e23bf8f@ec2-54-164-40-66.compute-1.amazonaws.com:5432/dcb77a4fao4kcs'
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'todoaplikace'
app.config['JWT_SECRET'] = 'todoaplikace'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable = False, unique = True)
    pswd = db.Column(db.String(150), nullable = False)
        
    def __init__(self, name, pswd):
        self.name = name
        self.pswd = flask_bcrypt.generate_password_hash(pswd.encode())
        
    def update(self, name, pswd):
        self.name = name
        self.pswd = flask_bcrypt.generate_password_hash(pswd.encode())

    def to_dict(self):
        return{
            "id": self.id,
            "name": self.name,
        }

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    complete = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return make_response(jsonify("Token chybi!"), 401)
        try:
            data = jwt.decode(token, app.config.get("SECRET_KEY"), "HS256")
            current_user = User.query.filter_by(id=data['id']).first()
        except jwt.DecodeError:
            return make_response(jsonify("Neplatny token!"), 403)
        except jwt.ExpiredSignatureError:
            return make_response(jsonify("Expirovany token!"), 401)
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@app.route("/login", methods=["GET"])
def login():
    auth = request.authorization
    

    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    user = User.query.filter_by(name=auth.username).first()

    if not user:
        return make_response('Could not verify - user', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if flask_bcrypt.check_password_hash(user.pswd, auth.password.encode()):
        token = jwt.encode({'id': user.id ,'exp' : datetime.utcnow() + timedelta(minutes=30)}, app.config['SECRET_KEY'], "HS256")
        print("token", token)
        return jsonify({'token' : token})

    return make_response('Could not verify -pass', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})   

"""
@app.route('/user', methods=['POST'])
def create_user():
    data = request.get_json()
        
    new_user = User(name = data['name'], pswd = data['pswd'])
    
    db.session.add(new_user)
    db.session.commit()
    
    return make_response(jsonify("Uzivatel vytvoren."), 200)
"""

@app.route('/user', methods=['GET'])
@token_required
def get_users(current_user):
    
    users = User.query.all()
    
    users = [user.to_dict() for user in users]
    result = {'users': users}
    
    return make_response(jsonify(result))

@app.route('/user/<name>', methods=['GET'])
@token_required
def get_user_by_name(current_user, name=None):
    
    user = get_existing_user(name)
    
    if user:
        return make_response(jsonify(message="Uzivatel nalezen", user = user.to_dict()))

def get_existing_user(name):
    return User.query.filter(User.name == name).first()

@app.route('/todo', methods=['POST'])
@token_required
def create_todo(current_user):
    
    data = request.get_json()
    
    new_todo = Todo(name=data['name'], complete=False, user_id=current_user.id)
    
    db.session.add(new_todo)
    db.session.commit()
    
    return make_response(jsonify("Přidán nový úkol!"), 200)

@app.route('/todo/all', methods=['GET'])
@token_required
def get_all_todos(current_user):
    todos = Todo.query.all()
    
    output = []
    
    for todo in todos:
        todo_data = {}
        todo_data['id'] = todo.id
        todo_data['name'] = todo.name
        todo_data['complete'] = todo.complete
        todo_data['user_id'] = todo.user_id
        output.append(todo_data)
        
    return make_response(jsonify({'todos': output}))

@app.route('/todo/incomplete', methods=['GET'])
@token_required
def get_incomplete_todos(current_user):
    todos = Todo.query.filter_by(complete = False, user_id = current_user.id).all()
    
    output = []
    
    for todo in todos:
        todo_data = {}
        todo_data['id'] = todo.id
        todo_data['name'] = todo.name
        todo_data['complete'] = todo.complete
        todo_data['user_id'] = todo.user_id
        output.append(todo_data)
        
    return make_response(jsonify({'todos': output}))

@app.route('/todo/complete', methods=['GET'])
@token_required
def get_complete_todos(current_user):
    todos = Todo.query.filter_by(complete = True, user_id = current_user.id).all()
    
    output = []
    
    for todo in todos:
        todo_data = {}
        todo_data['id'] = todo.id
        todo_data['name'] = todo.name
        todo_data['complete'] = todo.complete
        todo_data['user_id'] = todo.user_id
        output.append(todo_data)
        
    return make_response(jsonify({'todos': output}))

@app.route('/todo/<id>', methods=['PUT'])
@token_required
def todo_update(current_user, id):
    data = request.get_json()
    
    name = data.get('name', None)
    complete = data.get('complete', None)
    
    todo = Todo.query.filter_by(id=id, user_id=current_user.id).first()
    
    if not todo:
        return make_response(jsonify("Ukol nenalezen."), 404)
    
    todo.name = name
    todo.complete = complete
    todo.user_id = current_user.id
    
    db.session.commit()
    
    return make_response(jsonify("Ukol byl updatovan."), 200)

@app.route('/todo/<id>', methods=['GET'])
@token_required
def get_one_todo(current_user, id):
    todo = Todo.query.filter_by(id=id, user_id=current_user.id).first()
    
    if not todo:
        return make_response(jsonify("Ukol nenalezen"), 404)
    
    result = {}
    result['id'] = todo.id
    result["name"] = todo.name
    result["complete"] = todo.complete
    result["user_id"] = todo.user_id
    
    return make_response(jsonify(result), 200)

@app.route('/todo/<id>', methods=['DELETE'])
@token_required
def delete_todo(current_user, id):
    todo = Todo.query.filter_by(id=id, user_id = current_user.id).first()
    
    if not todo:
        return make_response(jsonify("Ukol neexistuje"), 404)
    
    db.session.delete(todo)
    db.session.commit()
    
    return make_response(jsonify("Ukol ostraněn!", 200))

if __name__ == '__main__':
    app.run(debug=False)