from flask import Flask, render_template, request, jsonify, session
import nltk
nltk.download("punkt_tab")
nltk.download("wordnet")
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
import pickle
import numpy as np
from tensorflow import keras
import json
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = '25082025-chtbtbrmppnrpn-rfldmr'

model = keras.models.load_model('model/chatbot_brmp_model.h5')
intents = json.loads(open('intents.json').read())
words = pickle.load(open('model/words.pkl','rb'))
classes = pickle.load(open('model/classes.pkl','rb'))

def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

def bag_of_words(sentence, words):
    sentence_words = clean_up_sentence(sentence)
    bag = np.zeros(len(words), dtype=np.float32)
    for sw in sentence_words:
        for i, word in enumerate(words):
            if word == sw:
                bag[i] = 1
    return bag

def predict_class(sentence):
    p = bag_of_words(sentence, words)
    res = model.predict(np.expand_dims(p, axis=0))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i,r] for i,r in enumerate(res) if r>ERROR_THRESHOLD]
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def getResponse(ints, intents_json):
    if not ints:
        return "Maaf, aku tidak mengerti."
    tag = classes[ints[0][0]]
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if i['tag'] == tag:
            result = random.choice(i['responses'])
            return result
    return "Maaf, aku tidak menemukan jawaban untuk itu."

@app.route('/')
def index():
    if 'messages' not in session:
        session['messages'] = [{"role": "assistant", "content": "Hai! Ada yang bisa aku bantu hari ini?"}]
    return render_template('index.html', title='Chatbot BRMP', now=datetime.now())

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json()
    prompt = data.get('message', '')
    
    if 'messages' not in session:
        session['messages'] = []
    
    session['messages'].append({"role": "user", "content": prompt})
    
    ints = predict_class(prompt)
    response = getResponse(ints, intents)
    
    session['messages'].append({"role": "assistant", "content": response})
    
    session.modified = True
    
    return jsonify({
        'response': response,
        'messages': session['messages']
    })

@app.route('/api/reset', methods=['POST'])
def reset_chat():
    session['messages'] = [{"role": "assistant", "content": "Hai! Ada yang bisa aku bantu hari ini?"}]
    session.modified = True
    return jsonify({'status': 'success', 'messages': session['messages']})

@app.route('/api/messages', methods=['GET'])
def get_messages():
    if 'messages' not in session:
        session['messages'] = [{"role": "assistant", "content": "Hai! Ada yang bisa aku bantu hari ini?"}]
    return jsonify({'messages': session['messages']})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)