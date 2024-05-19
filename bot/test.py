import en_core_web_sm
nlp = en_core_web_sm.load()

# Test it on some text
doc = nlp("Hello, world!")
for token in doc:
    print(token.text, token.pos_)
