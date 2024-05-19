import spacy
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

# Загрузка английской модели NLP
nlp = spacy.load('en_core_web_sm')

# Набор данных: список текстов
texts = [
    "Could you provide me a transcript for the first year?",
    "I need a transcription of the second semester lectures.",
    "Can I get the third year records?",
    "Please give me the documentation of the first quarter.",
    "Transcript for the second year would be helpful."
]

# Векторизация текста с использованием TF-IDF
vectorizer = TfidfVectorizer(stop_words='english')
X = vectorizer.fit_transform(texts)

# Применение K-means кластеризации
kmeans = KMeans(n_clusters=3, random_state=42)
kmeans.fit(X)

# Вывод результатов кластеризации
clusters = kmeans.labels_
for i, cluster in enumerate(clusters):
    print(f"Текст: '{texts[i]}' принадлежит кластеру {cluster}")
