import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
CORS(app)

# Load services data
with open('services.json', 'r', encoding='utf-8') as f:
    services = json.load(f)

# Prepare documents for TF-IDF
# We combine name, category and description for better matching
documents = [f"{s['name']} {s['category']} {s['description']}" for s in services]

# Initialize and fit the vectorizer
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(documents)

@app.route('/api/match', methods=['POST'])
def match_services():
    data = request.json
    if not data or 'needs' not in data:
        return jsonify({'error': 'Please provide entrepreneur needs'}), 400
    
    query = data['needs']
    
    # Transform query
    query_vec = vectorizer.transform([query])
    
    # Calculate cosine similarity
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    
    # Sort by score descending
    related_docs_indices = similarities.argsort()[::-1]
    
    results = []
    # Get top 3 or all with score > 0.1
    for i in related_docs_indices:
        score = similarities[i]
        if score > 0.05: # Threshold to filter out completely irrelevant
            service_match = services[i].copy()
            service_match['match_score'] = round(score * 100, 2)
            results.append(service_match)
            
    # If no high matches, just return top 2 as recommendations
    if not results and len(related_docs_indices) >= 2:
         for i in related_docs_indices[:2]:
            service_match = services[i].copy()
            service_match['match_score'] = round(similarities[i] * 100, 2)
            results.append(service_match)

    return jsonify({'matches': results[:3]}) # Return top 3

if __name__ == '__main__':
    app.run(debug=True, port=5000)
