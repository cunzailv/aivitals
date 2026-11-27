def search(vectorstore, query_embedding):
    return vectorstore.similarity_search(query_embedding, k=5)
