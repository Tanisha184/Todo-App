import json
from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from bson.objectid import ObjectId
from bson.errors import InvalidId
from bson.json_util import dumps  # Import dumps for proper ObjectId serialization

app = Flask(__name__)

# MongoDB configuration
app.config["MONGO_URI"] = "mongodb+srv://afrin:%40frin184@cluster0.wblq6.mongodb.net/mydb?retryWrites=true&w=majority"
app.config['JWT_SECRET_KEY'] = '63eb933426912b8d4589ff34cff85f7eb61a2fd3f591d0ab07ed0e6533261962'  # Change this to a random secret key

mongo = PyMongo(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)



# Custom JSON encoder
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

app.json_encoder = MongoJSONEncoder


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    mongo.db.users.insert_one({"username": data['username'], "password": hashed_password})
    return jsonify({"msg": "User registered successfully!"}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = mongo.db.users.find_one({"username": data['username']})

    if user and bcrypt.check_password_hash(user['password'], data['password']):
        access_token = create_access_token(identity=str(user['_id']))
        return jsonify(access_token=access_token), 200
    return jsonify({"msg": "Invalid credentials!"}), 401

@app.route('/todos', methods=['GET'])
@jwt_required()
def get_todos():
    current_user_id = get_jwt_identity()
    todos = mongo.db.todos.find({"user_id": ObjectId(current_user_id)})
    
    # Convert todos to a list of dictionaries and serialize ObjectId to string
    todos_list = []
    for todo in todos:
        todo['_id'] = str(todo['_id'])  # Convert ObjectId to string
        todos_list.append(todo)

    return jsonify(todos_list), 200

@app.route('/todos', methods=['POST'])
@jwt_required()
def add_todo():
    data = request.json
    current_user_id = get_jwt_identity()

    if 'text' not in data:
        return jsonify({"error": "Todo must have text."}), 400

    todo = {
        "text": data['text'],
        "user_id": ObjectId(current_user_id)
    }
    
    todo_id = mongo.db.todos.insert_one(todo).inserted_id
    todo['_id'] = str(todo_id)  # Convert ObjectId to string for JSON serialization
    return jsonify(todo), 201

@app.route('/todos/<id>', methods=['DELETE'])
@jwt_required()
def delete_todo(id):
    current_user_id = get_jwt_identity()

    # Log the incoming request for debugging
    print(f"Attempting to delete todo with id: {id} for user: {current_user_id}")

    try:
        todo_id = ObjectId(id)  # Validate ObjectId here
        result = mongo.db.todos.delete_one({'_id': todo_id, 'user_id': ObjectId(current_user_id)})

        if result.deleted_count == 0:
            return jsonify({"msg": "Todo not found or not owned by user."}), 404
        
        return jsonify({"msg": "Deleted"}), 200

    except InvalidId:
        return jsonify({"msg": "Invalid todo ID."}), 400  # Return a 400 for invalid ID
    except Exception as e:
        # Log the error message
        print(f"Error occurred while deleting todo: {str(e)}")
        return jsonify({"msg": "An error occurred while deleting the todo."}), 500
def convert_object_ids_to_strings(document):
    if isinstance(document, dict):
        return {k: (str(v) if isinstance(v, ObjectId) else convert_object_ids_to_strings(v)) for k, v in document.items()}
    elif isinstance(document, list):
        return [convert_object_ids_to_strings(item) for item in document]
    return document

if __name__ == "__main__":
    app.run(debug=True)
