import numpy as np
from keras.models import Sequential
from keras.layers import Dense, Activation, Dropout
from keras.optimizers import Adam
import random
import os
import nltk
from nltk.stem import WordNetLemmatizer
import json
import pickle

def train():
    try:
        lemmatizer = WordNetLemmatizer()

        model_dir = 'model'
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)

        words = []
        classes = []
        documents = []
        ignore_letters = ['!', '?', ',', '.']
        
        # Check if intents.json exists
        if not os.path.exists('intents.json'):
            raise FileNotFoundError("intents.json file not found")
        
        with open('intents.json', 'r') as file:
            intents = json.load(file)

        # Validate intents structure
        if 'intents' not in intents:
            raise ValueError("Invalid intents.json structure: missing 'intents' key")

        for intent in intents['intents']:
            if 'patterns' not in intent or 'tag' not in intent:
                print(f"Warning: Skipping incomplete intent: {intent}")
                continue
                
            for pattern in intent['patterns']:
                word = nltk.word_tokenize(pattern)
                words.extend(word)
                documents.append((word, intent['tag']))
                if intent['tag'] not in classes:
                    classes.append(intent['tag'])

        words = [lemmatizer.lemmatize(w.lower()) for w in words if w not in ignore_letters]
        words = sorted(list(set(words)))

        classes = sorted(list(set(classes)))

        pickle.dump(words, open(os.path.join(model_dir, 'words.pkl'), 'wb'))
        pickle.dump(classes, open(os.path.join(model_dir, 'classes.pkl'), 'wb'))

        training = []
        output_empty = [0] * len(classes)

        for doc in documents:
            bag = []
            pattern_words = doc[0]
            pattern_words = [lemmatizer.lemmatize(word.lower()) for word in pattern_words]
            for word in words:
                bag.append(1) if word in pattern_words else bag.append(0)

            output_row = list(output_empty)
            output_row[classes.index(doc[1])] = 1

            training.append([bag, output_row])

        random.shuffle(training)
        train_x = np.array([item[0] for item in training])
        train_y = np.array([item[1] for item in training])

        model = Sequential()
        model.add(Dense(128, input_shape=(len(train_x[0]),), activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(64, activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(len(train_y[0]), activation='softmax'))

        optimizer = Adam(learning_rate=0.001)
        model.compile(loss='categorical_crossentropy', optimizer=optimizer, metrics=['accuracy'])

        hist = model.fit(np.array(train_x), np.array(train_y), epochs=200, batch_size=5, verbose=1)
        model.save(os.path.join(model_dir, 'chatbot_brmp_model.h5'))

        print("Model berhasil dilatih ulang!")
        
    except Exception as e:
        print(f"Error during training: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    train()