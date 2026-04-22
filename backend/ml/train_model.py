import pickle
import sys
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import LabelEncoder

BASE_DIR = Path(__file__).resolve().parent
# Add the backend folder to system path so we can import 'apps'
sys.path.append(str(BASE_DIR.parent))

from apps.chatbot.nlp_utils import preprocess_text


DATA_PATH = BASE_DIR / "sample_symptoms.csv"
MODEL_PATH = BASE_DIR / "model.pkl"
VECTORIZER_PATH = BASE_DIR / "vectorizer.pkl"
LABEL_ENCODER_PATH = BASE_DIR / "label_encoder.pkl"


def train_and_save_model():
    df = pd.read_csv(DATA_PATH)

    if {"symptom", "disease"} - set(df.columns):
        raise ValueError("CSV must include 'symptom' and 'disease' columns")

    df = df.dropna()
    df["clean_text"] = df["symptom"].astype(str).map(preprocess_text)

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    x = vectorizer.fit_transform(df["clean_text"])

    encoder = LabelEncoder()
    y = encoder.fit_transform(df["disease"])

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    model = MultinomialNB()
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    print(classification_report(y_test, predictions, target_names=encoder.classes_))

    with open(MODEL_PATH, "wb") as model_file:
        pickle.dump(model, model_file)

    with open(VECTORIZER_PATH, "wb") as vec_file:
        pickle.dump(vectorizer, vec_file)

    with open(LABEL_ENCODER_PATH, "wb") as enc_file:
        pickle.dump(encoder, enc_file)

    print(f"Saved model to: {MODEL_PATH}")
    print(f"Saved vectorizer to: {VECTORIZER_PATH}")
    print(f"Saved label encoder to: {LABEL_ENCODER_PATH}")


if __name__ == "__main__":
    train_and_save_model()
