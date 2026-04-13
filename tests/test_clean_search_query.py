import spacy
from backend.agents.finalization_agent import clean_search_query
nlp = spacy.load("en_core_web_sm")

diagnoses = [
    "Mucinous neoplasm of the pancreas",
    "Secondary pancreatitis",
    "Bile duct stricture",
    "Insulin-dependent diabetes mellitus",
    "Tinnitus"
]
cleaned_diagnoses = [clean_search_query(d) for d in diagnoses]
print(cleaned_diagnoses)