def remember(store, docs):
    docs = dedup(docs)
    store.add_documents([summarize(d) for d in docs])
